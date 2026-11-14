"""Blind validation and pilot timing using the independently installed CUDA worker."""
from bench import *
import subprocess,io,struct,contextlib
GPU_PY=__import__('os').environ.get('GATE_GPU_PY',sys.executable)
seeds=[1729,2718,3141]; grid=np.array([.02,.05,.10,.15])
def feat(nom,k):
    g,r,_=nom; I,J=np.triu_indices(k,1); S=k//2
    a,b=np.log1p(.1*g[I])/5,np.log1p(.1*g[J])/5
    return np.stack([a+b,abs(a-b),r,np.broadcast_to(np.arange(S)/max(S-1,1),r.shape),np.zeros_like(r),np.full_like(r,.5),np.full_like(r,2.)],-1).astype('f')
@contextlib.contextmanager
def worker(seed):
    log=(res/f'gpu_stderr_{seed}.log').open('a')
    child=subprocess.Popen([GPU_PY,'-u',str(out/'train_gpu.py'),'serve',str(seed)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    def read():
        size=child.stdout.read(8)
        if len(size)!=8:raise RuntimeError('GPU worker failed; see log')
        n=struct.unpack('<Q',size)[0];buf=child.stdout.read(n)
        if len(buf)!=n:raise RuntimeError('truncated GPU result')
        return buf
    def predict(nom,k):
        b=io.BytesIO();np.save(b,feat(nom,k));msg=b.getvalue()
        child.stdin.write(struct.pack('<Q',len(msg))+msg);child.stdin.flush()
        with np.load(io.BytesIO(read())) as f:r={k:f[k] for k in f.files}
        r['lam']=float(r['lam'].item());predict.gpu=float(r['forward_ms']);predict.encoder=float(r['base_ms']);return r
    try:
        if read()!=b'OK':raise RuntimeError('GPU worker startup')
        yield predict
    finally:
        child.stdin.close();child.wait(timeout=30);log.close()
def writecsv(path,rows):
    with path.open('w',newline='') as fp:
        w=csv.DictWriter(fp,list(rows[0]));w.writeheader();w.writerows(rows)
def quality(rr):
    return float(np.mean(np.array([x['G'] for x in rr])[:,None]<=grid)),float(np.median([x['total_ns'] for x in rr]))
def validate():
    saved=res/'validation.csv'
    rows=list(csv.DictReader(saved.open())) if saved.exists() else []
    for r in rows:
        r['label']=int(r['label']) if r['label'].isdigit() else r['label']
        for key in ['G','total_ns']:r[key]=float(r[key])
    for label in list(METHODS)+seeds:
        if sum(r['label']==label for r in rows)==256:continue
        with worker(label) if isinstance(label,int) else contextlib.nullcontext(None) as infer:
            for i in range(64):
                for fam in ('analytic','A','B','C'):
                    raw=np.load(out/'data'/f'val_{fam}_{i:04d}.npz')['h'];db=(0,10,20)[(i//3)%3]
                    h,sc=normalized(raw,len(raw),db);r,_,tim=solve(h,'neural' if infer else label,propose=infer)
                    rows.append(dict(label=label,family=fam,idx=i,k=len(raw),db=db,G=r['G'],gpu_ms=infer.gpu if infer else 0,**tim))
        writecsv(res/'validation.csv',rows);print('validated',label,quality([r for r in rows if r['label']==label]),flush=True)
    def key(m):
        q,t=quality([r for r in rows if r['label']==m]);return (-q,t,m)
    seed=min(seeds,key=key);control=min(METHODS,key=key)
    import shutil
    shutil.copyfile(res/f'seed_{seed}.pt',res/'locked_proposer.pt')
    lock={'seed':seed,'comparator':control,'candidate':'neural','model_sha256':hashlib.sha256((res/'locked_proposer.pt').read_bytes()).hexdigest(),'utc':datestr()}
    (res/'selection.json').write_text(json.dumps(lock,indent=2));return seed
def neural_pilots(seed):
    path=res/'neural_pilot.csv'
    cols=fields+['gpu_ms','base_gpu_ms'];done=set()
    if path.exists():
        with path.open() as f:done={(r['family'],int(r['block']),int(r['k']),int(r['db']),int(r['rep'])) for r in csv.DictReader(f)}
    with worker(seed) as infer,path.open('a',newline='') as f,gzip.open(res/'neural_receipts.jsonl.gz','at',compresslevel=2) as archive:
        w=csv.DictWriter(f,cols)
        if not done:w.writeheader()
        # Only the predeclared known-channel operating-point cells require candidate pilot ECDF reevaluation.
        for i in range(24):
            for fam in families[:4]:
                raw=np.load(out/'data'/f'pilot_{fam}_{i:04d}.npz')['h']
                for k in [32,64]:
                    h,sc=normalized(raw,k,10);norm=k//2*np.log(2)
                    for rep in range(3):
                        if (fam,i,k,10,rep) in done:continue
                        r,p,tim=solve(h,'neural',propose=infer)
                        a=np.array(r['pair']);pw=np.array(r['power'])/PT;s=np.arange(k//2)
                        v=np.frombuffer(base64.b64decode(r['receiver'][2]),dtype='<c16').reshape(k//2,2,-1);true=0.
                        for j in [0,1]:
                            u,o=a[:,j],a[:,1-j];d=v[:,j];true+=np.log1p(pw[u]*abs((d.conj()*h[u,:,s]).sum(1))**2/((abs(d)**2).sum(1)+pw[o]*abs((d.conj()*h[o,:,s]).sum(1))**2)).sum()
                        lo=int(r['L'])/int(r['den']);hi=int(r['U'])/int(r['den'])
                        if not lo<=true+1e-10 or true>hi+1e-10:raise ArithmeticError('neural soundness')
                        w.writerow(dict(family=fam,block=i,k=k,db=10,rep=rep,method='neural',scale=sc,G=r['G'],dc='' if r['dc_tick'] is None else r['dc_tick']/Q/norm,Sd=r['Sd_tick']/Q/norm,Lbit=lo/norm,Ubit=hi/norm,fallback=r['fallback'],zero_ok=1,gpu_ms=infer.gpu,base_gpu_ms=infer.encoder,**tim))
                        if rep==0:archive.write(json.dumps({'id':[fam,i,10],'receipt':r},separators=(',',':'))+'\n')
                    f.flush()
            print('neural pilot',i,flush=True)
if __name__=='__main__':
    seed=validate() if not (res/'selection.json').exists() else json.loads((res/'selection.json').read_text())['seed']
    neural_pilots(seed)

