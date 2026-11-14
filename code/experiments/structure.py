"""Same-table integer DP, exact discrete relaxation loss, and fixed-policy interpolation."""
from inputs import *
from campaign import *
from numba import njit
import itertools
@njit(cache=True)
def dp0(weights):
    k=len(weights);S=k//2;N=1<<k;v=np.full(N,-(1<<60),np.int64);v[0]=0;back=np.zeros((N,2),np.int16)
    bits=np.empty(N,np.int16);pop=np.zeros(N,np.int16)
    for i in range(k):bits[1<<i]=i
    for mask in range(1,N):
        pop[mask]=pop[mask&(mask-1)]+1
        if pop[mask]%2:continue
        s=pop[mask]//2-1;rem=mask
        while rem:
            u=rem&-rem;rem-=u;ii=bits[u];r=rem
            while r:
                b=r&-r;r-=b;j=bits[b];z=v[mask^u^b]+weights[ii,j,s]
                if z>v[mask]:v[mask]=z;back[mask,0]=ii;back[mask,1]=j
    pa=np.empty((S,2),np.int64);mask=N-1
    for t in range(S-1,-1,-1):
        i,j=back[mask];pa[t,0]=i;pa[t,1]=j;mask^=(1<<i)|(1<<j)
    return v[-1],pa
def dp(H,k):
    assert k<=16 and np.max(abs(H.astype(float)))*k<2**58;I,J=np.triu_indices(k,1);w=np.zeros((k,k,k//2),np.int64);w[I,J]=w[J,I]=H
    val,pa=dp0(w);assert sorted(pa.ravel())==list(range(k)) and H[edgeid(k,*pa.T),np.arange(k//2)].sum()==val;return val,pa
def scurve(r,h,uniform=False):
    k=len(h);S=k//2;H,nom,I,J,lam,_=table(h);assert digest(H)==r['H_sha']
    opt,pa=dp(H,k);sf=Q*S*np.log(2);loss=(r['R_tick']-int(opt))/sf
    assert loss>=0 and (r['dc_tick'] is None or r['dc_tick']/sf+1e-12>=loss)
    out=dict(loss=loss,posterior=np.nan if r['dc_tick'] is None else r['dc_tick']/sf,prior=r['Sd_tick']/sf,dp_H=int(opt),matched_A=r['A_tick'],R=int(r['R_tick']))
    if uniform:
        eq,mp=dp(np.rint(nom[2]*Q).astype('int64'),k);p=np.full(k,PT//10,dtype='int64');v0=filt(h,mp,p);u=lower(h,p,mp,v0,np.zeros((S,2,2)),T)
        pp,pg,pv=refine(h,pa,nom);l=lower(h,pg,pp,pv,np.zeros((S,2,2)),T)
        from scipy.optimize import minimize
        s=np.arange(S);a,b=pa.T;e=edgeid(k,a,b);g,rho,_=nom;ga=g[a,s];gb=g[b,s];rr=rho[e,s]
        def neg(x):
            xa=x[a]*ga;yb=x[b]*gb
            return -float((np.log1p(xa)+np.log1p(yb)+2*np.log1p(-np.minimum(.99999999999999,rr*(xa/(1+xa))*(yb/(1+yb))))).sum())
        sol=minimize(neg,pg/PT,method='SLSQP',bounds=[(.05,.2)]*k,constraints=[dict(type='ineq',fun=lambda x:k*.1-x.sum())],options=dict(maxiter=60,ftol=1e-10))
        p=project(sol.x);v=filt(h,pa,p);sqp=lower(h,p,pa,v,np.zeros((S,2,2)),T)
        out.update(dp_uniform_L=u.sum()/sf,dp_refine_L=l.sum()/sf,priced_dp_SQP_L=sqp.sum()/sf,certified_dp_U=(lam*.1*k+int(opt)/Q)/(S*np.log(2)),sqp_converged=int(sol.success))
    return out
def filt(h,pair,p):
    k,n,S=h.shape;s=np.arange(S);v=np.empty((S,2,n),complex)
    for j in (0,1):
        a=h[pair[:,j],:,s];b=h[pair[:,1-j],:,s];q=p[pair[:,1-j]]/PT;v[:,j]=a-b*((q*(b.conj()*a).sum(1))/(1+q*(abs(b)**2).sum(1)))[:,None]
    return v
def transition(h):
    k=len(h);S=k//2;s=np.arange(S);seq=np.arange(k).reshape(S,2);p=np.full(k,PT//10,dtype=np.int64);v=filt(h,seq,p)
    r,_,_=solve(h);replay(h,r);H,_,I,J,lam,_=table(h);assert digest(H)==r['H_sha'];e=edgeid(k,*seq.T);b=np.asarray(r['beta']);w=(H-b).max(1);R=r['R_tick']
    a=int(w[e].sum());hs=int(H[e,s].sum());ls=int(lower(h,p,seq,v,np.zeros((S,2,2)),T).sum());sf=Q*S*np.log(2)
    terms=[(R-int(b.sum())-a)*PT,(a-hs+int(b.sum()))*PT,0,(hs-ls)*PT+lam*int(p.sum())*Q]
    led=lam*(k*PT//10)*Q+(R-ls)*PT;assert min(terms)>=0 and sum(terms)==led;dc=r['dc_tick']
    assert dc is not None
    return dict(total=led/(PT*sf),dc=dc/sf,dominant=int(led>0 and 2*dc*PT>led),**{'term'+str(i+1):z/(PT*sf) for i,z in enumerate(terms)})
def control():
    rng=np.random.default_rng(185)
    for k in [2,4,6,8]:
        S=k//2;W=rng.integers(-100,100,size=(k*(k-1)//2,S));a,_=dp(W,k)
        brute=max(sum(W[edgeid(k,p[2*j],p[2*j+1]),j] for j in range(S)) for p in itertools.permutations(range(k)))
        assert a==brute
if __name__=='__main__':control();print('Signed integer DP matches exhaustive labelled permutations through K=8.')

