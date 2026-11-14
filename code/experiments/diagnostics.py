"""Additional audit values; never change selection or deployed methods."""
from grid import *
import pandas as pd
from scipy.stats import rankdata
def valid():
    cfg,_,dest,n=which('pilot');out=[]
    # Check the prespecified primary/control ranking over the original validation cohort as well.
    with evaluate.worker(cfg['seed']) as pred:
        for i in range(64):
            for f in ('analytic','A','B','C'):
                raw=np.load(old/'data'/f'val_{f}_{i:04d}.npz')['h'];db=(0,10,20)[(i//3)%3];h,_=normalized(raw,len(raw),db)
                for m in ('legacy','det','standalone','hybrid'):
                    r,_,ti=runone(h,m,pred);out.append(dict(family=f,block=i,k=len(raw),db=db,method=m,G=r['G'],ms=ti['total_ns']/1e6))
    putcsv(dest/'validation_controls.csv',out)
def diagnostic(phase):
    cfg,root,dest,n=which(phase);out=[]
    for idx in range(n):
        with gzip.open(dest/'shards'/f'{idx:03d}.jsonl.gz','rt') as ff:
            for line in ff:
                x=json.loads(line);f,i,k,db,m,rep=x['id'];r=x['receipt']
                if rep:continue
                den=int(r['den'])*(k//2)*np.log(2);sf=Q*(k//2)*np.log(2)
                pdict=dict(family=f,block=i,k=k,method=m,G=r['G'],dc='' if r['dc_tick'] is None else r['dc_tick']/sf,Sd=r['Sd_tick']/sf,odds=len(r.get('z4',r.get('z',[]))),witness=r['witness'])
                for j,v in enumerate(r['terms']):pdict['term'+str(j+1)]=int(v)/den
                pdict['pooled_raise']=((r['A_pool_tick']-r['A_tick'])/sf if 'A_pool_tick' in r and r['A_tick'] is not None else '')
                pdict['dual_fall']=((r['proposals'][0]['R']-r['R_tick'])/sf if 'proposals' in r else '')
                pdict['unique_prices']=len(set(x['beta_sha'] for x in r.get('proposals',[])))
                out.append(pdict)
    putcsv(dest/'conflict_attribution.csv',out);p=pd.DataFrame(out);p[['dc','pooled_raise','dual_fall']]=p[['dc','pooled_raise','dual_fall']].apply(pd.to_numeric,errors='coerce')
    p.groupby(['k','family','method']).median(numeric_only=True).to_csv(dest/'conflict_strata.csv')
def measure_baseline(phase):
    cfg,root,dest,n=which(phase);x=pd.read_csv(dest/'times.csv');r=pd.read_csv(dest/'block_decisions.csv');det=r[r.method=='det'];hyb=r[r.method=='hybrid']
    v=det.merge(hyb,on=['family','block','k'],suffixes=('_det','_hyb'));assert (v.G_hyb<=v.G_det+1e-12).all()
    # First *completed* qualifying receipt among standalone timed policies: no intermediate checkpoints were timed.
    b=r.groupby(['k','family','block']);rr=[]
    for (k,f,i),o in b:
        pp=o[o.ok==1];first='' if pp.empty else pp.loc[pp.ms.idxmin(),'method'];firstms='' if pp.empty else pp.ms.min();rr.append(dict(k=k,family=f,block=i,first_complete_method=first,first_complete_ms=firstms))
    putcsv(dest/'first_complete_receipt.csv',rr)
    stats=[]
    for k in [32,64]:
        for fam in ['all','A','B','C','UMa']:
            for m in methods:
                o=r[(r.k==k)&(r.method==m)];o=o[o.family==fam] if fam!='all' else o
                a=o.sort_values(['family','block']);groups=a.family.unique();N=len(a)//len(groups)
                od=a.G.values.reshape(len(groups),N);lt=a.ms.values.reshape(len(groups),N);rng=np.random.default_rng(19073)
                count=[]
                for c in grid:
                    ok=(od<=c)&(lt<={32:250,64:1000}[k]);okg=od<=c
                    samples=[];gaps=[]
                    for rep in range(20):
                        ix=rng.integers(N,size=(500,len(groups),N));fs=np.arange(len(groups))[None,:,None];samples.extend(ok[fs,ix].mean((1,2)));gaps.extend(okg[fs,ix].mean((1,2)))
                    stats.append(dict(k=k,family=fam,method=m,tau=c,n=len(a),gap_fraction=okg.mean(),gap_ci_lo=np.quantile(gaps,.025),gap_ci_hi=np.quantile(gaps,.975),joint_fraction=ok.mean(),joint_ci_lo=np.quantile(samples,.025),joint_ci_hi=np.quantile(samples,.975)))
    putcsv(dest/'threshold_intervals.csv',stats)
if __name__=='__main__':
    if sys.argv[1]=='validation':valid()
    else:diagnostic(sys.argv[1]);measure_baseline(sys.argv[1])

