"""GPU worker in the installed CUDA environment; fitting refuses to start before baseline completion."""
from network import *
import os,sys,struct,io,json,hashlib,time,math
from pathlib import Path
import numpy as np
home=Path(__file__).resolve().parent; art=home/'results'
def train():
    if not (art/'deterministic.done').exists(): raise RuntimeError('finish the deterministic pilots first')
    paths=sorted((home/'teachers').glob('fit_*.npz')); assert len(paths)==4096
    loadtime=time.monotonic(); groups={8:[],16:[],32:[]}
    for path in paths:
        with np.load(path) as a: row={k:a[k] for k in a.files}
        groups[len(row['p'])].append(row)
    print('loaded fit data',len(paths),time.monotonic()-loadtime,flush=True)
    for seed in SEEDS:
        start=time.perf_counter();torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);rng=np.random.default_rng(seed)
        torch.backends.cuda.matmul.allow_tf32=False
        net=Net().cuda();opt=torch.optim.Adam(net.parameters(),lr=.001)
        batches=[]
        for k,rows in groups.items():
            order=rng.permutation(len(rows));batches.extend([[rows[z] for z in order[j:j+8]] for j in range(0,len(rows),8)])
        rng.shuffle(batches);acc=0.;seen=0
        for j,batch in enumerate(batches):
            opt.zero_grad(set_to_none=True);loss=batch_loss(net,batch)
            if not torch.isfinite(loss):raise ArithmeticError('nonfinite training loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),3.);opt.step()
            acc+=loss.item()*len(batch);seen+=len(batch)
            if j%100==0:print(seed,j,round(acc/seen,5),flush=True)
        assert seen==4096; torch.cuda.synchronize()
        dest=art/f'seed_{seed}.pt';torch.save(net.state_dict(),dest)
        report=dict(seed=seed,n=seen,steps=len(batches),epochs=1,mean_loss=acc/seen,seconds=time.perf_counter()-start,torch=torch.__version__,gpu=torch.cuda.get_device_name(),sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
        (art/f'seed_{seed}.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
def frame_read(f):
    b=f.read(8)
    if not b:return None
    n=struct.unpack('<Q',b)[0]; assert 0<n<=100_000_000
    b=f.read(n)
    if len(b)!=n:raise EOFError('truncated GPU message')
    return b
def frame_write(f,b):f.write(struct.pack('<Q',len(b)));f.write(b);f.flush()
@torch.no_grad()
def serve(seed):
    model=Net().cuda().eval();model.load_state_dict(torch.load(art/f'seed_{seed}.pt',map_location='cuda'))
    torch.backends.cuda.matmul.allow_tf32=False
    for k in [8,16,32,64]:
        x=torch.zeros(1,k*(k-1)//2,k//2,7,device='cuda')
        _=model(x)
    torch.cuda.synchronize()
    frame_write(sys.stdout.buffer,b'OK')
    while True:
        packet=frame_read(sys.stdin.buffer)
        if packet is None:break
        x=torch.from_numpy(np.load(io.BytesIO(packet))).unsqueeze(0).cuda()
        torch.cuda.synchronize()
        a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);c=torch.cuda.Event(enable_timing=True)
        a.record(); d=model(x,encoder_event=b)
        # Evaluate the same head on child boxes for the active budget. Include all proposals in GPU timing.
        k=2*x.shape[2];budget=max(2,k*k//32)
        choice=d['priority'].flatten().topk(budget).indices; active=d['f'].reshape(-1,D)[choice]
        child1=model.box(active,[0,.5,0,1]);child2=model.box(active,[.5,1,0,1])
        score=d['priority'].flatten().clone(); score[choice]+=.05*torch.maximum(child1[:,2],child2[:,2])
        d['priority']=score.reshape_as(d['priority'])
        peak=d['anchor'][0];I,J=d['I'],d['J'];anc=peak.new_zeros(k,k//2)
        # Endpoints supplied per pair; aggregate endpoint suggestions at each user.
        anc.index_add_(0,I,peak[:,:,0]);anc.index_add_(0,J,peak[:,:,1]);anc/=k-1
        c.record();torch.cuda.synchronize()
        arrays={key:d[key][0].cpu().numpy().copy() for key in ('p','score','alpha','beta','lam','priority')}
        arrays.update(anchor=anc.cpu().numpy(),forward_ms=np.array(a.elapsed_time(c)),base_ms=np.array(a.elapsed_time(b)))
        out=io.BytesIO();np.savez(out,**arrays);frame_write(sys.stdout.buffer,out.getvalue())
if __name__=='__main__':
    if sys.argv[1]=='train':train()
    else:serve(int(sys.argv[2]))

