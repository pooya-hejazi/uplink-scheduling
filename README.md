# Bounding the rate loss of individual wireless uplink schedules

Research code and data for the manuscript by **Pooya Hejazi and Masoud Sabaei**, Amirkabir University of Technology. The repository remains **private during review**.

**Repository contact: [Pooya Hejazi](https://github.com/pooya-hejazi).** Questions about this code and reproduction package should be directed to Pooya Hejazi. Scientific authorship and correspondence are recorded in the Article.

## Contents

| Directory | Contents |
|---|---|
| `paper/` | Article PDF, editable LaTeX, six figures and point-by-point response |
| `supplementary_materials/` | Scientific supplement, eight supplementary figures and annotated Source Data |
| `code/` | All executable research and document code; **start with `run.py`** |
| `data/` | Input archive names, sizes and SHA-256 digests |

Within `code`, source modules are grouped by purpose: `mathematics`, `channel_models`, `schedulers`, `experiments`, `manuscript` and `document_tools`. All commands below run from **the same `code` directory**. You do not need to change between module directories.

## Quick reproduction

The CPU environment was tested with CPython 3.13.5 on Windows 11. Keep assertions enabled; do not run Python with `-O`.

```sh
cd code
python -m venv .venv
# Activate .venv using the command appropriate to your shell.
python -m pip install -r requirements.txt
python run.py verify-math
python run.py verify-records
python run.py figures
```

These commands check exact mathematical fixtures and archived verification evidence, then regenerate the six Article figures from the supplied scalar tables. Figure outputs are in `code/manuscript/figures/` and `results/figures/`. No GPU or source recordings are needed for these commands. Plotting rewrites generated figures; use a working copy to preserve the supplied file hashes.

## Full experiment inputs

Download the five ZIP assets from the private [reviewer reproduction release](https://github.com/pooya-hejazi/uplink-scheduling/releases/tag/reviewer-materials-2026-11-14) into `data/inputs/`. They contain mathematical reference records, channel experiments, scheduler experiments, validation experiments and 8,960 simulated arrays. Restricted measurement recordings are excluded.

With GitHub CLI authenticated to an account that can access this repository, run from `code`:

```sh
gh release download reviewer-materials-2026-11-14 --repo pooya-hejazi/uplink-scheduling --pattern "*.zip" --dir ../data/inputs
python run.py verify-inputs
python run.py prepare
```

The same files can be downloaded through the authenticated release page. `data/inputs.json` and `data/INPUT_SHA256SUMS` identify their exact bytes. Preparation verifies the hashes, safely extracts the inputs and creates an ignored local execution workspace. Original identifiers inside immutable inputs are retained so historical verification evidence remains valid; they do not define this repository's directory structure. Allow about 4 GB for downloaded archives and the extracted workspace.

## Reproduce the reviewer analyses

After preparing the inputs, run from `code`:

```sh
python run.py reviewer-rates
python run.py reviewer-decomposition
python run.py reviewer-refinement
python run.py reviewer-compute
python run.py supplementary-figures
```

Scalar analysis outputs are copied to `results/`; supplementary plots are copied to `results/supplementary_figures/`. The first refinement and compute calls perform fresh calculations. Interrupted runs resume per-topology checkpoints in the ignored execution workspace. Existing completed checkpoints are reused on subsequent calls; to measure fresh timings again, move `.work` to a backup location and run `prepare` again.

The compute comparison uses the frozen CUDA/PyTorch proposal worker. Set `GATE_GPU_PY` to that environment's Python executable before running it. Native matching uses 64-bit Windows, Zig 0.13.0 and LEMON 1.3.1. Training and channel generation additionally require CUDA-enabled PyTorch and Sionna 2.2.0. The supplied input records include checkpoints and environment information.

The new control matches the **number of price iterations**, not measured wall time. The exact optimum of an upper-score table is not the continuous-power optimum. Small-instance physical references are reported as enclosing brackets, including their wide tails.

## Rebuild the documents

Install Tectonic, then run from `code`:

```sh
python run.py build-paper --tectonic PATH_TO_TECTONIC
python run.py build-supplement --tectonic PATH_TO_TECTONIC
```

Add `--only-cached` for an offline build after the required TeX resources have been cached. The builders read `code/manuscript/` and update `paper/` and `supplementary_materials/`. The scientific supplement has seven notes, sixteen tables, eight figures and the same 51 references as the Article. The response gives exact line locations in the delivered standalone LaTeX sources.

## Hardware replay

Obtain original recordings under the provider's terms from [Rice RENEW](https://renew.rice.edu/dataset-distributed.html) and [Argos](https://renew.rice.edu/dataset-argos.html). Original ray scenes are supplied by [DeepMIMO](https://www.deepmimo.net/). Capture identifiers, decoding conventions and scalar summaries are included.

```sh
python run.py hardware-decode --mode HUB
python run.py hardware-evaluate --mode HUB
python run.py hardware-decode --mode LO
python run.py hardware-evaluate --mode LO
```

The RENEW decoder checks HTTPS byte ranges, ETags and early-input hashes. Reconstructed channels remain in the ignored local execution workspace; only scalar results are copied to `results`. If an institutional TLS proxy is used, configure `REQUESTS_CA_BUNDLE` with its trusted CA bundle. TLS verification remains enabled.

The first 256 eligible post-prefix frames calibrate the residual radii; the remaining 1,614 HUB and 1,513 LO frames test the frozen rule. Coverage concerns the **observable second LTS**, not a noiseless payload channel. One temporally dependent recording per clock mode does not establish exchangeability or population coverage. No paired-payload experiment is claimed.

## Other research stages

`python run.py --help` lists every entry point. The following commands also run from `code`: `build-native`, `verify-scheduler`, `generate-training`, `train`, `confirmatory-test` and `summarize`. These stages write to the local execution workspace and may require the full native/GPU environment. Re-training and rerunning the original confirmatory campaign are separate from reproducing the supplied reviewer results.

## Integrity and attribution

`REPOSITORY_SHA256SUMS` covers the supplied repository files. `code/SOURCE_MAP.csv` maps the descriptive source layout to archived identifiers and original hashes. Third-party notices are retained. This review deposit does not grant a new license to third-party software or data.
