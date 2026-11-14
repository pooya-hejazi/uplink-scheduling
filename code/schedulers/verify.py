"""Replay raw channels, rate boxes, primal, two feasible label assignments and scaled blossom dual."""
import gzip,csv,json,hashlib,base64
from polish import *
def replay(h,r,eps=0.):
    k,n,S=h.shape;s=np.arange(S);assert digest(h)==r['raw_sha']
    g,G,rho,I,J=endpoints(h,eps);root,pen=cached_roots(g,G,rho,I,J,T);lam=r['lambda_price']
    def unpack(v):return np.frombuffer(base64.b64decode(v[2]),np.dtype(v[0])).reshape(v[1])
    anchor=unpack(r['anchor_input']) if 'anchor_input' in r else np.clip(1/max(lam,1)-1/np.maximum(G,1e-280),.05,.2)
    H=priced(g,G,rho,I,J,T,root,pen,lam,anchor);sel=np.asarray(r['leaves']);assert len(set(sel))==len(sel) and np.all((sel>=0)&(sel<H.size))
    leaves(H,sel,g,G,rho,I,J,T,lam);H=np.ceil(H*Q).astype('int64');assert digest(H)==r['H_sha']
    beta=np.asarray(r['beta']);w=(H-beta).max(1)
    if r['witness']=='odd-set4':
        m=np.asarray(r['pairs']);y=np.asarray(r['y4']); val=check4(k,I,J,w,m,y,r['z4'])
        cols=r['cols'];e=edgeid(k,*m.T);A=H[e];ay=np.asarray(r['ay']);ab=np.asarray(r['ab'])
        assert sorted(cols)==list(range(S)) and np.all(ay[:,None]+ab>=A) and sum(ay)+sum(ab)==A[s,cols].sum()==r['A_tick']
        R=int(beta.sum())+val; assert R-r['A_tick']==r['dc_tick'] and 0<=r['dc_tick']<=r['Sd_tick']
    else:
        assert r['witness']=='P3';bp,R=repair(H,I,J,np.asarray(r['alpha']));assert np.array_equal(bp,beta)
    assert int(np.ptp(H-beta,axis=1).max())*S==r['Sd_tick']
    for name in ['pair','pool_pair']:assert sorted(np.asarray(r[name]).ravel())==list(range(k))
    m=np.asarray(r['pool_pair']);assert H[edgeid(k,*m.T),s].sum()==r['A_pool_tick']<=R
    if r['A_tick'] is not None: assert r['A_pool_tick']>=r['A_tick']
    m=np.asarray(r['pair']);p=np.asarray(r['power']);v=unpack(r['receiver']);balls=ballarr(np.broadcast_to(eps,(k,S)),m)
    L=lower(h,p,m,v,balls,T);assert list(L)==r['L_pair'] and min(p)>=PT//20 and max(p)<=PT//5 and sum(p)<=k*PT//10
    e=edgeid(k,*m.T);P=k*PT//10;U=lam*P*Q+R*PT;ls=int(L.sum())*PT;wt=int(w[e].sum());hs=int(H[e,s].sum())
    terms=[(R-int(beta.sum())-wt)*PT,(wt-hs+int(beta.sum()))*PT,lam*(P-int(p.sum()))*Q,(hs-int(L.sum()))*PT+lam*int(p.sum())*Q]
    assert min(terms)>=0 and terms==list(map(int,r['terms'])) and sum(terms)==U-ls and (U,ls)==(int(r['U']),int(r['L']))
    direct=0.
    for t in [0,1]:
        a,b=m[:,t],m[:,1-t];u=v[:,t];direct+=np.log1p(p[a]/PT*abs((u.conj()*h[a,:,s]).sum(1))**2/((abs(u)**2).sum(1)+p[b]/PT*abs((u.conj()*h[b,:,s]).sum(1))**2)).sum()
    assert ls/int(r['den'])<=direct+1e-10 and direct<=U/int(r['den'])+1e-10
def controls():
    rng=np.random.default_rng(7184)
    for k in [4,6,8,16,32,64]:
        I,J=np.triu_indices(k,1)
        for j in range(3):
            w=(np.where((I<k//2)==(J<k//2),20,-19) if j==0 else rng.integers(-2**27,2**27,len(I))).astype('int64')
            pa,y,z,val=match(k,I,J,w);assert val==reference(k,I,J,w)[3]
            try:check4(k,I,J,w,pa,y-4,z)
            except ArithmeticError:pass
            else:raise AssertionError('bad weight witness accepted')
        if k<=8:
            h=np.ascontiguousarray(rng.normal(size=(k,4,k//2))+1j*rng.normal(size=(k,4,k//2)))
            r,*_=solve(h);replay(h,r)
    print('PASS: scaled native vs pinned reference including signed weights, adversarial odd sets, rejected corruptions; raw-input and exact ledger reconstruction.',flush=True)
if __name__=='__main__':controls()

