# Numerical source data for the six article figures

CSV tables retain unrounded values. Rates are bit/s/Hz, normalized by occupied bandwidth; times labelled ms are milliseconds. input_sha256.txt identifies the frozen inputs and new analysis outputs. Source_Data.zip provides one annotated text file per numbered display, including eight supplementary figures and sixteen supplementary tables.

| Figure | Included observations |
|---|---|
| 1 | Four nonnegative contributions for each deterministic topology; panel b uses CDL-A, block 0, 32 users. |
| 2 | Exact four-user pair/tone correlations and price sweep; 512 native 16-user upper-table comparisons. |
| 3 | Gaussian expected endpoints, noisy-channel utility and simulated joint-event coverage. |
| 4 | Original 4,096 method/topology decisions and timing summaries; new iteration-matched three-repeat control, kept separate from primary timings. |
| 5 | Absolute rates for seven methods, physical optimality brackets, and stationary pilot-cost fractions with exact binomial intervals over independent simulated topologies. |
| 6 | Original early/later RENEW summaries and capture denominators; chronological residual calibration, held-out later-pilot rates, and exhaustive enumeration of 90 equal-power schedules per eligible frame. |

The smallest certified ceiling is selected within each topology. Physical reference brackets through eight users and the 16-user upper-table optimum have different scopes. Hardware test frames are temporally dependent: reported coverage is descriptive for the observable second pilot, not a latent channel or payload. Calibration rows have blank test-only fields by design. Restricted raw Rice recordings and reconstructed complex channels are excluded.
