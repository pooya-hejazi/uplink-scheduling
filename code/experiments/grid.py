"""All topology grids; operated separately from the timed three-repeat primary benchmark."""
from structure import *
from inputs import root as root3
import argparse
from threadpoolctl import threadpool_limits
def source(f,i):
    return analytic(f,i) if f in geoms else np.load(root3/'data'/f'pilot_{f}_{i:04d}.npz')['h']
def run(group):
    guard();control();where=root3/'results'/('grid_'+group);where.mkdir(parents=True,exist_ok=True)
    scene=('O1_60','asu_campus1')
    sets=fams if group=='native' else geoms if group=='analytic' else scene
    for f in sets:
        count=128 if f not in scene else len(json.loads((root3/f'{f}_tiles.json').read_text()))
        for i in range(count):
            file=where/f'{f}_{i:03d}.csv'
            if file.exists():continue
            raw=source(f,i);out=[];tt=[]
            for k in (16,32,64):
                for db in (-5,0,10,20):
                    h,sc=normalized(raw,k,db);sf=k//2*np.log(2)
                    r,_,t=solve(h);replay(h,r);q=one_row(f,i,k,'det',0,r,t,None,db);q['scale']=sc
                    for j,v in enumerate(r['terms']):q['term'+str(j+1)]=int(v)/int(r['den'])/sf
                    if k==16:
                        q.update(scurve(r,h,uniform=True))
                    out.append(q)
            if f=='frequency_selective':
                H,_=normalized(raw,16,10)
                for j in range(9):
                    x=j/8;h=np.ascontiguousarray((1-x)*H[:,:,[0]]+x*H);tt.append(dict(block=i,t=x,**transition(h)))
                putcsv(where/f'transition_{i:03d}.csv',tt)
            # Uniform columns across small and large rows.
            keys=list(out[0]);putcsv(file,[{k:q.get(k,'') for k in keys} for q in out])
            if i%16==15:print(group,f,i+1,'/',count,flush=True)
def load_sensitivity():
    cfg,root,dest,n=which('test');path=dest/'load_sensitivity.csv';idx=sorted([(f,i) for f in fams for i in range(n)],key=lambda v:hashlib.sha256(f'load|{v[0]}|{v[1]}'.encode()).digest())[:52]
    rng=np.random.default_rng(7713);out=[]
    with evaluate.worker(cfg['seed']) as pred:
        for f,i in idx:
            raw=source(f,i)
            for k in (32,64):
                h,sc=normalized(raw,k,10)
                for m in rng.permutation(methods):
                    r,_,t=runone(h,m,pred);(audit.replay if m=='legacy' else replay)(h,r);out.append(one_row(f,i,k,m,3,r,t,pred))
        putcsv(path,out)
if __name__=='__main__':
    if sys.argv[1]=='load':load_sensitivity()
    else:
        with threadpool_limits(1):run(sys.argv[1])

