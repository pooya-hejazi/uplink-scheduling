"""Extend the original independent CDL-C calibration pool, without changing the locked n=256 estimator."""
from pathlib import Path
import hashlib,sys,csv,json
import numpy as np
root=Path(__file__).resolve().parent;old=root.parent/'Gate_2';sys.path.insert(0,str(root.parent/'Gate_2B'))
from inputs import guard
def gen():
    guard();sys.path.insert(0,str(old));import generate_native as g
    g.out=root/'calibration_sensitivity';g.out.mkdir(exist_ok=True)
    from cohorts import ids
    forbidden={r['seed'] for r in ids()}
    from cohorts import key
    for part,fs,n in [('fit',('analytic','A','B','C'),1024),('val',('analytic','A','B','C'),64),('cal',('C','UMa'),256),('cal64',('C','UMa'),256),('pilot',('A','B','C','UMa'),24)]:
        forbidden.update(key('gate2-v1|'+part,f,i) for f in fs for i in range(n))
    seeds=[key('Gate3-cal-size-v1','C',i) for i in range(768)];assert len(set(seeds))==768 and not forbidden.intersection(seeds)
    g.seed_for=lambda _,f,i:seeds[i];g.make('cal64','C',768)
    (root/'cal_size_manifest.csv').write_text('block,seed,sha256\n'+''.join(f"{i},{v},{hashlib.sha256((g.out/f'cal64_C_{i:04d}.npz').read_bytes()).hexdigest()}\n" for i,v in enumerate(seeds)))
def score():
    guard();from uncertainty import rows,putcsv,noise,normalized,imperfect
    base=rows(old/'results/calibration_scores.csv');rr=[]
    for arm in ('fixed','scaled'):
        sig=1/np.sqrt(32*(10 if arm=='scaled' else 1));a=[(float(r['T_F']),float(r['T_P'])) for r in base if r['family']=='C' and r['db']=='10' and r['arm']==arm];assert len(a)==256
        for i in range(768):
            raw=np.load(root/'calibration_sensitivity'/f'cal64_C_{i:04d}.npz')['h'];h,_=normalized(raw,32,10);_,_,f,q=imperfect.stats(h,noise('C',i,h,'extra-cal'),sig);a.append((f,q))
        tests=rows(root/'results'/f'imperfect_C_10_{arm}.csv')
        for n in [16,64,256,1024]:
            rank=int(np.ceil(.975*(n+1)));F,P=np.sort(a[:n],axis=0)[rank-1] if rank<=n else (np.inf,np.inf)
            hit=sum(float(q['T_F'])<=F and float(q['T_P'])<=P for q in tests);rr.append(dict(arm=arm,n=n,rank=rank,epsF=F*sig,epsP=P*sig,joint=hit,denominator=len(tests),finite=int(np.isfinite(F) and np.isfinite(P))))
    putcsv(root/'results/calibration_size.csv',rr)
if __name__=='__main__':(gen if sys.argv[1]=='generate' else score)()

