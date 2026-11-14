"""Build reviewer tables directly from the new scalar analysis outputs."""
from pathlib import Path
import shutil
import json
import pandas as pd

HERE=Path(__file__).resolve().parent
DATA=HERE/'reviewer_data'
SUP=HERE.parent/'supplementary'
LABELS={'det':'Deterministic search','hybrid':'Learned warm start','extra':'Equal-iteration deterministic','standalone':'Network only','legacy':'Subgradient baseline','cold':'Zero-price baseline','equal_match':'Matching + power refinement','sequential':'Sequential equal-power'}


def table(name,caption,label,headers,rows,after=''):
    text='\\begin{table}[htbp]\\centering\\small\n\\setlength{\\tabcolsep}{4pt}\n'
    text+=f'\\caption{{{caption}}}\\label{{{label}}}\n'
    text+='\\begin{tabular}{'+'l'*len(headers)+'}\\toprule\n'+' & '.join(headers)+r'\\'+'\n\\midrule\n'
    text+='\n'.join(' & '.join(map(str,r))+r'\\' for r in rows)
    text+='\n\\bottomrule\\end{tabular}\n\\end{table}\n'+after+'\n'
    (SUP/name).write_text(text,encoding='utf-8')


def build():
    for name in ['absolute_rates','absolute_rate_summary','gap_decomposition','gap_decomposition_summary','refinement_sweep','refinement_summary','compute_calls','compute_blocks','compute_summary','exact_binomial_intervals','horizon_intervals','hardware_calibration_HUB','hardware_calibration_LO']:
        path=DATA/(name+'.csv')
        if path.exists():shutil.copy2(path,SUP/'data'/('reviewer_'+name+'.csv'))
    d=pd.read_csv(DATA/'absolute_rate_summary.csv')
    table('reviewer_rates.tex','Absolute native rates at 10 dB. Each row has 512 topologies. Entries are medians in bit/s/Hz. The best ceiling is selected within each topology across all seven methods, then summarized. Retention is the median of paired lower/best-upper ratios. Repeated learned calls use the smallest lower and upper values separately; each remains valid.','supp:rates',
          ['$K$','Method','$L$','$U$','$U_{\\rm best}$','Retained (\\%)'],
          [[r.k,LABELS[r.method],f'{r.L_median:.4f}',f'{r.U_median:.4f}',f'{r.U_best_median:.4f}',f'{r.retention_median_pct:.3f}'] for r in d.itertuples()],
          'The archived matching control starts from equal powers and then allows feasible power refinement. Its label is made explicit here: it is not a fixed-equal-power comparator. Sequential equal-power retains 0.10 W per user. Exact fixed-equal-power enumeration is reported separately for the six-user hardware inputs.')
    d=pd.read_csv(DATA/'gap_decomposition_summary.csv')
    table('reviewer_decomposition.tex',r'Physical optimality brackets on 512 channels per size. For $V\in[V_-,V_+]$, upper slack lies in $[U-V_+,U-V_-]$ and action suboptimality in $[V_--L,V_+-L]$. Reported contribution endpoints are means; reference widths are median and maximum, all in bit/s/Hz. The 16-user reference is a physical bracket based on exact assignment of the upper-score table and feasible schedules, not an exact continuous optimum.','supp:decomposition',
          ['$K$','Mean upper slack','Mean action suboptimality','Median width','Maximum width'],
          [[r.k,f'[{r.slack_lo:.5f}, {r.slack_hi:.5f}]',f'[{r.suboptimality_lo:.5f}, {r.suboptimality_hi:.5f}]',f'{r.median_reference_width:.3g}',f'{r.max_reference_width:.3g}'] for r in d.itertuples()])
    d=pd.read_csv(DATA/'refinement_summary.csv')
    table('reviewer_refinement.tex',r'Refinement-budget sensitivity on the same 64 O1 tiles at 32 users and 10 dB. Each selected pair--tone rectangle is partitioned into 16 children. The original 32 choices are retained, and further entries are added in descending parent-score order with index tie-breaking. Every output is replayed against the full interval checker. Medians of components need not add.','supp:refinement',
          ['Refined entries','Tiles','Median $G$','Median $T_4$','Median time (ms)'],
          [[r.budget,r.n,f'{r.median_G:.6f}',f'{r.median_T4:.6f}',f'{r.median_ms:.2f}'] for r in d.itertuples()],
          r'All 7,936 pair--tone entries are refined in the last row. Expanding which entries receive this fixed 16-child partition does not reduce the median gap. This result does not establish an irreducible continuous-power gap: deeper partitions, other power prices or stronger local bounds were not tested in this sweep. Timings are exploratory single calls collected alongside other analysis jobs, and are not replacement primary deadline measurements.')
    d=pd.read_csv(DATA/'horizon_intervals.csv')
    rows=[]
    for r in d.query('M==0 and H==1 or M==16 and H in [256,1024]').itertuples():
        rows.append([('CDL-C' if r.family=='C' else r.family)+' '+r.arm,r.M,r.H,f'{r.wins}/{r.n}',f'[{100*r.lower:.1f}, {100*r.upper:.1f}]'])
    table('reviewer_horizon.tex',r'Stationary net-rate outcomes and exact two-sided 95\% binomial intervals over independent simulated topologies. Each comparison includes 128 test topologies. The zero-additional-pilot fraction is the same at all evaluated horizons. Both actions use the same least-squares observation; the comparator includes its feasible power refinement.','supp:table7',
          ['Channel / pilots','Extra blocks','$N_{\\rm blk}$','Positive gain',r'95\% interval (\%)'],rows)
    path=DATA/'compute_summary.csv'
    if path.exists():
        d=pd.read_csv(path)
        table('reviewer_compute.tex',r'Exploratory paired control after the primary experiment. The deterministic control receives three extra price iterations (10 at 32 users, 9 at 64), matching the number of price iterations in learned warm start. Each method is rerun three times on every topology in rotating order; a block uses its largest gap and median time. Equal iteration count is not equal wall time. The original confirmatory results remain unchanged.','supp:compute',
              ['$K$','Method','Iterations','Passes','Median $G$','Median ms'],
              [[r.k,LABELS[r.method],r.iterations,f'{r.passes}/{r.n}',f'{r.median_G:.5f}',f'{r.median_ms:.2f}'] for r in d.itertuples()],
              'The count-matched control shares the deterministic power table, update rule and candidate-action construction. It changes only the iteration budget. No new neural training or seed selection is performed. Background source-data transfers were active on the shared workstation; paired rotation limits order bias but does not establish an isolated latency benchmark.')
    if all((DATA/f'hardware_calibration_{mode}.json').exists() for mode in ['HUB','LO']):
        reports=[json.loads((DATA/f'hardware_calibration_{mode}.json').read_text()) for mode in ['HUB','LO']]
        rows=[]
        for label,key,fmt in [('Calibration frames','n_calibration','d'),('Test frames','n_test','d'),('Vector radius','qF','.4f'),('Projected radius','qP','.4f'),('Later rate above projected floor (\\%)','floor_coverage','pct'),('Later rate in combined interval (\\%)','interval_coverage','pct'),('Both residual events hold (\\%)','joint_score_coverage','pct'),('Median projected lower rate','median_LP','.3f'),('Median vector upper rate','median_UF','.3f'),('Median projected interval width','median_width','.3f'),('Positive projected floors','positive_floors','d'),('Median early ceiling minus equal-power optimum','median_equal_power_gap','.5g')]:
            rows.append([label,*[f'{100*r[key]:.2f}' if fmt=='pct' else format(r[key],fmt) for r in reports]])
        table('reviewer_hardware.tex',r'Chronological RENEW calibration against the observable second LTS. The first 256 eligible post-prefix frames calibrate the radii; all remaining eligible frames test the frozen rule. Rates and widths are bit/s/Hz; radii are in whitened digital channel units. Coverage fractions describe these temporally dependent recordings, without binomial population confidence intervals. The equal-power reference exhausts all 90 labelled pairings at 0.10 per user, with optimal linear combining, on every eligible early input. It is not the continuous-power optimum.', 'supp:hardware_calibration',['Quantity','HUB','LO'],rows,
              r'The projected interval is $[L_P,U_F]$; the combined lower endpoint for the interval-coverage diagnostic is $\\max(L_P,L_F)$. The early ceiling minus the enumerated equal-power optimum is reported separately from the achieved-action gap. The exhaustive comparison includes both calibration and test frames; calibrated coverage uses test frames only. The 70.26\% joint residual-event coverage on LO does not support a nominal 95\% calibration claim, even though the conservative rate floors cover all observed test rates.'.replace('\\\\max','\\max'))
    print('Reviewer numerical tables regenerated.')


if __name__=='__main__':build()
