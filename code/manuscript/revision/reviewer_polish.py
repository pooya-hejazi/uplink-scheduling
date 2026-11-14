"""Reviewer controls derived from frozen polish.py; default path must match it exactly."""
from matching import *
from solver import (T,Q,PT,PLO,PHI,now,digest,pack,normalized,project,nominal,ballarr,lower,logi,
                    cached_roots,priced,leaves,endpoints,repair)
from numba import njit
import json
def center(v):return v-v.mean()
def ticks(v):return np.rint(np.clip(center(v),-32,32)*Q).astype(np.int64)
def table(h,eps=0.,learned=None,refinement_budget=None):
    k,n,S=h.shape;g,G,r,I,J=endpoints(h,eps);nom=nominal(h,I,J)
    root,pen=cached_roots(g,G,r,I,J,T)
    lam=int(np.clip(round(np.median(nom[0]/(1+.1*nom[0]))),0,10)) if learned is None else int(np.clip(round(float(learned['lam'])),0,32))
    anchor=np.clip(1/max(lam,1)-1/np.maximum(G,1e-280),.05,.2) if learned is None else np.clip(learned['anchor'],.05,.2)
    H=priced(g,G,r,I,J,T,root,pen,lam,anchor)
    top=np.argsort(-H,axis=1,kind='stable')[:,:2]
    pool=(np.arange(len(I))[:,None]*S+top).ravel()
    priority=H.ravel() if learned is None else learned['priority'].ravel()
    chosen=pool[np.lexsort((pool,-priority[pool]))[:max(2,k*k//32)]]
    if refinement_budget is not None and refinement_budget != max(2,k*k//32):
        rest=np.setdiff1d(np.arange(H.size),chosen,assume_unique=True)
        extra=rest[np.lexsort((rest,-priority[rest]))[:max(0,refinement_budget-len(chosen))]]
        chosen=np.concatenate((chosen,extra))
    leaves(H,chosen,g,G,r,I,J,T,lam)
    if np.any(~np.isfinite(H)) or np.max(abs(H))>400:raise ArithmeticError('upper range')
    return np.ceil(H*Q).astype('int64'),nom,I,J,lam,chosen
@njit(cache=True)
def nbh(H,I,J,b,users):
    E,S=H.shape;K=2*S;top=np.full((K,S),-1e99); best=np.full(K,-1e99);idx=np.zeros(K,np.int64)
    for e in range(E):
        i,j=I[e],J[e];vmax=-1e99;tmax=0
        for t in range(S):
            val=H[e,t]-b[t];v=val-users[j];top[i,t]=max(top[i,t],v)
            v=val-users[i];top[j,t]=max(top[j,t],v)
            if val>vmax:vmax=val;tmax=t
        if vmax-users[j]>best[i]:best[i]=vmax-users[j];idx[i]=tmax
        if vmax-users[i]>best[j]:best[j]=vmax-users[i];idx[j]=tmax
    return idx,top
@njit(cache=True)
def shortlist(score,I,J,k):
    E,S=score.shape;allow=np.zeros(E,np.bool_);mid=np.zeros((k,S))
    for e in range(E):
        mid[I[e]]+=score[e];mid[J[e]]+=score[e]
    mid/=k-1
    for t in range(S):
        w=np.empty(E)
        for e in range(E):w[e]=score[e,t]-.5*(mid[I[e],t]+mid[J[e],t])
        order=np.argsort(-w);used=np.zeros(k,np.bool_);cnt=0
        for e in order:
            i,j=I[e],J[e]
            if not used[i] and not used[j]:
                allow[e]=True;used[i]=True;used[j]=True;cnt+=1
                if cnt==min(6,S): break
    return allow
@njit(cache=True)
def improve(pa,score,lookup,allowed):
    pa=pa.copy();S=len(pa)
    for _ in range(4):
        changed=False
        for s in range(S):
            for t in range(s+1,S):
                a,b=pa[s];c,d=pa[t]
                best=score[lookup[a,b],s]+score[lookup[c,d],t];winner=-1
                for ix,(u,v,w,x) in enumerate(((c,d,a,b),(a,c,b,d),(b,d,a,c),(a,d,b,c),(b,c,a,d))):
                    e1,e2=lookup[u,v],lookup[w,x]
                    if not (allowed[e1] and allowed[e2]):continue
                    z=score[e1,s]+score[e2,t]
                    if z>best+1e-11:best=z;winner=ix
                if winner>=0:
                    choices=((c,d,a,b),(a,c,b,d),(b,d,a,c),(a,d,b,c),(b,c,a,d))
                    u,v,w,x=choices[winner];pa[s,0]=u;pa[s,1]=v;pa[t,0]=w;pa[t,1]=x;changed=True
        if not changed:break
    return pa
def refine(h,pa,nom,initial=None):
    g,r,_=nom;k=len(h);S=k//2;s=np.arange(S);a,b=pa.T;e=edgeid(k,a,b);ga,gb=g[a,s],g[b,s];rr=r[e,s]
    def calc(p):
        x=p[a]/PT*ga;y=p[b]/PT*gb
        return float((np.log1p(x)+np.log1p(y)+2*np.log1p(-np.minimum(1-1e-15,rr*(x/(1+x))*(y/(1+y))))).sum())
    p=project(np.full(k,.1) if initial is None else initial);rate=calc(p)
    for step in [1,.5,.25,.125]:
        x=p[a]/PT*ga;y=p[b]/PT*gb;det=1+x+y+(1-rr)*x*y;grad=np.empty(k)
        grad[a]=ga*(2*(1+(1-rr)*y)/det-1/(1+x));grad[b]=gb*(2*(1+(1-rr)*x)/det-1/(1+y))
        trial=project(p/PT+step*.05*grad/max(1e-12,max(abs(grad))));rt=calc(trial)
        if rt>=rate:p,rate=trial,rt
    v=np.empty((S,2,h.shape[1]),complex)
    for j in [0,1]:
        u=h[pa[:,j],:,s];o=h[pa[:,1-j],:,s];pp=p[pa[:,1-j]]/PT
        v[:,j]=u-o*((pp*(o.conj()*u).sum(1))/(1+pp*(abs(o)**2).sum(1)))[:,None]
    return pa,p,v
def actionset(h,nom,I,J,matching_list,prior=None):
    k=len(h);S=k//2;s=np.arange(S);score=nom[2];scr=np.rint(score*2**27).astype('int64')
    E=len(I);mask=shortlist(score,I,J,k);lookup=np.zeros((k,k),int);lookup[I,J]=lookup[J,I]=np.arange(E)
    seq=np.arange(k).reshape(S,2);pool=[seq] + [a for a in matching_list]
    for m in pool:mask[edgeid(k,*m.T)]=True
    actions=[];signatures=set()
    def add(pa):
        key=tuple(edgeid(k,*pa.T))
        if key not in signatures:signatures.add(key);actions.append(pa.copy())
    add(seq)
    for m in pool:
        e=edgeid(k,*m.T);cols,_,_=assignment(scr[e]);pa=m[np.argsort(cols)];add(pa);add(improve(pa,score,lookup,mask))
    # Nominal scores only select which feasible actions to certify; the checked lower decides the winner.
    values=[score[edgeid(k,*a.T),s].sum() for a in actions]
    best=prior
    for j in np.argsort(values,kind='stable')[-min(3,len(actions)):]:
        pa,p,v=refine(h,actions[j],nom);L=lower(h,p,pa,v,np.zeros((S,2,2)),T)
        if best is None or int(L.sum())>int(best[3].sum()):best=pa,p,v,L
    return best,actions
def solve(h,mode='det',predict=None,*,extra_iterations=0,refinement_budget=None):
    start=now();k,n,S=h.shape
    # Warm proposal initializes the additional branch. Cold branch and cold feasible incumbent are bit-identical.
    if mode=='standalone':
        if predict is None:raise ValueError('standalone requires learned proposal')
        ti=now();I,J=np.triu_indices(k,1);nom=nominal(h,I,J);boxns=now()-ti
        ns=now();prop=predict(nom,k);netns=now()-ns
        tt=now();H,nom,I,J,lam,chosen=table(h,learned=prop);boxns+=now()-tt
    else:
        ti=now();H,nom,I,J,lam,chosen=table(h,refinement_budget=refinement_budget);boxns=now()-ti
        ns=now();prop=predict(nom,k) if predict is not None else None;netns=now()-ns if prop is not None else 0
    F=H/Q;ss=np.arange(S); matched=[];best=None;pool_actions=[];cold=None;branches=[];dc_history=[];pns=0;dns=0
    routes=['cold'] if mode=='det' else ['warm'] if mode=='standalone' else ['cold','warm']
    for route in routes:
        part=now();old_count=len(matched); baseline=nom[2] if mode!='standalone' else prop['score']
        pm=match(k,I,J,np.rint(baseline.max(1)*2**27).astype('int64'))[0];matched.append(pm)
        u=np.mean(np.log1p(.1*nom[0]),axis=1);f0=center(F.mean(0))
        # Assign two user slots per tone on isolated-user gains; use a single feasible midpoint for both duplicate slots.
        indiv=np.log1p(.1*nom[0]);_,_,pot=assignment(np.repeat(np.rint(indiv*Q).astype('int64'),2,axis=1))
        mass=center(2*pot.reshape(S,2).mean(1)/Q)
        c=(7 if k<=32 else 6)+extra_iterations
        if route=='warm':c=1 if mode=='standalone' else 3
        beta=ticks(prop['beta']) if route=='warm' else np.zeros(S,np.int64)
        route_best=None
        for it in range(c):
            if route=='cold' and it==1:beta=ticks(f0)
            if route=='cold' and it==2:beta=ticks(mass)
            w=(H-beta).max(1);alpha=np.rint(u*Q).astype('int64')
            try:
                m,y,z,val=match(k,I,J,w);e=edgeid(k,*m.T);cols,ay,ab=assignment(H[e]);A=int(H[e,cols].sum())
                R=val+int(beta.sum());dc=R-A
                if dc<0:raise ArithmeticError('negative conflict')
                rec=dict(witness='odd-set4',pairs=m.tolist(),y4=y.tolist(),z4=[(list(B),int(v)) for B,v in z],cols=cols.tolist(),ay=ay.tolist(),ab=ab.tolist(),beta=beta.tolist(),dc_tick=dc,A_tick=A)
            except ArithmeticError:
                beta,R=repair(H,I,J,alpha);w=(H-beta).max(1);m=pm;e=edgeid(k,*m.T);cols,ay,ab=assignment(H[e]);A=int(H[e,cols].sum());dc=None
                rec=dict(witness='P3',beta=beta.tolist(),alpha=alpha.tolist(),dc_tick=None,A_tick=None)
            matched.append(m);branches.append({'route':route,'it':it,'beta_sha':digest(beta),'R':int(R)})
            dc_history.append(None if dc is None else int(dc));key=(R,tuple(beta))
            if route_best is None or R<route_best[0]:route_best=(R,beta.copy(),m.copy(),ab.copy())
            if best is None or R<best[0]:best=(R,rec,w.copy())
            if it+1<c and not (route=='cold' and it<2):
                _,b,m0,price=route_best;e0=edgeid(k,*m0.T);adj=F[e0]-b/Q;pop=np.bincount(np.argmax(adj,axis=1),minlength=S)-1
                idx,_=nbh(F,I,J,b/Q,u);crowd=np.bincount(idx,minlength=S)/2-1
                anchor=center(price/Q); gain=.05/(1+max(0,it-2)*.35)
                beta=ticks(.42*b/Q+.58*anchor+gain*(.75*pop+.25*crowd))
        dns+=now()-part;pt=now()
        if mode=='standalone':
            cols,_,_=assignment(np.rint(baseline[edgeid(k,*pm.T)]*2**27).astype('int64'));pa=pm[np.argsort(cols)]
            pa,p,v=refine(h,pa,nom,prop['p']);L=lower(h,p,pa,v,np.zeros((S,2,2)),T)
            cold=(pa,p,v,L);pool_actions=[pa]
        else:cold,pool_actions=actionset(h,nom,I,J,matched,cold)
        pns+=now()-pt
    t=now();R,rec,w=best;pa,p,v,L=cold;ids=edgeid(k,*pa.T);s=np.arange(S);a=int(w[ids].sum());b=int(H[ids,s].sum());bs=sum(rec['beta']);P=k*PT//10
    U=lam*P*Q+R*PT;ln=int(L.sum())*PT;den=PT*Q
    terms=[(R-bs-a)*PT,(a-b+bs)*PT,lam*(P-int(p.sum()))*Q,(b-int(L.sum()))*PT+lam*int(p.sum())*Q]
    if min(terms)<0 or sum(terms)!=U-ln:raise ArithmeticError('incompatible ledger')
    if 'pairs' in rec:pool_actions.append(np.array(rec['pairs'])[np.argsort(rec['cols'])])
    poolm=max(pool_actions+[pa],key=lambda m:int(H[edgeid(k,*m.T),s].sum()))
    poolA=int(H[edgeid(k,*poolm.T),s].sum());rec['pool_pair']=poolm.tolist();rec['Sd_tick']=int(np.ptp(H-np.asarray(rec['beta']),axis=1).max())*S
    if poolA>R:raise ArithmeticError('pooled feasible assignment above dual')
    gp=float(np.nextafter(np.nextafter((U-ln)/den,np.inf)/np.nextafter(S*logi(2.,T,False),-np.inf),np.inf))
    rec.update(k=k,n=n,mode=mode,raw_sha=digest(h),lambda_price=lam,H_sha=digest(H),leaves=chosen.tolist(),power=p.tolist(),pair=pa.tolist(),receiver=pack(v),L_pair=L.tolist(),U=str(U),L=str(ln),den=str(den),terms=list(map(str,terms)),G=gp,A_pool_tick=poolA,R_tick=R,pool_count=len(pool_actions),branch_count=len(branches),proposals=branches,history_dc=dc_history)
    if mode=='standalone':rec['anchor_input']=pack(np.asarray(prop['anchor']))
    data=json.dumps(rec,separators=(',',':')).encode();end=now()
    return rec,data,dict(total_ns=end-start,enclosure_ns=boxns,neural_ns=netns,dual_ns=dns,primal_ns=pns,serialize_ns=end-t)

