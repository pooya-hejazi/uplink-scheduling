# Point-by-Point Response to Referees

Bounding the rate loss of individual wireless uplink schedules

Pooya Hejazi and Masoud Sabaei · 14 November 2026

The responses follow the supplied revision requests, using their section and item numbers. New calculations are exploratory extensions of the frozen confirmatory experiment. Locations below are exact line numbers in the delivered standalone UTF-8 LaTeX sources (main.tex and Supplementary_Information.tex), not the PDF margin line numbers. Figure and table numbers refer to the compiled revised documents.

## 1.1. Calibrated RENEW bounds and exhaustive scheduling

**Request.** Calibrate vector and directional errors from the two LTS windows, evaluate held-out floors, and enumerate the 90 labelled equal-power schedules.

**Response.** We retained the original 128-frame preprocessing prefix and used the first 256 eligible post-prefix frames for calibration. Each residual event receives error budget 0.025, giving rank 251. The action map is fixed before examining residuals. HUB: 1,614 test frames; observed projected-floor coverage 100.00%; median projected floor 3.754, upper endpoint 26.831 and interval width 23.075 bit/s/Hz. LO: 1,513 test frames; observed projected-floor coverage 100.00%; median projected floor 1.292, upper endpoint 28.118 and interval width 26.830 bit/s/Hz. Both residual events held jointly on 97.40% of HUB and 70.26% of LO test frames. The LO result does not support nominal 95% joint coverage, despite the conservative floors covering every observed later rate. Every calibrated output passes the separate numerical checker. Figure 6c,d and Supplementary Table 13 give coverage and endpoint summaries. All 90 schedules were evaluated at fixed equal powers on all 1,870 HUB and 1,769 LO early inputs. Figure 6a distinguishes the achieved-action gap from the early ceiling minus this exhaustive reference. The latter is an exact enumeration of a discrete feasible set, with numerical rate evaluation; it is not the continuous-power optimum. The temporal split prevents reuse of calibration residuals, but does not establish exchangeability or latent-payload coverage. The resulting wide intervals are reported as a limitation.

**Location.** Article source, line 225; SI source, line 1080.

## 1.2. Absolute rates and a shared certified ceiling

**Request.** Report L, U and the smallest available certified ceiling per topology for all seven methods at 16, 32 and 64 users.

**Response.** Supplementary Table 6 reports 21 rows, each based on 512 topologies. Figure 5a compares the 32- and 64-user endpoints. Deterministic median lower rates are 15.331 and 15.430 bit/s/Hz, with median paired retention 99.636% and 99.587%. Learned warm start gives 15.336 and 15.431 bit/s/Hz and 99.675% and 99.601% retention. We compute each ratio against its own topology ceiling, not a ratio of marginal medians. Code inspection showed that the archived equal-power-initialized matching control subsequently refines its powers; it is therefore labelled Matching + power refinement, rather than incorrectly described as fixed equal power.

**Location.** Article source, line 63; SI source, line 774.

## 1.3. Bound slack versus action suboptimality

**Request.** Separate U−V and V−L through 16 users using the continuous reference brackets and integer assignment results.

**Response.** Figure 5b and Supplementary Table 8 report enclosing ranges rather than treating a bracketed optimum as a known point. For two users, mean upper slack is 0.23467 and mean action suboptimality is 0.00340 bit/s/Hz. At four, six and eight users, median reference widths are 5.85e−5, 7.34e−5 and 1.50e−4 bit/s/Hz; their maxima are 0.5141, 0.8544 and 0.9291, so tight medians do not characterize every instance. At 16 users, exact assignment optimizes the rounded upper-score table. Combined with feasible schedules, it brackets mean upper slack at 0.01756–0.01874 and mean action suboptimality at 0.01400–0.01517 bit/s/Hz. Equating the integer-table optimum with the continuous physical optimum would be incorrect.

**Location.** Article source, line 71; SI source, line 821.

## 1.4. Additional deterministic iterations

**Request.** Give deterministic search three more price iterations and compare its success, gap and time with learned warm start.

