"""Fresh split-conformal calibration of a single frozen nominal action; no test-set tuning."""
from solver import *
import csv
home=Path(__file__).resolve().parent;res=home/'results';res.mkdir(exist_ok=True)
def sampling(fam,part,i,db):
    ar=np.load(home/'data'/f'{part}_{fam}_{i:04d}.npz')
    h,_=normalized(ar['h'],32,db)
    seed=int.from_bytes(hashlib.sha256(f'LS-v1|{fam}|{part}|{i}'.encode()).digest()[:8],'little')
    rng=np.random.default_rng(seed); z=(rng.normal(size=h.shape)+1j*rng.normal(size=h.shape))/math.sqrt(2)
    return h,z
def stats(h,z,sigma):
    est=np.ascontiguousarray(h+sigma*z);I,J=np.triu_indices(32,1)
    pa,p,v=make_action(est,I,J,'subgrad')
    resid=(h-est)/sigma;full=float(np.linalg.norm(resid,axis=1).max())
    s=np.arange(len(pa)); mx=0.
    for a in [0,1]:
        unit=v[:,a]/np.linalg.norm(v[:,a],axis=1)[:,None]
        for b in [0,1]:mx=max(mx,float(abs((unit.conj()*resid[pa[:,b],:,s]).sum(1)).max()))
    return est,(pa,p,v),full,mx
def job():
    rows=[]; scores=[]
    for fam in ['C','UMa']:
        for db in [0,10,20]:
            for arm in ['fixed','scaled']:
                ep=32*(10**(db/10) if arm=='scaled' else 1); sigma=1/math.sqrt(ep)
                c=[]
                for i in range(256):
                    h,z=sampling(fam,'cal64',i,db); _,_,f,q=stats(h,z,sigma);c.append((f,q));scores.append((fam,db,arm,i,f,q))
                cf,cp=np.sort(np.asarray(c),axis=0)[250];ef=float(np.nextafter(sigma*cf,np.inf));pp=float(np.nextafter(sigma*cp,np.inf))
                for i in range(24):
                    h,z=sampling(fam,'pilot',i,db);start=now();est,act,f,q=stats(h,z,sigma)
                    # Measure online pilot-to-action and verifier only; truth-based scoring above is conservative timing overhead.
                    rec,_,tim=solve(est,'subgrad',eps=ef,proj=pp,action=act); elapsed=(now()-start)/1e6
                    norm=16*np.log(2); U=int(rec['U'])/int(rec['den']);LF=sum(rec['LF_pair'])/Q;LP=sum(rec['LP_pair'])/Q
                    pa,p,v=act;s=np.arange(16); true=0.
                    for a in [0,1]:
                        u,o=pa[:,a],pa[:,1-a];vv=v[:,a]
                        true+=np.log1p((p[u]/PT)*abs((vv.conj()*h[u,:,s]).sum(1))**2/((abs(vv)**2).sum(1)+(p[o]/PT)*abs((vv.conj()*h[o,:,s]).sum(1))**2)).sum()
                    ok=(not f<=cf or LF<=true+1e-10) and (not q<=cp or LP<=true+1e-10) and (not f<=cf or true<=U+1e-10)
                    if not ok:raise ArithmeticError('conditional soundness on pilot')
                    rows.append(dict(family=fam,db=db,arm=arm,Ep=ep,block=i,rank=251,epsF=ef,epsP=pp,hitF=int(f<=cf),hitP=int(q<=cp),joint=int(f<=cf and q<=cp),LF=LF/norm,LP=LP/norm,U=U/norm,G_P=(U-LP)/norm,retention=LP/U,ms=elapsed,verified=int(ok)))
                print(fam,db,arm,cf,cp,flush=True)
                with (res/'imperfect.csv').open('w',newline='') as f:
                    w=csv.DictWriter(f,rows[0]);w.writeheader();w.writerows(rows)
    with (res/'calibration_scores.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['family','db','arm','topology','T_F','T_P']);w.writerows(scores)
if __name__=='__main__':job()

