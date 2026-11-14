# Numerical changes and their sources

`Numerical_changes.csv` enumerates every numeric occurrence in changed paragraphs/tables of the editable Article and supplement, compared with commit f7adc44d04b660d07ab3c7faadb4f432e26f5b66. Context is retained to distinguish rates, counts, parameters and equation constants. Rewritten or relocated paragraphs also include their unchanged numbers; the ledger does not classify those as newly measured outcomes. References and cross-reference labels are excluded from token extraction.

All following paths are relative to `code/manuscript/revision/` in GitHub, or `Gate_4/revision/` in the journal software archive. CSV files retain unrounded values; the companion Source Data files map these values to every display.

| Result / displayed values | Numerical source | Calculation / interpretation |
|---|---|---|
| Paired iteration counts 507/0/5/0 and 505/0/4/3; exact P 0.0625/0.125 | round2_data/iteration_paired_tests.csv | round2_summary.py; conditioning on discordant topology pairs |
| Added median times 2.5850/6.7841 and 22.7841/95.4903 ms | round2_data/latency_increments.csv | Differences computed before rounding |
| 38/63 iteration budgets; 38.39/176.35 versus 35.59/164.01 ms; 6,144 new calls | round2_data/time_budget.json, time_budget_pilot.csv, time_control_calls.csv, time_control_blocks.csv, time_control_summary.csv, time_control_paired_tests.csv | round2_compute.py; timing-only pilot then frozen budgets, 512 topologies per size, three repetitions |
| Achieved rates, retention and learned lower-rate increments | reviewer_data/absolute_rates.csv, absolute_rate_summary.csv; round2_data/achieved_rate_comparison.csv | Verified common action path; difference of marginal medians distinguished from paired ratios |
| Analytic slack/loss means, medians and endpoint IQRs | round2_data/decomposition_distribution.csv | round2_summary.py; enclosing continuous references |
| Separate 16-user upper-table split | round2_data/integer_table_reference.csv | Exact integer-table reference, not a physical continuous optimum |
| O1 width sweep: zero changed entries; shortlist counts | round2_data/o1_budget_entries.csv | round2_refinement.py; 64 tiles, fixed action/prices |
| O1 depth medians 1.119582/1.118334/1.117494 and T4 1.113253/1.080005/0.867040 | round2_data/o1_depth.csv, o1_depth_summary.csv | 16/64/256 children for scheduled entries, verified matching witness |
| O1 two-/four-user slack 1.03877/0.90425 and action loss 0.13522/0.15193 | round2_data/o1_small_references.csv | round2_refinement.py and round2_oracle.py; all 128 references resolved, largest four-user width 9.999108e-7 bit/s/Hz |
| Raw and phase-invariant radii, LF, LP, UF, later rates, widths and coverage | round2_data/hardware_comparison_HUB.csv, hardware_comparison_LO.csv, hardware_phase_HUB.csv, hardware_phase_LO.csv | round2_hardware.py, same chronological split/rank; every certificate replayed |
| Phase medians/IQRs, equivalent CFO and noise benchmark | round2_data/hardware_phase_rotations_HUB.csv, hardware_phase_rotations_LO.csv, hardware_phase_HUB.json, hardware_phase_LO.json | Six user-frame diagnostics; frequency conversion is not causal attribution |
| Sionna 2.2.0 / TR 38.901 V19.2.0; dated configuration and pilot lock | protocol_provenance.json; round2_data/reference_verification.json | Frozen generator plus official documentation/publisher records |
| Unchanged primary rates, times, confidence intervals, structural fixtures and geometry in rewritten passages | ../source_data/, reviewer_data/, ../supplementary/data/ and original audit results | Original confirmatory records remain byte-identical; source hashes were rechecked |

No calculation is replaced by an unfilled marker. Persistent DOI registration is the outstanding external action, not a missing numerical result.
