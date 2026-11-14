"""Feature-matched one-shot MLP and fixed-component swaps, evaluated after the primary freeze."""
import sys,os,json
from pathlib import Path
import numpy as np
here=Path(__file__).resolve().parent;old=here.parent/'Gate_2';sys.path.insert(0,str(here.parent/'Gate_2B'))
def design(x):
    # Teacher link features and one shared hidden layer; no third-party or published P1 weights are claimed.
    return np.asarray(x,np.float32)
def train():
    from sklearn.neural_network import MLPClassifier
    from sklearn.utils import check_random_state
    import pickle,hashlib
    paths=sorted((old/'teachers').glob('fit_*.npz'));assert len(paths)==4096;rng=np.random.default_rng(61831);model=MLPClassifier(hidden_layer_sizes=(32,),activation='relu',solver='adam',alpha=.0001,learning_rate_init=.001,random_state=61831,max_iter=1)
    for epoch in range(5):
        xs=[];ys=[]
        for j in rng.permutation(len(paths)):
            with np.load(paths[j]) as ar:
                x=ar['x'];S=x.shape[1];idx=ar['e'].astype(int)*S+np.arange(S);allx=x.reshape(-1,7);neg=rng.choice(np.setdiff1d(np.arange(len(allx)),idx,assume_unique=True),len(idx),replace=False)
                xs.extend([allx[idx],allx[neg]]);ys.extend([np.ones(len(idx)),np.zeros(len(neg))])
            if len(xs)==128:model.partial_fit(np.concatenate(xs),np.concatenate(ys),classes=[0,1]);xs=[];ys=[]
        assert not xs
    p=here/'results/pair_mlp.pkl';p.write_bytes(pickle.dumps(model));(here/'results/pair_mlp_sha.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest())
def run():
    from grid import guard,which,evaluate,source,normalized,nominal,edgeid,ticks,Q,T,lower,refine,shortlist,hashlib,PT,table,match,assignment,repair,solve,putcsv,now,fams,actionset,digest,replay
    import pickle
    guard();cfg,_,dest,n=which('test');model=pickle.loads((dest/'pair_mlp.pkl').read_bytes());rr=[];rpool=dest/'ablations';rpool.mkdir(exist_ok=True)
    with evaluate.worker(cfg['seed']) as pred:
        for i in range(n):
            pth=rpool/f'{i:03d}.csv'
            if pth.exists():continue
            rs=[]
            for f in fams:
                raw=source(f,i);h,_=normalized(raw,32,10);k,nrx,S=h.shape;s=np.arange(S);st=now()
                H,nom,I,J,lam,leaves=table(h);prop=pred(nom,k);base,_,_=solve(h);replay(h,base);den=int(base['den'])*S*np.log(2);coldL=int(base['L'])/den;coldU=int(base['U'])/den
                scr=nom[2];baseprice=np.array(base['beta']);eq=np.full(k,.1);cc=np.clip(1/max(lam,1)-1/np.maximum(nom[0],1e-280),.05,.2)
                def primal(score,p):
                    m=match(k,I,J,np.rint(score.max(1)*2**27).astype('int64'))[0];idx=edgeid(k,*m.T);col,_,_=assignment(np.rint(score[idx]*2**27).astype('int64'));pa,pw,vr=refine(h,m[np.argsort(col)],nom,p);return float(lower(h,pw,pa,vr,np.zeros((S,2,2)),T).sum())/(Q*S*np.log(2))
                def dual(A,b):
                    w=(A-b).max(1);mv=match(k,I,J,w)[3];return (int(mv)+int(b.sum())+lam*(k*PT//10)*Q/PT)/(Q*S*np.log(2))
                mlp=model.predict_proba(evaluate.feat(nom,k).reshape(-1,7))[:,1].reshape(scr.shape)
                def add(m,lo,hi):assert lo<=hi;rs.append(dict(family=f,block=i,k=k,mode=m,L=lo,U=hi,G=hi-lo))
                add('deterministic_polish',coldL,coldU);add('swap_learned_primal',primal(prop['score'],prop['p']),coldU)
                add('one_shot_MLP_projected',primal(mlp,eq),dual(H,np.zeros(S,dtype=np.int64)))
                # Switch only the indicated field at fixed deterministic lambda and pilot schedule.
                add('swap_learned_beta',coldL,dual(H,ticks(prop['beta'])))
                baseprio=H.astype(float);cp0=dict(prop,lam=lam,priority=baseprio,anchor=cc)
                aa=table(h,learned=dict(cp0,anchor=prop['anchor']))[0];add('swap_learned_anchor',coldL,dual(aa,baseprice))
                aa=table(h,learned=dict(cp0,priority=prop['priority']))[0];add('swap_learned_priority',coldL,dual(aa,baseprice))
                alpha=np.rint(np.mean(np.log1p(.1*nom[0]),axis=1)*Q).astype('int64');bp,rp=repair(H,I,J,alpha);add('P3_repair_only',coldL,(lam*(k*PT//10)*Q/PT+rp)/(Q*S*np.log(2)))
            putcsv(pth,rs)
            if i%32==31:print('ablations',i+1,flush=True)
if __name__=='__main__':(train if sys.argv[1]=='train' else run)()

