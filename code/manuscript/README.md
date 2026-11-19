# Bounding the rate loss of individual paired wireless uplink schedules

Pooya Hejazi and Masoud Sabaei • Reviewer analysis and manuscript edition • 19 November 2026

The authors prepared this Article for **Communications Engineering**. Read [the article](main_nature.pdf) with its [Supplementary Information](Supplementary_Information.pdf). The [computational audit](Gate_4_Audit_Certificate.pdf) covers the underlying frozen results. Each distributed clock configuration contributed one Rice recording. The revised Article separately reports the six-user receiver errors against the transmitter files. The recordings contain no CRC log for the proposed two-user schedules.

The system and receiver diagrams in Figs. 1–3 are drawn from the stated model. Supplementary Note 7 reports a direct check of the small-system fixed-filter rates.

## Reproduce the article and illustrations

Edit [main_nature.tex](main_nature.tex) and its local inputs, including [the references](references.tex). From this directory run `tectonic main_nature.tex` and `tectonic Supplementary_Information.tex`, or use the PowerShell wrapper `./build.ps1` for both PDFs and the current single-file editorial source. XeLaTeX users should run each document twice to resolve cross-references. The six required figure PDFs are in `figures/`.

The `revision/refs_*.json` records supply the bibliography and literature comparisons. After changing citations or records, run `python revision/build_references.py`. Then run `python build_submission.py` to regenerate [main_nature_submission.tex](main_nature_submission.tex), the single editable submission source with its bibliography embedded. Compile it beside the same `figures/` directory. This generated editorial alias is refreshed automatically by `build.ps1`, `package.py`, and the portable `tools/build_paper.py` and `tools/refresh_software.py` entry points. The official Springer Nature submission source is `paper_submission/paper/main.tex`, assembled by `tools/build_paper.py`; its default inputs are the included `reproduction/Gate_4` sources, with `--source` available for the canonical editorial directory. The [supplementary source](Supplementary_Information.tex) is a separate document. The [revision response](Revision_plan_and_response.md) records the editorial changes, and the [geometry notes](revision/ray_geometry.md) describe how to reproduce the channel comparisons.

For the six plots, install Python with NumPy, pandas, SciPy and Matplotlib. Run `python make_figures.py` in this directory. It reads only the adjacent source_data folder. `python make_figures.py --collect` rebuilds the figure inputs after checking each original source against its released SHA-256 manifest; this alternative requires the Gate_1, Gate_2 and Gate_3 source directories as siblings. The source_data/input_sha256.txt lists those immutable input fingerprints. The static figures are standard numerical plots, not generated images. PDFs embed fonts; SVGs retain editable text.

## Reproduce the independent audit

