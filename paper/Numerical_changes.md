# Numerical changes and sources

The CSV includes the 19 November pre-submission edition and enumerates numeric occurrences in changed paragraphs and tables compared with round-two commit 376c7ed27de583eb064cdf9cf7c48c0c50da2417. Reworded or relocated paragraphs include retained numbers; they are not all new measurements. Reference keys and cross-reference labels are excluded. No numerical result has been replaced by an unfilled marker.

Paths below are relative to code/manuscript/revision in GitHub, or Gate_4/revision in Supplementary Software 1.

| Added or clarified result | Exact scalar source | Aggregation and check |
|---|---|---|
| HUB raw difference mean/median 18.398139868 / 3.536998356; aligned 12.249401226 / 2.906931151 | round3_data/hardware_scale_HUB.json; hardware_scale_summary.csv | 1,859,328 entries over 1,614 test frames, six users, 64 streams and three tones |
| LO raw difference mean/median 121.622382397 / 18.557571253; aligned 43.954320613 / 8.394412304 | round3_data/hardware_scale_LO.json; hardware_scale_summary.csv | 1,715,742 entries over 1,513 test frames, six users, 63 streams and three tones |
| Mean early powers 1256.871195248 and 1074.460899573; raw/aligned relative powers -18.345168571/-20.111759132 dB and -9.461771095/-13.881890441 dB | Same JSONs; hardware_scale_frames_HUB/LO.csv; hardware_scale_stream_tone_HUB/LO.csv | Ratios of pooled means; frame and stream-by-tone summaries reproduce the means |
| Single-projection median/q97.5: HUB 4.335309914/30.489072302, LO 6.282940600/35.520708093 | Same JSONs; round3_diagnostics.py | Pools 12 magnitude residuals per frame; all reconstructed maxima and input hashes match round2_data/hardware_phase_HUB/LO.csv |
| Tangent binding in all 507,904 O1 pair-tone entries; zero box wins or ties; minimum box/child margins 1.219302/0.228126 nats | round3_data/o1_binding_bounds.csv | Production priced-bound arithmetic and all 16 children, 64 tiles; existing table ticks reproduced exactly |
| Explicit 16/64/256-child O1 baseline and results | round2_data/o1_depth_summary.csv | Existing results only, newly written out in prose |
| Methods summaries moved to Supplementary Note 4 | Existing primary audit tables and simulation summaries | Original learned-versus-baseline intervals, subgradient passes and time retained |

The diagnostic does not identify active-period noise variance or an impairment mechanism. It does not rescale archived hardware rates. All original confirmatory inputs and all 591 first-revision numerical records retain their hashes. DOI registration is deferred until acceptance by author decision.

## Current edition

| Result | Source | Calculation |
|---|---|---|
| At 32 and 64 users, 395/512 and 426/512 zero-price actions meet the rate-gap threshold with a common ceiling. Both counts are 0/512 with the method's own ceiling. | Supplementary Table 6 Source Data, blocks reviewer_absolute_rates and action_common_ceiling_counts | Group the seven endpoints by profile, topology and user count, take their minimum upper endpoint and subtract the original zero-price floor. No runtime threshold is applied. |
| All 2,176 fixed-filter rates lie less than 1.41 × 10⁻¹² bit/s/Hz above their floors | Supplementary Table 8 Source Data, block action_fixed_filter_checks | Exact rational complex inner products, receiver powers and noise terms, followed by directed 75-digit logarithms and conversion to occupied-band units. |
| Two-user continuous roots have maximum width 5.125483 × 10⁻¹⁵ bit/s/Hz | Supplementary Table 8 Source Data, block action_two_user_root_widths | Subtract the binary64 bounds in nats, then convert the width outwards. Subtracting separately displayed rates can change the last few bits. |
| Four-user pricing gap persists on a neighbourhood | Supplementary Note 2 and Figure 2 Source Data, block fig2_channels | Exact four-user enumeration and linear-programming duality. Uniform score perturbations of size η move an S-edge feasible or relaxed optimum by at most Sη. |

The 19 November wording brings the existing four-user result and the unchanged-schedule counts into the abstract. The 24–28% figures are medians of per-frame projected-floor/later-pilot-rate ratios. The joint residual counts are 1,583/1,614 (HUB) and 1,146/1,513 (LO), using the phase-invariant score rows underlying Supplementary Table 13. No simulation result or measurement changed in this revision.