**Response.** We ran three calls per method on all 512 topologies at each size, rotating method order. The ten-iteration 32-user control passed on 507/512 topologies, with median gap 0.05942 bit/s/Hz and time 19.46 ms. The nine-iteration 64-user control passed on 505/512, with gap 0.06612 and time 80.81 ms. In the same rerun, learned warm start passed on 512/512 and 509/512, with gaps 0.05495 and 0.06447 and times 39.66 and 169.51 ms. The baseline reproduced all 1,024 archived deterministic gaps. Figure 4d and Supplementary Table 7 describe this as iteration-matched, exploratory evidence: equal iteration counts do not establish equal wall time or eliminate neural and action-pool costs. The primary confirmatory results remain unchanged.

**Location.** Article source, line 67; SI source, line 805.

## 1.5. O1 refinement-budget sweep

**Request.** Increase the number of refined pair–tone boxes from 32 to 128, 512 and all 7,936 on the 64 O1 tiles.

**Response.** All four budgets were evaluated and each certificate was replayed. The median gap remained 1.1195818 bit/s/Hz and median T4 remained 1.1132530 bit/s/Hz. The sweep preserves the same 16-child partition depth and adds entries in descending parent-score order, retaining the original shortlist. Thus broader fixed-depth refinement did not close the median O1 gap. It does not establish an intrinsic or irreducible physical loss: deeper partitions, alternative prices and stronger bounds were not tested. Supplementary Table 10 reports the full sweep and explicitly separates its exploratory timing from primary deadline results.

**Location.** Article source, line 75; SI source, line 911.

## 2.1. Model scope in the abstract and Results

**Request.** State the paired full-service model early, including receiver and power restrictions.

**Response.** The first abstract sentence and opening Results paragraph now specify two single-antenna users per tone, one tone per pair, bounded powers and separate linear receivers without SIC. Results also state K=2S. The scope is attached to the bound, rather than presented as a universal uplink optimum.

**Location.** Article source, line 15; Article source, line 30.

## 2.2. Abstract

**Request.** Use a flowing abstract of fewer than 150 words, with quantitative scale and an accurate hardware conclusion.

**Response.** The revised abstract contains 139 whitespace-separated words. It reports the two median gaps and decision times and median retention above 99.5%. Its closing sentence describes the optimism of uncalibrated pilot floors and the conservative calibrated floors observed across successive training sequences in the six-user recordings. The conclusion is limited to those observed later-pilot rates.

**Location.** Article source, line 15.

## 2.3. Practical degrees of freedom and latency

**Request.** Explain what is outside the oracle model and how the measured times relate to deployment.

**Response.** Discussion explicitly excludes variable multiplexing orders, multiple tones per user, nonlinear SIC, and queue/fairness weights. The 18–80 ms median times are related to slowly changing or nomadic blocks and upper-layer allocation. Millisecond slot scheduling would require a smaller budget or acceleration, with new end-to-end measurements. Methods clarify that the recorded timer begins after channel cropping and normalization.

**Location.** Article source, line 97; Article source, line 230.

## 2.4. Unpublished companion manuscripts

**Request.** Remove reliance on unpublished manuscripts and make the mathematical presentation self-contained.

**Response.** The Article contains no reference to the two under-review manuscripts. No public preprint citation was invented. Methods and Supplementary Note 2 contain the required continuous-power, vertex-repair and rounding arguments. Established ingredients are distinguished from their present combination. Confidential editorial overlap disclosure is retained separately; it is not part of the reviewer code/data repository.

**Location.** Article source, line 24; SI source, line 55.

## 2.5. Figure 5 and pilot-cost uncertainty

**Request.** Remove the scalar phase-shape experiment and replace it with scheduling validation, keeping the horizon analysis.