The full handoff includes the four original sealed releases under **output/** with a SHA-256 list and the independent code and detailed results under **Gate_4/audit/**. The auditor reads the original ZIPs; do not silently substitute a merged working copy. Start with audit/README.md for commands, environment, compiler provenance, diagnostic negative controls and optional hardware inputs. The releases contain historical notes and absolute machine paths from the original campaigns. The fresh audit, figure reconstruction and article build are separate entry points. Computational independence in this edition means a separate execution role with no training role on the same workstation, not a human auditor or an outside laboratory.

For original research code and complete numerical evidence, use the four payload releases in order (1, 2, 2B, 3); extract them into an empty directory if running the original software rather than audit/prepare.py. Later packages intentionally add to earlier code directories. The final study contains frozen proposer weights; rerunning inference during the CPU certificate audit is neither required nor allowed. The original generators and optimizers can recreate fit, validation and calibration data. Supplementary fit inputs, where present in the full handoff, are archived separately from the original ZIPs and do not change their fingerprints. Do not treat older gate reports or pilot criteria as final confirmatory results.

## Obtain the measurement sources

Rice RENEW: register under the [distributed collection terms](https://renew-wireless.org/dataset-distributed.html); the citable record is [Zafari (2024), IEEE DataPort](https://doi.org/10.21227/74ez-b275). Use the individual capture IDs, sizes, hashes, signed data tones and row-level identifiers documented in Gate_2/RICE_RESULTS.md and Gate_2/results/rice_inventory_verified.csv. The full-chain result uses one acquisition per mode; a second chain, duplicate catalogue paths and adjacent frames are not independent captures. The release includes derived decision and reference statistics; it excludes raw IQ and reconstructed channels.

Rice Argos: register through the [Argos channel survey](https://renew-wireless.org/dataset-argos.html). The three ArgosCSI-8x6 recordings, selected frame and byte ranges, RF eligibility rules, acquisition identifiers and derived pair/frame statistics are documented in Gate_3/ARGOS_PROTOCOL.md, Gate_3/ARGOS.md and Gate_3/results/argos. The [Shepard et al. source paper](https://doi.org/10.1109/ACSSC.2016.7869082) and [RENEW platform paper](https://doi.org/10.1109/ACSSC.2018.8645391) are credited in the manuscript. Original data remain subject to their source terms.

DeepMIMO: obtain the legacy O1_60 and asu_campus1 scenario files from the [DeepMIMO database](https://www.deepmimo.net/) using its v3 conventions. Gate_3/ray_manifest.csv, scene-specific tile files and the archived code give base station, physical carrier, coordinate guard, exact users and source hashes. Native single-site CDL and four-site UMa channels use the 3GPP 38.901 v19.2 simulator and seed manifests described in Methods.

## Interpret the evidence

The independent computational replay covers the integers, numerical endpoints and released decisions. The simulation results quantify the rate interval under the stated receiver and power model. At 64 users the learned initialization rescued five of eight remaining failures. The paired bootstrap interval excludes zero, while the exact two-sided test on five discordances gives 0.0625. The coverage tests and Rice replay use separate observational units and support separate conclusions about uncertainty and recorded inputs.

Masoud Sabaei is the corresponding author (sabaei@aut.ac.ir). The supplied editorial archive provides the article, Supplementary Information and figure data. The full reproducibility archive also supplies the software, simulated inputs and numerical outputs. The original Rice observations follow the access routes above.


## November 14 reviewer extension

The current supplement contains sixteen numbered tables, including absolute rates, physical optimality brackets, the additional-iteration control, O1 refinement sensitivity and chronological RENEW calibration. The 51 references are shared with the Article. The standalone scalar phase-shape experiment has been removed from current displays.

The scripts revision/reviewer_analysis.py and revision/reviewer_hardware.py generate scalar outputs in revision/reviewer_data. revision/reviewer_tables.py regenerates their supplementary tables. The full reproduction README explains the native/CUDA dependencies, completed-output resume behaviour and provider-controlled input paths. The formal point-by-point response is delivered beside the official-class paper in paper_submission/paper, or paper/ in the repository.

## Second-round revision

The second revision adds exact paired learning tests, a median-time-budget deterministic control, phase-invariant recorded-pilot calibration, endpoint quartiles for physical optimality brackets, O1 depth tests and resolved small O1 continuous references. Scripts and scalar results are in revision/round2_*.py and revision/round2_data. Original confirmatory records and first-revision numerical files are unchanged.

The learning controls do not establish a benefit at P < 0.05. O1 small references show mostly ceiling slack with nonzero action loss; they do not resolve the 32-user optimum. Phase-invariant floors improve but LO residual coverage remains below nominal. Neither the chronological replay nor its phase diagnostic identifies a causal oscillator mechanism or a payload-throughput guarantee.

The formal response quotes all 19 second-round points, uses printed PDF margin-line numbers and accompanies two marked-change PDFs. Numerical_changes.csv and Numerical_changes.md identify reported numbers and numerical sources. At the authors’ request, the DOI deposit remains private and registration is deferred until acceptance. Confidential editorial documents are excluded from GitHub; no journal submission or reviewer invitation has been sent.

The public GitHub repository uses one code/ execution directory and names Pooya Hejazi as its author and maintainer. Masoud Sabaei remains the Article's corresponding author. Authorship roles and the named AI-assistance disclosure reflect the authors' confirmations. Funding is declared in Acknowledgements.
