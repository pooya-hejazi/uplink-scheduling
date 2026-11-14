import base64,hashlib,json,math,time
from pathlib import Path
import numpy as np
from enclosures import endpoints,cached_roots,priced,leaves,lower,get_table,Q,PT,PLO,PHI,logi
from witness import assignment,blossom,edgeid,repair
T=get_table(); now=time.perf_counter_ns
METHODS=('sequential','equal_match','cold','subgrad')
def pack(a):
    a=np.ascontiguousarray(a);return [a.dtype.str,list(a.shape),base64.b64encode(a.tobytes()).decode()]
def digest(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def normalized(raw,k,db):
    v=np.asarray(raw,np.complex128); scale=np.sqrt(10**(db/10)/(.1*np.median(np.mean(abs(v)**2,axis=1))))
    n=v.shape[2]; s=k//2
    return np.ascontiguousarray(v[:k,:,::n//s]*scale),float(scale)
def project(p):
    p=np.clip(np.rint(p*PT),PT//20,PT//5).astype('int64')
    lo=PT//20; avail=len(p)*lo; excess=p-lo
    if int(excess.sum())>avail: p=lo+(excess*avail)//int(excess.sum())
    if not (p.min()>=lo and p.max()<=PT//5 and p.sum()<=len(p)*PT//10): raise ArithmeticError('power projection')
    return p
def nominal(h,I,J):
    H=h.transpose(2,0,1); gram=H.conj()@H.transpose(0,2,1)
    g=gram.diagonal(axis1=1,axis2=2).real.T.copy()
    r=np.clip(abs(gram[:,I,J].T)**2/np.maximum(g[I]*g[J],1e-290),0,1)
    x,y=.1*g[I],.1*g[J]
    score=np.log1p(x)+np.log1p(y)+2*np.log1p(-np.minimum(1-1e-15,r*(x/(1+x))*(y/(1+y))))
    return g,r,score
def make_action(h,I,J,method,prop=None,nom=None):
    k,n,S=h.shape; g,r,score=nom if nom is not None else nominal(h,I,J)
    seq=np.arange(k).reshape(S,2); eq=project(np.full(k,.1)); ss=np.arange(S)
    def q(pa,p):
        a,b=pa.T; e=edgeid(k,a,b); x=p[a]/PT*g[a,ss];y=p[b]/PT*g[b,ss]
        return (np.log1p(x)+np.log1p(y)+2*np.log1p(-np.minimum(1-1e-15,r[e,ss]*(x/(1+x))*(y/(1+y))))).sum()
    best=(float(q(seq,eq)),seq,eq)
    if method!='sequential':
        scr=score if prop is None else prop['score']
        w=np.rint(scr*2**27).astype('int64')
        pairs,*_=blossom(k,I,J,w.max(1)); e=edgeid(k,*pairs.T)
        cols,_,_=assignment(w[e]); pa=pairs[np.argsort(cols)]; a,b=pa.T; e=edgeid(k,a,b)
        p=eq.copy() if prop is None else project(prop['p'])
        rate=q(pa,p)
        if rate>best[0]: best=(float(rate),pa,p.copy())
        for step in [1,.5,.25,.125]:
            x=p[a]/PT*g[a,ss]; y=p[b]/PT*g[b,ss]; R=r[e,ss]
            det=1+x+y+(1-R)*x*y
            grad=np.empty(k)
            grad[a]=g[a,ss]*(2*(1+(1-R)*y)/det-1/(1+x))
            grad[b]=g[b,ss]*(2*(1+(1-R)*x)/det-1/(1+y))
            trial=project(p/PT+step*.05*grad/max(1e-12,max(abs(grad))))
            value=q(pa,trial)
            if value>=rate: p=trial;rate=value
            if value>best[0]: best=(float(value),pa,trial.copy())
    _,pa,p=best
    v=np.empty((S,2,n),dtype=np.complex128)
    for j in [0,1]:
        u=h[pa[:,j],:,ss]; o=h[pa[:,1-j],:,ss]; pp=p[pa[:,1-j]]/PT
        v[:,j]=u-o*((pp*(o.conj()*u).sum(1))/(1+pp*(abs(o)**2).sum(1)))[:,None]
    return pa,p,v
def ballarr(eps,pa):
    S=len(pa); s=np.arange(S); b=np.empty((S,2,2))
    for t in [0,1]: b[:,t,0]=eps[pa[:,t],s];b[:,t,1]=eps[pa[:,1-t],s]
    return b
def solve(h,method,eps=0.,proj=None,propose=None,action=None,force_fallback=False):
    start=now(); h=np.ascontiguousarray(h,np.complex128); k,n,S=h.shape
    eps=np.broadcast_to(np.asarray(eps,dtype=float),(k,S))
    g,G,r,I,J=endpoints(h,eps); nom=nominal(h,I,J); feat=now()-start
    ip=now(); prop=propose(nom,k) if propose is not None else None; net=now()-ip if propose else 0
    pre=now(); pa,p,v=make_action(h,I,J,method,prop,nom) if action is None else action
    e=edgeid(k,*pa.T); ss=np.arange(S)
    LF=lower(h,p,pa,v,ballarr(eps,pa),T); LP=None
    if proj is not None:
        bb=np.broadcast_to(np.asarray(proj,dtype=float),(S,2,2))
        if np.any(~np.isfinite(bb)) or np.any(bb<0):raise ValueError('projected radii')
        LP=lower(h,p,pa,v,bb,T)
    L=LP if LP is not None and sum(LP)>sum(LF) else LF
    primal=now()-pre; clk=now(); root,pen=cached_roots(g,G,r,I,J,T); box=now()-clk; dual=0
    if not np.isfinite(root).all(): raise ArithmeticError('root coverage')
    bet=np.zeros(S,np.int64); alpha=np.zeros(k,np.int64); P=k*PT//10
    lam0=int(np.clip(round(np.median(nom[0]/(1+.1*nom[0]))),0,10))
    # Same three candidates for deterministic optimized and neural: zero, centered, final proposed/subgradient.
    prices=[0] if method in METHODS[:2] else ([0,lam0] if method=='cold' else [0,lam0,lam0 if prop is None else int(np.clip(round(prop['lam']),0,32))])
    best=None; count=0; fall=0; trees=[]
    for it,lam in enumerate(prices):
        t=now()
        if it==1 and method!='cold':
            cen=np.mean(root,axis=0); bet=np.rint((cen-cen.mean())*Q).astype('int64')
        if prop is not None and it==2:
            bet=np.rint(np.clip(prop['beta']-np.mean(prop['beta']),-16,16)*Q).astype('int64')
            alpha=np.rint(np.clip(prop['alpha'],-16,16)*Q).astype('int64')
        anchor=(np.full_like(G,.125) if not lam or method=='cold' else np.clip(1/max(lam,1)-1/np.maximum(G,1e-280),.05,.2))
        if prop is not None and it==2: anchor=np.clip(prop['anchor'],.05,.2)
        H=priced(g,G,r,I,J,T,root,pen,lam,anchor)
        adj=H-bet/Q
        top=np.argsort(-adj,axis=1,kind='stable')[:,:min(S,2)]
        pool=(np.arange(len(I))[:,None]*S+top).ravel()
        priority=adj.ravel() if prop is None else prop['priority'].ravel()
        chosen=pool[np.lexsort((pool,-priority[pool]))[:max(2,k*k//32)]]
        leaves(H,chosen,g,G,r,I,J,T,lam)
        if not np.isfinite(H).all() or np.max(np.abs(H))>400: raise ArithmeticError('scaled table range')
        H=np.ceil(H*Q).astype('int64'); w=(H-bet).max(1); box+=now()-t;t=now()
        rec={'lambda':lam,'beta':bet.tolist(),'leaves':chosen.tolist(),'H_sha':digest(H)}
        al=(np.rint(np.mean(np.log1p(.1*nom[0]),axis=1)*Q).astype('int64') if prop is None or it!=2 else alpha)
        bp,rp=repair(H,I,J,al)
        rec['P3_checked']=True
        try:
            if force_fallback: raise ArithmeticError('forced witness failure')
            m,y,z,mval=blossom(k,I,J,w)
            ei=edgeid(k,*m.T); cols,ay,ab=assignment(H[ei])
            R=int(bet.sum())+mval; A=int(H[ei,cols].sum())
            dc=R-A
            if dc<0: raise ArithmeticError('negative posterior')
            rec.update(witness='odd-set',pairs=m.tolist(),y2=y.tolist(),z=[(list(B),int(pp)) for B,pp in z],cols=cols.tolist(),ay=ay.tolist(),ab=ab.tolist())
            if it and rp<R:
                bet=bp;w=(H-bet).max(1)
                m,y,z,mval=blossom(k,I,J,w);ei=edgeid(k,*m.T);cols,ay,ab=assignment(H[ei])
                dc=int(bet.sum())+mval-int(H[ei,cols].sum());R=rp
                rec.update(witness='P3+diagnostic',alpha=al.tolist(),beta=bet.tolist(),pairs=m.tolist(),y2=y.tolist(),z=[(list(B),int(pp)) for B,pp in z],cols=cols.tolist(),ay=ay.tolist(),ab=ab.tolist())
        except ArithmeticError:
            bet,R=bp,rp; w=(H-bet).max(1);rec.update(witness='P3',beta=bet.tolist(),alpha=al.tolist()); dc=None;fall+=1
        U=lam*P*Q+R*PT
        spread=int(np.ptp(H-bet,axis=1).max())*S
        if best is None or U<best[0]:
            A0=sum(int(xx) for xx in w[e])
            terms=[U-lam*P*Q-(int(bet.sum())+A0)*PT,(A0-int(H[e,ss].sum())+int(bet.sum()))*PT,lam*(P-int(p.sum()))*Q,(int(H[e,ss].sum())-int(L.sum()))*PT+lam*int(p.sum())*Q]
            if min(terms)<0 or sum(terms)!=U-int(L.sum())*PT:raise ArithmeticError(('ledger',terms))
            if dc is not None and dc>spread:raise ArithmeticError('prior bound')
            best=U,rec,terms,dc,spread
        if it==1 and method=='subgrad' and dc is not None:
            labels=np.argmax(H[ei]-bet,axis=1); bet=bet+np.rint(.0625*Q*(np.bincount(labels,minlength=S)-1)).astype('int64')
        count+=len(chosen);trees.append([lam,len(chosen)]);dual+=now()-t
    t=now(); U,rec,terms,dc,spread=best; denom=Q*PT; Lnum=int(L.sum())*PT
    # Exact integer endpoints/ledger in denominator Q*PT. The displayed gap rounds its ratio upward.
    Gbit=np.nextafter(np.nextafter(float((U-Lnum)/denom),np.inf)/np.nextafter(S*logi(2.,T,False),-np.inf),np.inf)
    rec.update(k=k,n=n,method=method,raw_sha=digest(h),eps_sha=digest(eps),pair=pa.tolist(),power=p.tolist(),receiver=pack(v),L_pair=L.tolist(),LF_pair=LF.tolist(),LP_pair=None if LP is None else LP.tolist(),U=str(U),L=str(Lnum),den=str(denom),terms=list(map(str,terms)),G=Gbit,dc_tick=dc,Sd_tick=spread,roots=int(root.size),refinements=trees,fallback=fall)
    if prop is not None: rec['anchor_input']=pack(prop['anchor'])
    payload=json.dumps(rec,separators=(',',':')).encode()
    finish=now()
    return rec,payload,{'endpoint_ns':feat,'proposer_ns':net,'enclosure_ns':box,'matching_ns':dual,'primal_ns':primal,'receipt_ns':finish-t,'total_ns':finish-start}