**Response.** The standalone phase-shape simulation has been removed from current Article and SI displays and prose. Figure 5a shows absolute rates and ceilings; Figure 5b shows physical optimality brackets. Panels c,d retain the stationary pilot-cost calculation. The comparator is explicitly the zero-price, equal-power-initialized matching action with its feasible power refinement on the same LS estimate. Exact two-sided 95% binomial intervals quantify fractions over the 128 independent simulated topologies in each arm; they are not coverage guarantees for a future temporal sequence.

**Location.** Article source, line 80; SI source, line 952.

## 2.6. Figure 6 and Argos

**Request.** Move Argos panels to the supplement and dedicate Figure 6 to RENEW.

**Response.** Figure 6 now contains early-input certificates and the exhaustive fixed-power reference, the uncalibrated later-pilot shift, chronological test coverage and calibrated endpoint summaries. Its caption distinguishes each denominator and explains that median endpoints are marginal summaries. The Argos first/second-pilot spatial-overlap panels are in Supplementary Figure 8, with recording summaries in Supplementary Table 14. No paired-payload transmission is inferred.

**Location.** Article source, line 327; SI source, line 1232.

## 2.7. Gaussian benchmark arithmetic

**Request.** Show explicitly how radius 0.50 produces interference power 0.25 and a rate-floor reduction of about 0.87.

**Response.** The text now states 0.50 squared equals 0.25 above unit noise. Together with the reduction in desired amplitude, the floor decreases by 0.87 bit/s/Hz at squared nominal amplitude 160. The previous ambiguous comparison with 0.20 has been removed. Figure 3a starts at 11.5 bit/s/Hz, so the 11.974 lower endpoint is visible.

**Location.** Article source, line 53.

## 2.8. Exact confidence limits, nesting and threshold scale

**Request.** Add exact binomial intervals, identify nested user subsets and express absolute thresholds relative to rate.

**Response.** The exact one-sided 97.5% lower limits for 506/512 and 504/512 are 97.47% and 96.94%, reported alongside the prespecified bootstrap limits. The two-sided 95% intervals for 120/128 and 127/128 are 88.06–97.26% and 95.72–99.98%; direct beta-quantile evaluation gives 95.72%, correcting the suggested 95.71%. The 16-, 32- and 64-user sets are nested within the same 512 realizations. Relative to the reported rate scales, 0.15 is about 1%, 0.50 is about 2.6–3.3%, and the hardware threshold 0.10 is about 0.41–0.42%. The requested 1–3.5% range does not apply to the hardware data and was not imposed.

**Location.** Article source, line 61; Article source, line 55; Article source, line 215.

## 2.9. Decoder knowledge and pilot overhead

**Request.** State the effective scalar gain and gross-rate assumptions.

**Response.** Methods define the fixed-filter rate as Gaussian-input mutual information assuming knowledge of the effective scalar complex gain after combining. Gross occupied-band rates exclude pilot overhead except in the explicitly defined stationary net-rate calculation.

**Location.** Article source, line 119.

## 2.10. Computing environment and verification terminology

**Request.** Give full hardware/software details and describe the scope of separate verification.

**Response.** Methods identify the Intel Core i9-10885H at 2.40 GHz, eight physical and sixteen logical cores, 32 GB RAM, Windows 11 build 26200, Python 3.13.5, NumPy 2.3.4, SciPy 1.16.3, Numba 0.62.1, NetworkX 3.4.2, Zig 0.13.0 and LEMON 1.3.1. BLAS and OpenMP are restricted to one thread for verification. The text describes a separate CPU verification implementation on the original workstation, not an outside laboratory. Hardware fetching and new exploratory analyses are separated from original confirmatory timing.

**Location.** Article source, line 232; SI source, line 1337.

## 2.11. The small unused-power charge

**Request.** Explain the approximately 6.88e−7 bit/s/Hz T3 term.

**Response.** The note following Supplementary Table 9 explains the integer grid PT=20 times 2^20 and downward rounding by at most one tick per user. A few unused ticks leave the small deterministic power-price charge when the total budget is active.

**Location.** SI source, line 925.

## 2.12. Consistent terminology and symbols

**Request.** Unify algorithm labels and remove internal workflow terms from scientific prose.

