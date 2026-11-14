# Bounding the rate loss of individual wireless uplink schedules

Research code, numerical source data and reproduction materials for the manuscript by **Pooya Hejazi and Masoud Sabaei** (Amirkabir University of Technology).

This repository is private during review. Reviewers need access granted by the repository owner. The paper studies full-service paired uplinks: two single-antenna users per tone, one tone per pair, bounded powers and separate linear receivers without SIC.

## Start here

- `paper/main.pdf`: article; `paper/main.tex`: standalone editable source.
- `supplementary_materials/Supplementary_Information.pdf`: proofs, algorithms and extended results.
- `supplementary_materials/Source_Data.zip`: annotated numerical data for the numbered displays.
- `software/`: directly browsable Python/C++ code, figure CSVs, exact fixtures and verification evidence.
- `supplementary_materials/reproduction/`: complete research-workspace assembler and input manifests.

## Quick reproduction (CPU)

Use Python 3.11 or newer, with assertions enabled (do not use `python -O`). From the repository root:

```sh
python -m venv .venv
# Activate .venv using the command appropriate to your shell.
python -m pip install numpy scipy pandas matplotlib numba networkx
python software/Gate_1/verify_gate1.py
python software/Gate_4/audit/issue.py verify
python software/Gate_4/make_figures.py
python software/Gate_4/supplementary/make_physics_supp.py
```

These commands check exact mathematical fixtures, verify the archived verification evidence, and regenerate the six article figures and propagation/pilot-cost supplementary figures from included scalar data. They do not retrain a network or decode a recording. Plotting rewrites generated figure files, so use a working copy if you want to preserve the supplied hashes.

The recorded CPU verification environment is Windows 11, CPython 3.13.5, NumPy 2.3.4, SciPy 1.16.3, Numba 0.62.1 and NetworkX 3.4.2. Native matching targets 64-bit Windows with Zig 0.13.0 and LEMON 1.3.1. Training uses CUDA-enabled PyTorch; channel generation additionally requires Sionna 2.2.0. See the detailed [reproduction guide](supplementary_materials/reproduction/README.md) before running those stages.

## Full input data

Large immutable inputs are attached to the private [reviewer-materials-2026-11-14 release](../../releases/tag/reviewer-materials-2026-11-14). They contain four frozen experiment packages and `Gate_2_arrays.zip` (4,096 fit teachers and 4,864 additional simulated arrays). They are kept out of ordinary Git history.

With the GitHub CLI authenticated to an account that can access this repository:

```sh
gh release download reviewer-materials-2026-11-14 --repo pooya-hejazi/uplink-scheduling --pattern "Gate_*_Deliverable_Package.zip" --dir supplementary_materials/reproduction/output
gh release download reviewer-materials-2026-11-14 --repo pooya-hejazi/uplink-scheduling --pattern "Gate_2_arrays.zip" --dir .
python -m zipfile -e Gate_2_arrays.zip supplementary_materials/reproduction
python supplementary_materials/reproduction/reproduce.py verify
python supplementary_materials/reproduction/reproduce.py unpack research_workspace
```

You may instead download these same assets through the authenticated release page. Put the four experiment ZIPs in `supplementary_materials/reproduction/output/` and extract `Gate_2_arrays.zip` into `supplementary_materials/reproduction/`. The SHA-256 manifest verifies every complete input before extraction. Allow about 1.5 GB for downloaded inputs and another 2 GB for the materialized research workspace, in addition to download archives.

## Reviewer analyses

Run these from the materialized `research_workspace`, after installing the documented scientific/native environment:

```sh
python Gate_4/revision/reviewer_analysis.py rates
python Gate_4/revision/reviewer_analysis.py decomposition
python Gate_4/revision/reviewer_analysis.py sweep
python Gate_4/revision/reviewer_analysis.py compute
python Gate_4/revision/reviewer_tables.py
```

The scripts write scalar outputs to `Gate_4/revision/reviewer_data/` and preserve the earlier confirmatory experiment. The extra-iteration control matches the number of price iterations; measured wall times are reported separately. Exact assignment of an upper-score table is not an exact continuous-power optimum. Small-instance physical optima are reported as enclosing intervals.

## Rebuild the documents

Install Tectonic and run from the repository root, replacing `PATH_TO_TECTONIC` with its executable:

```sh
python supplementary_materials/tools/build_paper.py --tectonic PATH_TO_TECTONIC
python supplementary_materials/tools/build_supplementary.py --tectonic PATH_TO_TECTONIC
```

Add `--only-cached` only if all required TeX resources are already cached. Builders read the editable sources in `supplementary_materials/reproduction/Gate_4/`. Regenerating full simulation or hardware figures from original records requires the materialized workspace; the shipped CSVs and PDFs can be inspected without that step.

## Measurement data and interpretation

Restricted Rice IQ/HDF5 recordings and reconstructed complex measurement channels are not redistributed. Obtain them under the provider's research-use terms from [Rice RENEW](https://renew.rice.edu/dataset-distributed.html) and [Argos](https://renew.rice.edu/dataset-argos.html). Original ray scenes are available from [DeepMIMO](https://www.deepmimo.net/). Derived scalar summaries, source identifiers and integrity records are included.

`reviewer_hardware.py decode HUB` / `decode LO` re-fetch the specified RENEW windows and keep decoded channels in a separate local `output/reviewer_revision_20261114/private/` directory; `evaluate HUB` / `evaluate LO` produce scalar summaries. Do not redistribute that private directory. Chronological calibration is evaluated against an observable second LTS, not a noiseless payload channel. One recording per clock mode does not establish exchangeability or population coverage. No paired-payload experiment is claimed.

## Attribution

Correspondence: **Masoud Sabaei**, sabaei@aut.ac.ir. Third-party components and their notices are retained in the experiment packages. This review deposit does not add a new license to third-party data or software.
