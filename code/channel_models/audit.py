"""CPU-only receipt reconstruction, with adversarial odd-set, corruption, log and small optimum controls."""
import gzip,random,sys
from fractions import Fraction as F
from decimal import Decimal as Dec,localcontext
from solver import *
from witness import check
def unpack(a):return np.frombuffer(base64.b64decode(a[2]),np.dtype(a[0])).reshape(a[1])
def replay(h,r,eps=0.,proj=None):
    k,n,S=h.shape;g,G,rho,I,J=endpoints(h,eps);assert digest(h)==r['raw_sha']
    ep=np.broadcast_to(np.asarray(eps,dtype=float),(k,S));assert digest(ep)==r['eps_sha']
    root,pen=cached_roots(g,G,rho,I,J,T);lam=r['lambda'];bet=np.array(r['beta'],dtype='int64')
    anchors=[np.full_like(G,.125),np.clip(1/max(lam,1)-1/np.maximum(G,1e-280),.05,.2)]
    if 'anchor_input' in r:anchors+=[unpack(r['anchor_input'])]
    for anc in anchors:
        H=priced(g,G,rho,I,J,T,root,pen,lam,anc)
        chosen=np.asarray(r['leaves']);assert len(set(chosen))==len(chosen) and np.all((chosen>=0)&(chosen<root.size))
        leaves(H,chosen,g,G,rho,I,J,T,lam);H=np.ceil(H*Q).astype('int64')
        if digest(H)==r['H_sha']:break
    else:raise AssertionError('covered table does not match')
    w=(H-bet).max(1);R=None;dc=None
    if 'pairs' in r:
        pairs=np.array(r['pairs']);m=check(k,I,J,w,pairs,np.array(r['y2']),r['z'])
        A=H[edgeid(k,*pairs.T)];y=np.array(r['ay']);b=np.array(r['ab']);cols=np.array(r['cols'])
        assert sorted(cols)==list(range(S)) and np.all(y[:,None]+b>=A) and y.sum()+b.sum()==A[np.arange(S),cols].sum()
        R=int(bet.sum())+m;dc=R-int(y.sum()+b.sum())
    if r['witness'].startswith('P3'):
        bp,R=repair(H,I,J,np.array(r['alpha']));assert np.array_equal(bp,bet)
    assert dc==r['dc_tick'] and int(np.ptp(H-bet,axis=1).max())*S==r['Sd_tick']
    U=lam*(k*PT//10)*Q+R*PT;assert U==int(r['U'])
    pa=np.asarray(r['pair']);p=np.asarray(r['power']);v=unpack(r['receiver'])
    assert sorted(pa.flatten())==list(range(k)) and p.min()>=PT//20 and p.max()<=PT//5 and sum(p)<=k*PT//10
    lo=lower(h,p,pa,v,ballarr(ep,pa),T);assert np.array_equal(lo,r['LF_pair'])
    if proj is not None:
        lp=lower(h,p,pa,v,np.broadcast_to(proj,(S,2,2)),T);assert np.array_equal(lp,r['LP_pair'])
        if lp.sum()>lo.sum():lo=lp
    assert np.array_equal(lo,r['L_pair'])
    e=edgeid(k,*pa.T);a=int(w[e].sum());b=int(H[e,np.arange(S)].sum());c=int(p.sum());P=k*PT//10
    terms=[U-lam*P*Q-(int(bet.sum())+a)*PT,(a-b+int(bet.sum()))*PT,lam*(P-c)*Q,(b-int(lo.sum()))*PT+lam*c*Q]
    assert min(terms)>=0 and terms==list(map(int,r['terms'])) and sum(terms)==U-int(r['L']) and int(r['L'])==int(lo.sum())*PT
def controls():
    from itertools import combinations,permutations,product
    rng=np.random.default_rng(831);k=6;I,J=np.triu_indices(k,1);w=np.where((I<3)==(J<3),20,-19).astype('int64')
    p,y,z,val=blossom(k,I,J,w);assert len(z)>0 and val==21
    try:check(k,I,J,w,p,y-3,z)
    except ArithmeticError:pass
    else:raise AssertionError('tampered witness accepted')
    with localcontext() as ctx:
        ctx.prec=90
        for x in np.r_[np.exp2(rng.uniform(-90,90,1000)),1+np.arange(257)/256]:
            exact=Dec.from_float(float(x)).ln()
            assert Dec.from_float(logi(x,T,False))<=exact<=Dec.from_float(logi(x,T,True))
    for k in [2,4,6]:
        s=k//2;I,J=np.triu_indices(k,1);h=np.ascontiguousarray(rng.normal(size=(k,4,s))+1j*rng.normal(size=(k,4,s)))
        rec,_,_=solve(h,'subgrad');replay(h,rec)
        alt,_,_=solve(h,'subgrad',eps=.02,force_fallback=True);replay(h,alt,.02)
        g,G,R,_,_=endpoints(h,0)
        for e in range(len(I)):
            for t in range(s):
                A,B=h[I[e],:,t],h[J[e],:,t]
                gg=lambda a:sum(F(float(v.real))**2+F(float(v.imag))**2 for v in a)
                aa,bb=gg(A),gg(B);rr=sum(F(float(a.real))*F(float(b.real))+F(float(a.imag))*F(float(b.imag)) for a,b in zip(A,B));ii=sum(F(float(a.real))*F(float(b.imag))-F(float(a.imag))*F(float(b.real)) for a,b in zip(A,B))
                assert F(g[I[e],t])<=aa<=F(G[I[e],t]) and F(R[e,t])<=(rr*rr+ii*ii)/(aa*bb)
        n,r,score=nominal(h,I,J);best=-math.inf
        # Enumerate all labelled schedules and every feasible point of a three-point power grid.
        for perm in permutations(range(k)):
            if any(perm[j]>perm[j+1] for j in range(0,k,2)):continue
            a=np.array(perm[::2]);b=np.array(perm[1::2]);e=edgeid(k,a,b);tt=np.arange(s)
            pp=np.array([p for p in product([1,2,4],repeat=k) if sum(p)<=2*k])*.05
            xx=pp[:,a]*n[a,tt];yy=pp[:,b]*n[b,tt]
            q=(np.log1p(xx)+np.log1p(yy)+2*np.log1p(-r[e,tt]*(xx/(1+xx))*(yy/(1+yy)))).sum(1)
            best=max(best,q.max())
        assert best<=int(rec['U'])/int(rec['den'])+1e-10
    print('PASS: rational complex Gram, 1,257 decimal log checks, necessary odd sets, rejected invalid dual, forced P3, six-user grid and exact replay.')
if __name__=='__main__':
    controls();home=Path(__file__).resolve().parent
    for name in sys.argv[1:]:
        cache={};count=0
        with gzip.open(home/'results'/name,'rt') as f:
            for line in f:
                entry=json.loads(line);fam,i,db=entry['id'];r=entry['receipt'];path=home/'data'/f'pilot_{fam}_{i:04d}.npz'
                if path not in cache:cache={path:np.load(path)['h']}
                h,_=normalized(cache[path],r['k'],db);replay(h,r);count+=1
        print('PASS CPU-only receipt reconstructions',name,count,flush=True)