**Response.** The current displays use Deterministic search, Learned warm start, Network only, Subgradient baseline and Zero-price baseline. The added control is called Equal-iteration deterministic because its measured compute time differs. Internal workflow names and code/log filenames have been removed from Article and SI prose. Assigned score, Gaussian amplitude, orthogonal-pair rate, channel set, upper-score table and horizon use distinct symbols A_beta, A_0, c_orth, mathcal H, H and N_blk. Original identifiers remain in software/data for reproducibility.

**Location.** Article source, line 142; Article source, line 221; SI source, line 188.

## 2.13. Contributions and funding

**Request.** Use author initials, record supervision and move funding to Acknowledgements.

**Response.** The updated author statement records the confirmed roles. P.H. conceived the study, formulated the mathematical bounds, developed the scheduling and verification software, analysed simulation and measurement data, and wrote the manuscript. M.S. supervised the research, contributed to problem formulation and analytical design, and reviewed and edited the manuscript. The no-funding statement remains in Acknowledgements.

**Location.** Article source, line 300; Article source, line 298.

## 2.14. Figure and heading polish

**Request.** Keep bold panel letters, move explanations to captions, show the full Gaussian endpoint and shorten the Methods heading.

**Response.** Panel titles have been replaced by bold letters, with channel profiles and user-count mappings in the captions. The lower limit of Figure 3a is 11.5. The Methods heading is now Small-instance continuous and discrete references. Supplementary table alignment and long-table numbering have been checked in the compiled PDF.

**Location.** Article source, line 202; SI source, line 647.

## 3.1. Supplementary order

**Request.** Order supplementary notes, tables and figures by their first Article citation.

**Response.** The seven notes are now prior work, proofs, Gaussian calculation, solver/simulations, propagation/pilot cost, hardware and numerical verification. Sixteen tables and eight figures follow their first-citation order in the Article. All Article references and the numbered Source Data files were updated together.

**Location.** Article source, line 28; SI source, line 33.

## 3.2. Concise literature comparison

**Request.** Replace the long annotated bibliography with a one-page, five-column comparison of ten closest studies and standard references.

**Response.** Supplementary Table 1 compares the model, optimization mechanism, guarantee and relation to this study for ten selected works. It fits on one page. A standard numbered Supplementary References section follows the scientific notes; its 51 entries match the Article bibliography. Sources used only for the removed scalar phase experiment are no longer cited.

**Location.** SI source, line 39; SI source, line 1405.

## 3.3. Table alignment

**Request.** Repair Panel A of the primary table and the four-user counterexample table.

**Response.** The primary results use a seven-column Panel A and a nine-column timing Panel B under one table number, with distinct hyperlink anchors. The four-user table has an explicit column specification matching every row. Both are included in the compiled layout review.

**Location.** SI source, line 647; SI source, line 173.

## 4. Final prose and layout polish

**Request.** Complete the five technical corrections and seven prose edits without changing numerical results.

**Response.** Supplementary Table 16 now reads Distinct decision certificates. The full Learned warm start tick label in Supplementary Figure 4c is right-aligned with a 35-degree rotation, and the signed-score fixture uses 8-point column padding. The contributions paragraph records the newly confirmed analytical-design role, and Code availability identifies the repository and the complete code archive in Supplementary Software 1. The abstract, retained-rate comparison, iteration control, refinement sweep, RENEW results, threshold explanation and Figure 5–6 captions now use direct analytical prose. The rate fractions remain paired by topology, and the timing comparison still matches iteration counts. Broader fixed-depth refinement left the median O1 gap unchanged; deeper partitions are proposed for testing. The RENEW text reports the 70.26% LO joint residual coverage alongside complete observed rate-floor coverage without attributing that difference to an untested drift mechanism. Captions identify deterministic contribution ranges and marginal endpoint medians. All numerical data files are unchanged.

**Location.** Article source, line 15; Article source, line 75; Article source, line 89; Article source, line 242; SI source, line 1391; SI source, line 201; SI source, line 848.
