"""Finish the paired neural and version-matched resource-control comparisons across the sensitivity matrix."""
from grid import *
def run():
    guard();cfg,_,dest,n=which('test');where=dest/'matrix_methods';where.mkdir(exist_ok=True)
    # The legacy co-primary timing uses unmodified Gate 2A. Here this resource control shares the candidate's native matcher and exact checker.
    solver.blossom=match;audit.check=check4
    groups={'native':fams,'analytic':geoms,'ray':('O1_60','asu_campus1')}
    fs=groups.get(sys.argv[1],(sys.argv[1],))
    assert set(fs)<=set(fams+geoms+('O1_60','asu_campus1'))
    with evaluate.worker(cfg['seed']) as pred:
        for f in fs:
            N=64 if f in ('O1_60','asu_campus1') else 128
            start=int(sys.argv[2]) if len(sys.argv)>2 else 0;stride=int(sys.argv[3]) if len(sys.argv)>3 else 1
            for i in range(start,N,stride):
                path=where/f'{f}_{i:03d}.csv'
                if path.exists():continue
                raw=source(f,i);rr=[]
                for k in (16,32,64):
                    for db in (-5,0,10,20):
                        # Exact native 10-dB K32/64 three-repeat results are authoritative and already archived.
                        if f in fams and k in (32,64) and db==10:continue
                        h,_=normalized(raw,k,db);nom=nominal(h,*np.triu_indices(k,1));st=now();proposal=pred(nom,k);tprop=now()-st;fm=pred.gpu
                        # Pair all methods on a single GPU proposal: times here are component-assembled and never used for a deadline decision.
                        for m in ('standalone','hybrid','legacy'):
                            if m=='legacy':r,_,t=solver.solve(h,'subgrad');audit.replay(h,r);ns=t['total_ns'];gms=0
                            else:r,_,t=solve(h,m,lambda *_:proposal);replay(h,r);ns=t['total_ns']+tprop;gms=fm
                            den=int(r['den'])*(k//2)*np.log(2);rr.append(dict(family=f,block=i,k=k,db=db,method=m,G=r['G'],L=int(r['L'])/den,U=int(r['U'])/den,component_ms=ns/1e6,gpu_ms=gms))
                putcsv(path,rr)
            print('paired matrix',f,N,flush=True)
if __name__=='__main__':run()

