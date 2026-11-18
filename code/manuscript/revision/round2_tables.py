"""Generate round-two supplementary tables from the stored scalar calculations."""
from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd

from reviewer_tables import table as base_table, LABELS

HERE = Path(__file__).resolve().parent
OUT = HERE/'round2_data'
SUP = HERE.parent/'supplementary'


def bracket(a, b):
    def number(x):
        return f'{x:.2g}' if 0 < abs(x) < .00005 else f'{x:.5f}'
    return f'[{number(a)}, {number(b)}]'


def table(name, caption, label, headers, rows, after=''):
    base_table(name, caption, label, headers, rows, after)
    if after:
        path = SUP/name
        text = path.read_text(encoding='utf-8')
        assert text.count('\\end{table}\n'+after) == 1
        text = text.replace('\\end{table}\n'+after,
                            '\\par\\medskip\\begin{minipage}{\\linewidth}\\small\n'+after+
                            '\n\\end{minipage}\n\\end{table}')
        path.write_text(text, encoding='utf-8')


def build():
    from round2_summary import build as summarize
    summarize()
    keep = ['iteration_paired_tests', 'latency_increments', 'achieved_rate_comparison',
            'decomposition_distribution', 'integer_table_reference', 'time_budget_pilot',
            'time_control_calls', 'time_control_blocks', 'time_control_summary', 'time_control_paired_tests',
            'o1_budget_entries', 'o1_depth', 'o1_depth_summary', 'o1_small_references']
    keep += [f'hardware_{kind}_{mode}' for kind in ('phase', 'phase_rotations', 'comparison') for mode in ('HUB', 'LO')]
    diagnostic = HERE/'round3_data'
    scale = [json.loads((diagnostic/f'hardware_scale_{mode}.json').read_text()) for mode in ('HUB', 'LO')]
    pd.DataFrame(scale).to_csv(diagnostic/'hardware_scale_summary.csv', index=False)
    for path in diagnostic.glob('*.csv'):
        shutil.copy2(path, SUP/'data'/('round3_'+path.name))
    for name in keep:
        path = OUT/(name+'.csv')
        assert path.exists(), path
        shutil.copy2(path, SUP/'data'/('round2_'+name+'.csv'))

    rates = pd.read_csv(HERE/'reviewer_data/absolute_rates.csv')
    groups = rates.groupby(['k', 'family', 'block'])
    assert groups.size().eq(7).all() and not rates.duplicated(['k','family','block','method']).any()
    best = groups.U.transform('min')
    assert np.allclose(best, rates.U_best, rtol=0, atol=2e-12) and (rates.L <= best + 2e-12).all()
    cold = rates.loc[rates.method == 'cold'].copy()
    cold['own'] = cold.U - cold.L <= .15
    cold['common'] = cold.U_best - cold.L <= .15
    assert not (cold.own & ~cold.common).any()
    by_profile = cold.groupby(['k', 'family']).agg(n=('block', 'size'), own=('own', 'sum'), common=('common', 'sum'))
    by_profile.to_csv(SUP/'data/action_common_ceiling_counts.csv')
    pooled = by_profile.groupby(level='k').sum()
    assert pooled.n.eq(512).all()
    summary = pd.read_csv(HERE/'reviewer_data/absolute_rate_summary.csv')
    rows = [[r.k, LABELS[r.method], f'{r.L_median:.4f}', f'{r.U_median:.4f}',
             f'{r.U_best_median:.4f}', f'{r.retention_median_pct:.3f}'] for r in summary.itertuples()]
    counts = ', '.join(str(int(pooled.loc[k, 'common'])) for k in (16,32)) + ' and ' + str(int(pooled.loc[64, 'common']))
    own = ', '.join(str(int(pooled.loc[k, 'own'])) for k in (16,32)) + ' and ' + str(int(pooled.loc[64, 'own']))
    after = ('The three matching controls share the same starting pairs and four power-refinement steps. '
             'They give identical lower endpoints on each topology. Sequential equal-power uses 0.10 W per user. '
             'At 16, 32 and 64 users, the zero-price decision meets the 0.15-bit/s/Hz gap on '
             f'{own} of 512 topologies using its own ceiling, and on {counts} using the common ceiling. '
             'These paired comparisons use rate alone. Supplementary Table 6 Source Data gives the counts by profile.')
    table('reviewer_rates.tex',r'Native rates at 10 dB on 512 topologies per size. Rates are medians in bit/s/Hz. '
          r'$U_{\rm best}$ is the smallest verified ceiling across all seven methods on the same topology. '
          r'Retention is the median of $100 L/U_{\rm best}$. Across repeated calls each endpoint minimum is taken separately.',
          'supp:rates',['$K$', 'Method', '$L$', '$U$', r'$U_{\rm best}$', r'Retained (\%)'],rows,after)
    for name in ('fixed_filter_checks', 'two_user_root_widths'):
        shutil.copy2(HERE/'action_data'/(name+'.csv'), SUP/'data'/('action_'+name+'.csv'))

    prior = pd.read_csv(HERE/'reviewer_data/compute_summary.csv')
    current = pd.read_csv(OUT/'time_control_summary.csv')
    rows = []
    for campaign, data in [('Iteration run', prior), ('Time-budget run', current)]:
        rows.append([r'\multicolumn{6}{l}{\textit{'+campaign+r'}}'])
        for r in data.itertuples():
            label = 'Time-budget deterministic' if r.method == 'time' else LABELS[r.method]
            rows.append([r.k, label, r.iterations, f'{r.passes}/{r.n}', f'{r.median_G:.5f}', f'{r.median_ms:.2f}'])
    tests = pd.concat([pd.read_csv(OUT/'iteration_paired_tests.csv'), pd.read_csv(OUT/'time_control_paired_tests.csv')])
    after = r'\par\smallskip\noindent\begin{tabular}{llrrrrr}\toprule Control & $K$ & Both & Control only & Learned only & Neither & Exact $P$\\\midrule'+'\n'
    for r in tests.itertuples():
        after += ' & '.join(map(str, ['Iteration' if r.control == 'extra' else 'Time budget', r.k, r.both_pass, r.control_only, r.treatment_only, r.neither, f'{r.exact_two_sided_p:.5g}']))+r'\\'+'\n'
    after += r'\bottomrule\end{tabular}\par\smallskip'+'\n'
    after += r'Each campaign uses the same 512 topologies, three repeats and rotating method order. A topology uses its largest gap and median time. The iteration control adds three deterministic price updates. For the time-budget control, 16 hash-selected topologies calibrate only timing; the resulting 38/63 deterministic iterations are frozen before the full comparison. The control shares the original power table, update rule and candidate construction. No network is retrained. Absolute times differ between campaigns; matching their medians does not impose equal time on each topology. Exact two-sided McNemar tests condition on discordant topology pairs. All rates are bit/s/Hz.'
    table('reviewer_compute.tex', 'Paired iteration- and time-budget controls. Passes require the original gap and deadline criteria. The original confirmatory campaign is unchanged.', 'supp:compute',
          ['$K$', 'Method', 'Iterations', 'Passes', 'Median $G$', 'Median ms'], rows, after)

    dist = pd.read_csv(OUT/'decomposition_distribution.csv')
    rows = []
    for k in (2, 4, 6, 8):
        for stat in ('mean', 'q25', 'median', 'q75'):
            r = dist.query('k == @k and statistic == @stat').iloc[0]
            family = 'Analytic / roots' if k == 2 else 'Analytic / 192 splits'
            rows.append([k if stat == 'mean' else '', family if stat == 'mean' else '',
                         {'q25':'25th percentile', 'q75':'75th percentile'}.get(stat, stat.capitalize()),
                         bracket(r.slack_lo, r.slack_hi), bracket(r.suboptimality_lo, r.suboptimality_hi)])
    integer = pd.read_csv(OUT/'integer_table_reference.csv')
    after = r'\par\smallskip\noindent\begin{tabular}{llrr}\toprule Family / reference & Statistic & Slack above table & Shortfall below table\\\midrule'+'\n'
    for stat, fn in [('Mean', np.mean), ('25th percentile', lambda x: np.quantile(x, .25)), ('Median', np.median), ('75th percentile', lambda x: np.quantile(x, .75))]:
        after += ' & '.join(['Native 3GPP / exact DP' if stat == 'Mean' else '', stat, f'{fn(integer.slack_above_table_reference):.5f}', f'{fn(integer.shortfall_below_table_reference):.5f}'])+r'\\'+'\n'
    after += r'\bottomrule\end{tabular}\par\smallskip'+'\n'
    after += r'For $K=2$, rational polynomial-root isolation encloses the physical optimum. At $K=4,6,8$, continuous box references allow 192 splits and remain unresolved at $10^{-6}$ bit/s/Hz. Quartiles and medians summarize each bracket endpoint separately; the 25th--75th percentile rows describe their IQRs. At $K=16$, exact integer DP optimizes the upper-score table, giving $V_{\rm tab}\geq V^*$; the displayed $U-V_{\rm tab}$ and $V_{\rm tab}-L$ are an algebraic table-reference split, not physical slack and action loss. No trend across these different channel families is implied. All entries use 512 topologies per size and bit/s/Hz.'
    widths = dist[dist.statistic == 'median']
    roots = pd.read_csv(HERE/'action_data/two_user_root_widths.csv')
    assert len(roots) == 512
    after += f' The two-user median and maximum root widths are {roots.G_oracle.median():.6g} and {roots.G_oracle.max():.6g} bit/s/Hz. These use outward conversion of the difference in nats. For the box references the median and maximum widths are '+', '.join(f'$K={int(r.k)}$: {r.reference_width:.6g}; {r.maximum_reference_width:.6g}' for r in widths.query('2 < k < 16').itertuples())+'.\n'
    table('reviewer_decomposition.tex', r'Ceiling slack and shortfall to the rate floor. A reference $V^*\in[V_-,V_+]$ puts $U-V^*$ in $[U-V_+,U-V_-]$ and $V^*-L$ in $[V_--L,V_+-L]$. The latter includes $R_{\rm fix}-L$.', 'supp:decomposition',
          ['$K$', 'Channel / reference', 'Statistic', 'Ceiling slack', 'Optimum to floor'], rows, after)

    budgets = pd.read_csv(OUT/'o1_budget_entries.csv')
    depth = pd.read_csv(OUT/'o1_depth_summary.csv')
    rows = []
    for budget, group in budgets.groupby('budget'):
        assert group.changed_from_parent.max() == 0 and len(group) == 64
        coverage = group.scheduled_entries_in_shortlist
        rows.append([budget, 0, f'{coverage.min()}/{coverage.median():g}/{coverage.max()}', '1.119582', '1.113253'])
    after = r'\par\smallskip\noindent\begin{tabular}{rrrr}\toprule Children per selected entry & Median changed entries & Median $G$ & Median $T_4$\\\midrule'+'\n'
    for r in depth.itertuples():
        after += f'{r.children} & {r.median_changed:g} & {r.median_G:.6f} & {r.median_T4:.6f}'+r'\\'+'\n'
    after += r'\bottomrule\end{tabular}\par\smallskip'+'\n'
    small = pd.read_csv(OUT/'o1_small_references.csv')
    assert len(small) == 128 and small.resolved.all()
    after += r'\noindent\begin{tabular}{rlrrrr}\toprule $K$ & Statistic & Gap & Ceiling slack & Optimum to floor & Reference width\\\midrule'+'\n'
    for k, group in small.groupby('k'):
        for stat, fn in [('Mean', np.mean), ('Median', np.median)]:
            after += f'{k} & {stat} & {fn(group.U-group.L):.6f} & '+bracket(fn(group.slack_lo), fn(group.slack_hi))+' & '+bracket(fn(group.suboptimality_lo), fn(group.suboptimality_hi))+f' & {fn(group.reference_width):.3g}'+r'\\'+'\n'
    after += r'\bottomrule\end{tabular}\par\smallskip'+'\n'
    binding = pd.read_csv(diagnostic/'o1_binding_bounds.csv')
    assert len(binding) == 64 and binding.entries.sum() == 507904
    assert (binding.tangent_strict == binding.entries).all() and not binding.child_below_tangent.any()
    after += r'The width sweep partitions every chosen rectangle into 16 children. No upper-table tick changes at any budget. Direct comparison of all 507,904 entries across the 64 tiles confirms that each parent concave-log tangent bound is below both its box bound and its maximum child mixed bound; the tangent remains binding across all four width budgets. The action has 16 scheduled entries; the shortlist column gives their minimum/median/maximum counts in the refined set. The depth sweep refines these entries into 16, 64 or 256 children with the original action, powers and tone/power prices fixed. Matching witnesses and the four-term identity are rebuilt and checked. Small references use the nested first two and four users of all 64 O1 tiles with the original channel normalization. Two-user roots have outward numerical enclosures; four-user complete labelled enumeration uses validated continuous Taylor/box bounds to $10^{-6}$ bit/s/Hz. Rates are bit/s/Hz; different $K$ have different feasible problems.'
    table('reviewer_refinement.tex', 'O1 enclosure width, partition depth and small continuous references at 10 dB. Each experiment uses the same 64 guarded tiles.', 'supp:refinement',
          ['Entries refined', 'Entries changed', 'Scheduled in shortlist', 'Median $G$', 'Median $T_4$'], rows, after)

    reports = [json.loads((OUT/f'hardware_phase_{mode}.json').read_text()) for mode in ('HUB', 'LO')]
    comparison = pd.concat([pd.read_csv(OUT/f'hardware_comparison_{mode}.csv') for mode in ('HUB', 'LO')], ignore_index=True)
    print('Hardware summary columns:', comparison.columns.tolist())
    quantities = [('Vector radius', 'qF', '.3f'), ('Projected radius', 'qP', '.3f'), ('Radius ratio', 'radius_ratio', '.3f'),
                  ('Median vector floor $L_F$', 'median_LF', '.3f'), ('Median projected floor $L_P$', 'median_LP', '.3f'),
                  ('Median later-LTS rate', 'median_later_rate', '.3f'), ('Median vector ceiling $U_F$', 'median_UF', '.3f'),
                  ('Median width $U_F-L_P$', 'median_width', '.3f'),
                  (r'Median paired floor / later rate (\%)', 'median_paired_floor_pct', '.2f'),
                  (r'Projected floor coverage (\%)', 'floor_coverage', 'pct'), (r'Combined interval coverage (\%)', 'interval_coverage', 'pct'),
                  (r'Joint residual-event coverage (\%)', 'joint_score_coverage', 'pct')]
    # Input schema is checked here so a changed summary cannot silently relabel a result.
    assert len(comparison) == 4
    records = comparison.to_dict('records')
    rows = [[label, *[f'{100*r[key]:.2f}' if fmt == 'pct' else format(r[key], fmt) for r in records]] for label, key, fmt in quantities]
    rows.append([r'\multicolumn{5}{l}{\textit{Test-frame noise-scale diagnostics (pooled entries)}}'])
    for label, rawkey, phasekey in [
        ('Mean early channel power', 'early_mean', 'early_mean'),
        ('Mean difference power', 'raw_mean', 'phase_mean'),
        ('Median difference power', 'raw_median', 'phase_median'),
        ('Relative mean difference power (dB)', 'raw_relative_db', 'phase_relative_db'),
        ('Single magnitude residual: median', 'projection_median', 'projection_median'),
        ('Single magnitude residual: 97.5th percentile', 'projection_q975', 'projection_q975')]:
        rows.append([label, *[f'{r[key]:.3f}' for r in scale for key in (rawkey, phasekey)]])
    table('reviewer_hardware.tex', r'Chronological RENEW calibration: raw complex differences and phase-invariant residuals. Each capture uses 256 calibration frames and rank 251, followed by 1,614 HUB or 1,513 LO test frames. Rates are bit/s/Hz; radii use whitened digital channel units. Percentages describe these recordings.', 'supp:hardware_calibration',
          ['Quantity', 'HUB raw', 'HUB phase', 'LO raw', 'LO phase'], rows,
          r'The phase score uses projection-magnitude differences for $L_P$ and phase-aligned vectors for $L_F,U_F$. The combined interval is $[\max(L_P,L_F),U_F]$; floor percentages are medians of paired $100L_P/R_{\rm later}$ ratios. Difference powers pool frames, users, retained streams and tones; ratios divide their mean by mean early power. Independent unit-variance pilot noise predicts raw mean power two. The single magnitude residual is phase invariant, so its quantiles repeat across raw/phase columns; it pools the 12 scheduled projections per test frame before maximization. Note~6 defines the normalization and its limits. Exhaustive fixed-equal-power early schedules give median ceiling excesses of $3.33\times10^{-5}$ (HUB) and $6.86\times10^{-5}$ (LO) bit/s/Hz, a discrete reference. LO fails nominal 95\% joint coverage under both scores; its rate floors hold through slack.')
    print('Round-two tables and scalar source data generated.')


if __name__ == '__main__':
    build()
