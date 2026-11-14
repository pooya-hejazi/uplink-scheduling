# Response to the third-round referee report

**Bounding the rate loss of individual paired wireless uplink schedules**

This revision addresses the supplied third-round report and is prepared for Nature Computational Science. The main body contains 3,487 words, the Abstract 133 and Online Methods 4,767 by a conservative whitespace count including TeX notation. Original confirmatory records remain unchanged; the new diagnostics are exploratory. DOI registration remains deferred until acceptance at the authors' request.

Locations below use the printed Article PDF margin ruler, not LaTeX source lines. Supplementary locations refer to its printed page numbers.

## T1

> The hardware residual is still about 25 times the thermal-noise benchmark after phase is removed (the one substantive point)
>
> My round-two suggestion that phase rotation explains the large radii was only partly right, and the authors' own numbers show it. On HUB the median phase rotation is just 0.042 rad, and removing phase lowers the projected radius only from 87.4 to 59.5 (LO: 165.3 to 70.3). The thermal benchmark is 2.45. So a magnitude residual of 24–29 noise standard deviations between two pilots 16 µs apart remains unexplained.
>
> This matters beyond the calibration section, because every hardware rate in the paper is expressed in "whitened" units that depend on the noise variance estimated from the noise slot. If that variance is too small by a large factor, the early rates of about 24 bit/s/Hz, the G ≤ 0.10 pass fractions and the floor percentages are all on the wrong scale.
>
> One inexpensive check settles it. Report, for each capture, the mean of |h⁽¹⁾ − h⁽⁰⁾|² per retained stream and tone in whitened units over the test frames (thermal noise alone predicts 2), together with its ratio to the mean |h⁽⁰⁾|². Then:
> - if the per-entry difference is near 2, the noise scale is right and the large block maxima come from the tail or from the filters; say so;
> - if it is far above 2, the residual is an error that scales with the signal (or the noise slot underestimates pilot-period noise). Say which, state that hardware rates in whitened units are then upper-scale figures, and add one sentence to the limitations.
>
> No new experiment is needed; the stored channel pairs suffice.

**Response.** We computed all diagnostics directly from the stored whitened pairs on the original held-out test frames, without changing calibration, filters, actions or input arrays. Equal-weight entry pooling includes 1,859,328 complex entries on HUB and 1,715,742 on LO. The pooled raw difference-power mean and median are 18.398139868 and 3.536998356 on HUB, and 121.622382397 and 18.557571253 on LO. After optimal per-user, per-tone vector phase alignment, the means and medians are 12.249401226 and 2.906931151 on HUB, and 43.954320613 and 8.394412304 on LO. Mean early channel powers are 1256.871195248 and 1074.460899573. Raw and aligned ratios of pooled mean difference power to pooled mean early power are -18.345168571 and -20.111759132 dB on HUB, and -9.461771095 and -13.881890441 dB on LO.

The single-projection magnitude residual, before frame maximization, has median 4.335309914 and 97.5th percentile 30.489072302 on HUB (19,368 terms), and 6.282940600 and 35.520708093 on LO (18,156 terms). These are 12 scheduled desired/interfering projection terms per test frame, not a second distribution of block maxima. Every reconstructed maximum agrees with the archived phase-invariant score, and every early/later input digest agrees with the original replay. Source Data include pooled, frame and retained-stream-by-tone scalar summaries; raw complex channels remain excluded.

The raw mean powers exceed the independent unit-variance pilot-noise prediction of two; phase alignment does not reduce them to that scale. Modest relative errors on large quiet-slot-normalized channel powers can therefore coexist with large absolute residuals. The pairs do not identify whether the excess comes from signal-dependent distortion, synchronization/window leakage, correlated errors or underestimation of pilot-period noise. We state that hardware rates depend on the frozen quiet-slot noise metric. If it understates active-period noise and distortion, rates are optimistic and gaps, pass fractions and floor ratios require recalculation. We do not call all rates unconditional upper bounds: these data do not estimate the active-period variance or establish a correction factor. The limitation is stated in Results, Discussion and Supplementary Note 6.

