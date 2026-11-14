"""Construct deterministic supervision from fit blocks only; no GPU training here."""
from solver import *
import csv
from enclosures import strict,mix
home=Path(__file__).resolve().parent; dst=home/'teachers';dst.mkdir(exist_ok=True)
def features(nom,k):
    g,r,_=nom; I,J=np.triu_indices(k,1);S=k//2
    a,b=np.log1p(.1*g[I])/5,np.log1p(.1*g[J])/5
    return np.stack([a+b,np.abs(a-b),r,np.broadcast_to(np.arange(S)/max(1,S-1),r.shape),np.zeros_like(r),np.full_like(r,.5),np.full_like(r,2.)],-1).astype('float32')
@strict
def sibling_labels(g,G,r,I,J,T,lam,chosen):
    S=g.shape[1]; out=np.empty((len(chosen),2))
    for z in range(len(chosen)):
        e=chosen[z]//S;s=chosen[z]%S; mid=(PLO+PHI)/2
        for side in range(2):
            a,A=(PLO,mid) if side==0 else (mid,PHI)
            parent=mix(g,G,I[e],J[e],s,r[e,s],a,A,PLO,PHI,T)-lam*(a+PLO)
            sub=-np.inf
            for b,B in [(PLO,mid),(mid,PHI)]: sub=max(sub,mix(g,G,I[e],J[e],s,r[e,s],a,A,b,B,T)-lam*(a+b))
            out[z,side]=max(0.,parent-sub)
    return out
def job():
    with (dst/'manifest.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['id','K','db','teacher_ns','G','num_visited','strict_priority_comparisons'])
        for i in range(1024):
            for fam in ('analytic','A','B','C'):
                start=now(); name=f'fit_{fam}_{i:04d}'; raw=np.load(home/'data'/(name+'.npz'))['h'];k=len(raw);S=k//2
                db=(0,10,20)[(i//3)%3];h,_=normalized(raw,k,db)
                I,J=np.triu_indices(k,1);nom=nominal(h,I,J);x=features(nom,k)
                rec,_,_=solve(h,'subgrad');pa=np.asarray(rec['pair']); e=edgeid(k,*pa.T)
                p=np.array(rec['power'])/PT; lam=rec['lambda']
                bet=np.array(rec['beta'])/Q; bet-=bet.mean()
                alpha=np.array(rec.get('alpha',rec.get('y2',[0]*k)))/Q/(1 if 'alpha' in rec else 2);alpha-=alpha.mean()
                g,G,r,*_=endpoints(h,0.)
                root,pen=cached_roots(g,G,r,I,J,T);anc=np.clip(1/max(1,lam)-1/np.maximum(G,1e-280),.05,.2)
                # Separate mixed-root labels avoid censoring by the competing concave envelope.
                mixed=root-lam*(2*PLO); chosen=np.asarray(rec['leaves'],dtype='int64')
                after=mixed.copy();leaves(after,chosen,g,G,r,I,J,T,lam)
                delta=(mixed-after).ravel()[chosen]
                sib=sibling_labels(g,G,r,I,J,T,lam,chosen); sign=np.sign(sib[:,0]-sib[:,1]);mask=abs(sib[:,0]-sib[:,1])>1e-10
                anchor=np.stack([anc[I],anc[J]],-1)
                np.savez(dst/(name+'.npz'),x=x,e=e,p=p.astype('f'),beta=bet.astype('f'),alpha=alpha.astype('f'),lam=lam,anchor=anchor.astype('f'),visited=chosen,root_delta=delta.astype('f'),rank_id=chosen[mask],rank_sign=sign[mask].astype('f'))
                w.writerow([name,k,db,now()-start,rec['G'],len(chosen),mask.sum()])
            if i%32==0: f.flush();print(i,flush=True)
if __name__=='__main__':job()

