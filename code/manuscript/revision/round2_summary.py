"""Second-round summaries from frozen scalar results; no solver or timing rerun."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
PRIOR = HERE / 'reviewer_data'
OUT = HERE / 'round2_data'
OUT.mkdir(exist_ok=True)


def paired(frame, control, treatment, cohort):
    rows = []
    for k, group in frame.groupby('k'):
        wide = group.pivot(index=['family', 'block'], columns='method', values='ok')
        a, b = wide[control].astype(bool), wide[treatment].astype(bool)
        both = int((a & b).sum())
        only_control, only_treatment = int((a & ~b).sum()), int((~a & b).sum())
        discordant = only_control + only_treatment
        rows.append(dict(cohort=cohort, k=int(k), control=control, treatment=treatment,
                         n=len(wide), both_pass=both, control_only=only_control,
                         treatment_only=only_treatment, neither=int((~a & ~b).sum()),
                         exact_two_sided_p=binomtest(only_control, discordant, .5).pvalue if discordant else 1.))
    return pd.DataFrame(rows)


def build():
    blocks = pd.read_csv(PRIOR / 'compute_blocks.csv')
    tests = paired(blocks, 'extra', 'hybrid', 'first reviewer rerun')
    tests.to_csv(OUT / 'iteration_paired_tests.csv', index=False)
    summary = pd.read_csv(PRIOR / 'compute_summary.csv').set_index(['k', 'method'])
    times = []
    for k in (32, 64):
        base = summary.loc[k, 'det'].median_ms
        for method in ('extra', 'hybrid'):
            value = summary.loc[k, method].median_ms
            times.append(dict(k=k, method=method, baseline_ms=base, median_ms=value,
                              difference_of_medians_ms=value-base))
    pd.DataFrame(times).to_csv(OUT / 'latency_increments.csv', index=False)

    rates = pd.read_csv(PRIOR / 'absolute_rates.csv')
    records = []
    for k, group in rates.groupby('k'):
        wide = group.pivot(index=['family', 'block'], columns='method', values='L')
        shared = max(float(abs(wide.cold-wide.equal_match).max()), float(abs(wide.cold-wide.legacy).max()))
        assert shared < 1e-10, (k, shared)
        med = group.groupby('method')[['L', 'U', 'retention_pct']].median()
        gaps = group.assign(G=group.U-group.L).groupby('method').G.median()
        for method in ('cold', 'equal_match', 'legacy', 'sequential', 'det', 'hybrid'):
            records.append(dict(k=k, method=method, n=len(wide), median_L=med.loc[method, 'L'],
                                median_U=med.loc[method, 'U'], median_G=gaps[method],
                                median_retention_pct=med.loc[method, 'retention_pct'],
                                difference_from_cold_median_L=med.loc[method, 'L']-med.loc['cold', 'L'],
                                difference_from_cold_pct=100*(med.loc[method, 'L']/med.loc['cold', 'L']-1),
                                difference_from_det_median_L=med.loc[method, 'L']-med.loc['det', 'L'],
                                median_paired_L_gain_vs_det=float((wide[method]-wide.det).median()),
                                maximum_shared_lower_difference=shared))
    pd.DataFrame(records).to_csv(OUT / 'achieved_rate_comparison.csv', index=False)

    data = pd.read_csv(PRIOR / 'gap_decomposition.csv')
    rows = []
    for k, group in data.groupby('k'):
        family = 'Analytic' if k < 16 else 'Native 3GPP'
        kind = 'Exact polynomial-root enclosure' if k == 2 else '192-split continuous box reference' if k < 16 else 'Physical bracket using integer upper-table DP'
        for statistic, reduce in [('mean', np.mean), ('q25', lambda a: np.quantile(a, .25)),
                                  ('median', np.median), ('q75', lambda a: np.quantile(a, .75))]:
            values = {key: float(reduce(group[key])) for key in ['slack_lo', 'slack_hi', 'suboptimality_lo', 'suboptimality_hi', 'reference_width']}
            values.update(mean_gap=float((group.U-group.L).mean()), maximum_reference_width=float(group.reference_width.max()))
            rows.append(dict(k=k, family=family, reference=kind, n=len(group), statistic=statistic, **values))
    pd.DataFrame(rows).to_csv(OUT / 'decomposition_distribution.csv', index=False)
    # The table optimum is an upper reference, so these are not a physical loss decomposition.
    table = data.query('k == 16').copy()
    table['integer_table_reference'] = table.U-table.exact_table_relaxation_loss
    assert np.allclose(table.integer_table_reference, table.V_hi, atol=1e-12)
    table['slack_above_table_reference'] = table.exact_table_relaxation_loss
    table['shortfall_below_table_reference'] = table.integer_table_reference-table.L
    assert np.allclose(table.slack_above_table_reference+table.shortfall_below_table_reference, table.U-table.L, atol=1e-12)
    table.to_csv(OUT / 'integer_table_reference.csv', index=False)
    print(tests.to_string(index=False), flush=True)
    print(pd.DataFrame(times).to_string(index=False), flush=True)


if __name__ == '__main__':
    build()