**Locations.** Article pp. 7–8, lines 321–327; Article pp. 8, lines 355–357; Supplementary Table 13 and Note 6, pp. 25–26.

## T2

> Abstract and Results prose
>
> - The abstract no longer says what "paired" restricts. Add a half clause: two single-antenna users per tone, linear receivers, no successive cancellation. The round-one concern about scope was closed by that sentence and it should not disappear again.
> - The abstract's second sentence stacks five technical terms ("integer-verified odd-set matching dual", "decision-projected split-conformal calibration"). Nature Communications abstracts must be readable by non-specialists; simplify.
> - "No significant benefit" is accurate, but with only four or five discordant topologies the test could hardly reach 0.05. "Was not established" is the more careful wording, and the Discussion already uses it.
> - Results now compress pairs of values with slashes ("0.0549/0.0645 bit/s/Hz", "32/64-user", "HUB/LO", "1.080005/0.867040"). Write these out ("… and …, respectively"). In the O1 sentence, three partition depths are followed by two values; make clear that 16 children is the baseline.

**Response.** The 133-word Abstract explicitly defines two single-antenna users per tone, separate linear filters and no successive interference cancellation. It uses power-interval bounds, a checkable matching certificate and calibration along deployed filters, and says that learned proposals “did not establish a benefit over” the compute-matched controls. Its numerical claims are retained. Slash-compressed counts, paired values and labels in Results and Discussion are written out, including the Fig. 4d iteration budgets. The O1 paragraph now explicitly gives the 16-child baseline (median T4 1.113253 and G 1.119582), the 64-child results (1.080005 and 1.118334) and the 256-child results (0.867040 and 1.117494 bit/s/Hz). The main body remains 3,487 words under the author's selected Nature Computational Science limit of 3,500, rather than the longer limit assumed in the supplied revision prompt.

**Locations.** Article pp. 1, lines 021–033; Article pp. 6, lines 256–265; Supplementary Table 10, p. 19.

## T3

> Data, code and protocol
>
> - Code is still cited only by a GitHub URL. Deposit the release and the Source Data in a DOI-issuing archive and cite the DOIs. The journal will require this before acceptance.
> - The protocol manifest is "timestamped 13 November" with no year, one day before the previous revision. Give the year, and say explicitly that it records the exploratory revision controls; the original thresholds are described, correctly, as "fixed before evaluating the held-out test cohort, rather than externally registered".

**Response.** The full date, 13 November 2026, is given with the recorded source freeze and pilot-lock times. The accompanying provenance inventory records existing pre-test files, not an external preregistration. The original thresholds were fixed before held-out evaluation; the iteration-matched, time-budget, depth-sweep and phase-invariant controls are explicitly exploratory revision analyses. The new noise-scale check is likewise exploratory.

The complete Source Data and custom software accompany the Article as Source Data and Supplementary Software 1, with the private GitHub repository named in both availability statements. At the authors' explicit direction, DOI registration is deferred until acceptance. The complete offline archival package and metadata are prepared privately; no DOI is fabricated, no public archival record has been created and no unfilled DOI marker appears in the manuscript. This requested external deposit remains deferred, rather than represented as completed.

**Locations.** Article pp. 18, lines 814–826; Article pp. 19–20, lines 857–882; Supplementary Software 1; private offline archival-deposit status.

## T4

> Editorial
>
> - Supply a point-by-point response letter with PDF line numbers and a marked-changes PDF. I had neither this round.
> - If the matching certificate is also the subject of another manuscript under review, that manuscript should be made available to the referees through the editor. I cannot tell from these files whether this has been done.

**Response.** This response quotes the complete T1–T5 sections verbatim and supplies locations from the printed Article PDF margin ruler. Both marked-change PDFs compare with the preceding round-two submission at commit 376c7ed27de583eb064cdf9cf7c48c0c50da2417; the exact baseline sources and their hashes accompany them.

The confidential editorial_only submission folder contains Related_manuscript_equal_power.pdf and Related_manuscript_phase_error.pdf, together with the equal-power supplement and an editorial note explaining the relation to the present Article. They are prepared for the editor to forward to referees. No journal submission has been made from this workspace, so we do not assert that the editor or referees have already received them. They are excluded from GitHub and are not cited or discussed in the main Article.

