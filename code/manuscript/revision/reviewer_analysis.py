"""Exploratory reviewer analyses; archived confirmatory inputs are read-only."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'reviewer_data'
OUT.mkdir(exist_ok=True)
for name in ('Gate_2', 'Gate_2B', 'Gate_3'):
    sys.path.insert(0, str(ROOT / name))


def read_many(folder):
    return pd.concat([pd.read_csv(p) for p in sorted((ROOT / folder).glob('*.csv'))], ignore_index=True)


def save(name, rows):
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    frame.to_csv(OUT / (name + '.csv'), index=False)
    return frame


def rates():
    grid = read_many('Gate_3/results/grid_native').query('db == 10')
    times = pd.read_csv(ROOT / 'Gate_3/results/times.csv')
    keys = ['family', 'block', 'k', 'method']
    primary = times.groupby(keys, as_index=False).agg(L=('Lbit', 'min'), U=('Ubit', 'min'))
    small = grid.query('k == 16').rename(columns={'Lbit': 'L', 'Ubit': 'U'})
    matrix = read_many('Gate_3/results/matrix_methods').query("family in ['A','B','C','UMa'] and db == 10 and k == 16")
    controls = read_many('Gate_3/results/controls_native').query('db == 10')
    cols = keys + ['L', 'U']
    data = pd.concat([primary[cols], small[cols], matrix[cols], controls[cols]], ignore_index=True)
    assert not data.duplicated(keys).any() and len(data) == 512 * 3 * 7
    data['U_best'] = data.groupby(keys[:3]).U.transform('min')
    data['gap_to_best'] = data.U_best - data.L
    data['retention_pct'] = 100 * data.L / data.U_best
    assert (data.gap_to_best > -1e-10).all()
    save('absolute_rates', data)
    summary = data.groupby(['k', 'method']).agg(n=('L', 'size'), L_median=('L', 'median'), U_median=('U', 'median'), U_best_median=('U_best', 'median'), gap_to_best_median=('gap_to_best', 'median'), retention_median_pct=('retention_pct', 'median')).reset_index()
    save('absolute_rate_summary', summary)
    cis = []
    for label, x, n, alpha, sides in [('det32',506,512,.025,1),('det64',504,512,.025,1),('coverage_C',120,128,.05,2),('coverage_UMa',127,128,.05,2)]:
        tail = alpha / sides
        cis.append(dict(comparison=label, x=x, n=n, confidence=1-alpha, sides=sides, lower=beta.ppf(tail,x,n-x+1), upper=1. if sides==1 else beta.ppf(1-tail,x+1,n-x)))
    save('exact_binomial_intervals', cis)
    net = pd.read_csv(ROOT/'Gate_3/results/net_benefit.csv')
    net = net.groupby(['family','arm','H','M'],as_index=False).agg(n=('win','size'),wins=('win','sum'),affordable=('affordable','min'))
    net['lower'] = [0 if x==0 else beta.ppf(.025,x,n-x+1) for x,n in zip(net.wins,net.n)]
    net['upper'] = [1 if x==n else beta.ppf(.975,x+1,n-x) for x,n in zip(net.wins,net.n)]
    save('horizon_intervals',net)
    print(summary.to_string(index=False), flush=True)


def decomposition():
    from inputs import analytic
    from polish import solve
    from verify import replay
    refs = pd.read_csv(ROOT/'Gate_3/results/oracle_intervals.csv')
    exact = pd.read_csv(ROOT/'Gate_3/results/exact_two.csv').set_index(['family','block'])
    rows = []
    for (fam, block), group in refs.groupby(['family','block']):
        raw = analytic(fam,block)
        scale = np.sqrt(10/(.1*np.median(np.mean(abs(raw.astype(complex))**2,axis=1))))
        for ref in group.itertuples():
            k=ref.k; s=k//2; norm=s*np.log(2)
            h=np.ascontiguousarray(raw[:k,:,np.floor(np.arange(s)*64/s).astype(int)].astype(complex)*scale)
            r,_,_=solve(h);replay(h,r)
            lo,hi=(exact.loc[(fam,block)][['lo_nats','hi_nats']] if k==2 else (ref.lo_nats,ref.hi_nats))
            L=int(r['L'])/int(r['den'])/norm; U=int(r['U'])/int(r['den'])/norm
            vlo=max(L,lo/norm);vhi=min(U,hi/norm)
            assert vlo <= vhi + 1e-10 and abs(r['G']-ref.candidate_G)<1e-10
            rows.append(dict(family=fam,block=block,k=k,L=L,U=U,V_lo=vlo,V_hi=vhi,slack_lo=max(0,U-vhi),slack_hi=U-vlo,suboptimality_lo=max(0,vlo-L),suboptimality_hi=max(0,vhi-L),reference_width=max(0,vhi-vlo),kind='continuous reference'))
        if block%32==31: print('decomposition',fam,block+1,flush=True)
    grid=read_many('Gate_3/results/grid_native').query('db==10 and k==16')
    for r in grid.itertuples():
        vlo=max(r.Lbit,r.dp_uniform_L,r.dp_refine_L,r.priced_dp_SQP_L);vhi=min(r.Ubit,r.certified_dp_U)
        assert vlo<=vhi+1e-9
        rows.append(dict(family=r.family,block=r.block,k=16,L=r.Lbit,U=r.Ubit,V_lo=vlo,V_hi=vhi,slack_lo=max(0,r.Ubit-vhi),slack_hi=r.Ubit-vlo,suboptimality_lo=max(0,vlo-r.Lbit),suboptimality_hi=max(0,vhi-r.Lbit),reference_width=max(0,vhi-vlo),kind='physical bracket using exact table DP',exact_table_relaxation_loss=r.loss))
    d=save('gap_decomposition',rows)
    save('gap_decomposition_summary',d.groupby('k').agg(n=('L','size'),gap=('U',lambda x:0),slack_lo=('slack_lo','mean'),slack_hi=('slack_hi','mean'),suboptimality_lo=('suboptimality_lo','mean'),suboptimality_hi=('suboptimality_hi','mean'),median_reference_width=('reference_width','median'),max_reference_width=('reference_width','max')).drop(columns='gap').reset_index())
    assert len(d)==512*5
    print('decomposition complete',len(d),flush=True)


def sweep():
    from grid import source
    from solver import normalized
    from reviewer_polish import solve
    from verify import replay
    rows=[]
    for i in range(64):
        path=OUT/f'refinement_{i:03d}.csv'
        if path.exists():rows.extend(pd.read_csv(path).to_dict('records'));continue
        h,_=normalized(source('O1_60',i),32,10);part=[]
        for budget in (32,128,512,7936):
            r,_,t=solve(h,refinement_budget=budget);replay(h,r);norm=int(r['den'])*16*np.log(2)
            part.append(dict(block=i,budget=budget,refined=len(r['leaves']),G=r['G'],L=int(r['L'])/norm,U=int(r['U'])/norm,T4=int(r['terms'][3])/norm,ms=t['total_ns']/1e6))
        save(f'refinement_{i:03d}',part);rows.extend(part)
        print('refinement',i+1,'/64',flush=True)
    d=save('refinement_sweep',rows)
    save('refinement_summary',d.groupby('budget').agg(n=('G','size'),median_G=('G','median'),median_T4=('T4','median'),median_ms=('ms','median')).reset_index())


def compute():
    from grid import source
    from solver import normalized
    import campaign
    from reviewer_polish import solve as extended
    from verify import replay
    import evaluate
    from threadpoolctl import threadpool_limits
    cfg=json.loads((ROOT/'Gate_2B/results/freeze.json').read_text())
    # Preserve historical timing logs; the worker's code/checkpoint root stays frozen.
    oldres=evaluate.res;evaluate.res=OUT
    rows=[]
    with threadpool_limits(1), evaluate.worker(cfg['seed']) as pred:
        for fam in ('A','B','C','UMa'):
            for i in range(128):
                path=OUT/f'compute_{fam}_{i:03d}.csv'
                if path.exists():
                    try:
                        completed=pd.read_csv(path)
                        if len(completed)==18 and not completed.isna().any().any():
                            rows.extend(completed.to_dict('records'));continue
                    except (pd.errors.ParserError,pd.errors.EmptyDataError):pass
                part=[]
                for k in (32,64):
                    h,_=normalized(source(fam,i),k,10)
                    for rep in range(3):
                        order=['det','extra','hybrid'];shift=(i+rep+(k==64))%3;order=order[shift:]+order[:shift]
                        for method in order:
                            r,_,t=(extended(h,extra_iterations=3) if method=='extra' else campaign.solve(h,method,pred if method=='hybrid' else None))
                            replay(h,r)
                            part.append(dict(family=fam,block=i,k=k,rep=rep,method=method,G=r['G'],ms=t['total_ns']/1e6,iterations=r['branch_count'],receipt_sha256=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()))
                save(f'compute_{fam}_{i:03d}',part);rows.extend(part)
                if i%8==7:print('paired compute',fam,i+1,'/128',flush=True)
    evaluate.res=oldres
    d=save('compute_calls',rows)
    blocks=d.groupby(['family','block','k','method'],as_index=False).agg(G=('G','max'),ms=('ms','median'),iterations=('iterations','first'))
    blocks['ok']=(blocks.G<=.15)&(blocks.ms<=blocks.k.map({32:250,64:1000}))
    save('compute_blocks',blocks)
    save('compute_summary',blocks.groupby(['k','method']).agg(n=('ok','size'),passes=('ok','sum'),median_G=('G','median'),median_ms=('ms','median'),iterations=('iterations','first')).reset_index())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('task',choices=['rates','decomposition','sweep','compute']);args=parser.parse_args()
    globals()[args.task]()
