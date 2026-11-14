"""Isolate all writes from the accepted model. Reuse the original layers, losses and GPU worker."""
import sys,time,json,hashlib
from pathlib import Path
home=Path(__file__).resolve().parent;old=home.parent/'Gate_2';sys.path.insert(0,str(old))
import train_gpu as gpu
from network import Net,SEEDS,batch_loss
import torch,numpy as np
from scipy.optimize import linear_sum_assignment
art=home/'results';art.mkdir(exist_ok=True);gpu.art=art
def target(row):
    x=row['x'];hi=(x[:,:,0]+x[:,:,1]).astype('d')*2.5;lo=(x[:,:,0]-x[:,:,1]).astype('d')*2.5
    rate=hi+lo+2*np.log1p(-np.minimum(.99999999,x[:,:,2]*(-np.expm1(-hi))*(-np.expm1(-lo))))
    A=rate[row['e']];n=len(A);i,j=linear_sum_assignment(-A);b=np.zeros(n)
    for _ in range(n):b=np.maximum(b,(A+(b[j]-A[i,j])[:,None]).max(0))
    y=A[i,j]-b[j];assert np.min(y[:,None]+b-A)>-1e-8
    return (b-b.mean()).astype('f')
def train():
    paths=sorted((old/'teachers').glob('fit_*.npz'));assert len(paths)==4096;groups={8:[],16:[],32:[]}
    for path in paths:
        with np.load(path) as f:row={k:f[k] for k in f.files}
        row['beta']=target(row); groups[len(row['p'])].append(row)
    for seed in SEEDS:
        torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);rng=np.random.default_rng(seed);torch.backends.cuda.matmul.allow_tf32=False
        net=Net().cuda();opt=torch.optim.Adam(net.parameters(),lr=.001);history=[];t=time.perf_counter()
        for ep in range(15):
            batches=[]
            for k,rows in groups.items():
                order=rng.permutation(len(rows));batches.extend([[rows[z] for z in order[j:j+8]] for j in range(0,len(rows),8)])
            rng.shuffle(batches);total=0;losses=0.
            for batch in batches:
                opt.zero_grad(set_to_none=True);loss=batch_loss(net,batch)
                if not torch.isfinite(loss):raise ArithmeticError('nonfinite loss')
                loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),3.);opt.step()
                total+=len(batch);losses+=loss.item()*len(batch)
            assert total==4096;torch.cuda.synchronize();history.append(losses/total)
            print('seed',seed,'epoch',ep+1,'loss',round(history[-1],5),'seconds',round(time.perf_counter()-t,2),flush=True)
        path=art/f'seed_{seed}.pt';torch.save(net.state_dict(),path)
        data=dict(seed=seed,epochs=15,per_epoch=4096,optimizer_steps=15*len(batches),gpu=torch.cuda.get_device_name(),seconds=time.perf_counter()-t,loss=history,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        (art/f'seed_{seed}.json').write_text(json.dumps(data,indent=2))
if __name__=='__main__':
    if sys.argv[1]=='train':train()
    else:gpu.serve(int(sys.argv[2]))