**Locations.** Article/SI marked PDFs and confidential editorial_only folder.

## T5

> Small items
>
> 1. Check that "Sionna 2.2.0 with spec_version='19.2'" is the exact release and option used; I could not verify it.
> 2. Methods now runs to about 6,700 words. Consider moving the solver constants and the RENEW decoding details to the Supplementary Information, where they are already repeated.
> 3. The compiled layout of Supplementary Tables 3, 7, 9 and 13 should be checked by eye; I could only read the text layer.
> 4. Supplementary Table 10 note: "the child mixed signal/interference bounds remain above the parent tangent/box bound" — add one sentence saying this means the tangent bound, not the box bound, is the binding one on these channels.

**Response.** 1. The archived native generator explicitly sets spec_version='19.2' for both CDL and UMa. Its documented environment specifies Sionna 2.2.0, consistent with the official v2.2.0 release and versioned API. The retained generation log records successful channel-generation counts but has no package-version banner, so it is not independent runtime attestation of that patch version. We retain the documented release and explicit generator option and supply this distinction in the verification record.

2. We removed the three duplicated tail subsections from Online Methods. Methods now contains 4,767 whitespace-delimited words, conservatively counting TeX notation and headings. Numerical constants and decoding details needed for reproduction remain in Methods and Supplementary Notes 4–7. The original learned-versus-baseline bootstrap intervals and subgradient summary from the deleted tail were retained in Supplementary Note 4.

3. We inspected the compiled tables. Table 3 now uses Method, K, Profile consistently in both panels, repeated headers and the table generator. Tables 7, 8, 9, 10 and 13 were checked visually for alignment and legibility. Table 13 includes the new diagnostics with explicit pooling and units.

4. We did not infer the active bound from unchanged ticks alone. Reusing the production enclosure arithmetic, we compared both parent candidates and the maximum of all 16 child bounds for all 7,936 pair-tone entries on each of 64 O1 tiles. The tangent was strictly smaller than the box in all 507,904 entries, with no ties; every child maximum exceeded the tangent. The smallest box-minus-tangent and child-minus-tangent margins were 1.219302 and 0.228126 aggregate nats. Table 10 now states that the tangent remains binding throughout the four width budgets. No original result was changed.

We also replaced model codenames in the assistance disclosure with OpenAI ChatGPT, Google Gemini and Anthropic Claude. The statement describes assistance and author responsibility without adding an unconfirmed claim that all outputs have already undergone human author verification.

**Locations.** Article pp. 15, lines 675–677; Article pp. 13, lines 553–592; Article pp. 19, lines 852–856; Supplementary Table 3, pp. 11–12; Table 7, p. 16; Table 8, p. 17; Table 9, p. 18; Table 10, p. 19; Table 13, p. 25.

## Additional verification (report Part C)

All nine listed 2026 journal references were checked against publisher-deposited DOI records; reference 28 was checked against the official ETSI report. Titles, volumes, pages/article numbers and years agree. The machine-readable records from 14 November 2026 accompany this response. The noise-scale diagnostic in T1 does not identify a causal mechanism.

| Article reference | DOI or primary source |

|---|---|

| 20 | https://doi.org/10.23919/jcn.2025.000085 |

| 21 | https://doi.org/10.1038/s41598-026-38685-3 |

| 22 | https://doi.org/10.1038/s41467-026-73725-6 |

| 23 | https://doi.org/10.1038/s41467-026-76069-3 |

| 41 | https://doi.org/10.23919/jcn.2025.000112 |

| 44 | https://doi.org/10.1038/s41467-026-71793-2 |

| 45 | https://doi.org/10.1038/s41467-026-69493-y |

| 49 | https://doi.org/10.1038/s41467-026-76739-2 |

| 50 | https://doi.org/10.1038/s41467-026-74485-z |

| 28 | [ETSI TR 138 901 V19.2.0, February 2026](https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/19.02.00_60/tr_138901v190200p.pdf) |
