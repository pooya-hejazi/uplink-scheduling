# Bounding the rate loss of individual paired wireless uplink schedules

**[Pooya Hejazi](https://github.com/pooya-hejazi) is the repository author and maintainer.** Please direct questions about the code, datasets and reproduction to him.

The Article by **Pooya Hejazi and Masoud Sabaei** is prepared for *Communications Engineering*. Masoud Sabaei is the corresponding author. This repository contains the research code, measurements derived from the recordings, and the figures and tables used in the Article. [Article PDF](paper/main.pdf) · [Supplementary Information](supplementary_materials/Supplementary_Information.pdf) · [Source Data](data/Source_Data.zip)

## Contents

| Directory | Contents |
|---|---|
| `code/` | All executable research/document code; one entry point, `run.py` |
| `paper/` | Current Article, source, six figures and numerical-change ledger. The earlier response and marked documents are retained as historical material. |
| `supplementary_materials/` | Scientific supplement, its source, eight supplementary figures and the earlier marked version |
| `data/` | Annotated [Source Data](data/Source_Data.zip), input archive names, sizes and SHA-256 digests |

Source modules under `code/` are grouped as `mathematics`, `channel_models`, `schedulers`, `experiments`, `manuscript` and `document_tools`. **Run every command below from the same `code` directory.** Original identifiers within immutable inputs preserve their provenance; they are not repository folders.

The journal upload packages contain the compiled manuscript and its LaTeX sources, and the single Supplementary Information PDF. [Paper ZIP](submission/paper.zip) · [Supplementary materials ZIP](submission/supplementary_materials.zip)

## Quick reproduction from included data

The numerical CPU environment uses CPython 3.13.5 on Windows 11. Keep assertions enabled; do not use Python `-O`.

```sh
cd code
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -r requirements.txt
python run.py verify-math
python run.py verify-records
python run.py round2-summary
python run.py figures
```

These commands verify exact mathematical fixtures and archived audit records, recalculate scalar summaries/tables and regenerate all six main figures. No GPU or source recordings are needed. Figure outputs are in `code/manuscript/figures/` and `results/figures/`. Generated-file bytes may differ across plotting/TeX versions; numerical CSVs and hashes identify the supplied edition. Use a working copy when regenerating files covered by the manifest.

The Article contains six figures. The supplement contains seven notes, sixteen numbered tables, eight figures and 51 references. Table 13a reports paired-pilot results. Table 13b reports hard decisions on the recorded six-user data. The numerical-change ledger identifies the source of each new measurement. [Ledger](paper/Numerical_changes.md)

## Complete experiment inputs

Download the five ZIP assets from the public [reproduction-input release](https://github.com/pooya-hejazi/uplink-scheduling/releases/tag/reviewer-materials-2026-11-14) into `data/inputs/`. The release is pinned to the original inputs; its tag is not moved when the manuscript changes. The assets contain mathematical records, channel/scheduler/validation experiments and 8,960 simulated arrays. Restricted radio recordings and reconstructed measurement channels are excluded.

With the GitHub CLI, from `code`:

```sh
gh release download reviewer-materials-2026-11-14 --repo pooya-hejazi/uplink-scheduling --pattern "*.zip" --dir ../data/inputs
python run.py verify-inputs
python run.py prepare
```

The release page also provides direct browser downloads. Preparation verifies SHA-256 hashes and safely extracts an ignored `.work/` execution workspace. Allow about 4 GB for inputs and extraction. **After updating this repository, move an existing `.work/` to a backup location before preparing the new edition**, so old code overlays are not reused. Moving the workspace also gives a clean rerun; completed per-block checkpoints otherwise resume an interrupted calculation.

## Recompute the reviewer analyses

The three revision rounds have separate numerical records. These commands operate on the prepared local workspace:

```sh
python run.py reviewer-rates
python run.py reviewer-decomposition
python run.py reviewer-refinement
python run.py reviewer-compute
python run.py round2-check
python run.py round2-time-pilot
python run.py round2-time-control
python run.py round2-refinement
python run.py round2-small-reference
python run.py round3-bounds
python run.py verify-action-rates
python run.py seven-method-cost
python run.py supplementary-figures
```

The timing pilot selects deterministic budgets for the current workstation; omitting it retains the reported 38/63 iteration budgets. Fresh timing campaigns can have different absolute latencies. The control matches median elapsed time approximately, not a hard per-topology deadline shared by both methods. Both comparisons use the same 512 topologies per size, three repeats and rotating method order. The original paired tests are P = 0.0625 and 0.125 against both deterministic controls and do not establish a learning advantage at 0.05.

The O1 reference command enumerates every labelled schedule at two/four users with a 32,768-split cap and reports enclosing physical-optimum intervals. All 128 supplied small O1 references resolved to 1e-6 bit/s/Hz; the four-user maximum width is 9.999108e-7. A fresh run can take several hours. The separate analytic four-to-eight-user references retain unresolved tails. The exact 16-user integer-table optimum is not the physical continuous optimum.

Scalar rerun outputs go to `results/`, second-round outputs to `results/round2/` and third-round diagnostics to `results/round3/`. Supplementary plots go to `results/supplementary_figures/`. Reruns do not replace the published source CSVs automatically. `round2-summary` regenerates the published tables from the included scalar results.

The compute controls use the frozen CUDA/PyTorch proposer. Set `GATE_GPU_PY` to that environment's Python executable. Native matching targets 64-bit Windows, Zig 0.13.0 and LEMON 1.3.1. Channel generation uses Sionna 2.2.0 with explicit `spec_version='19.2'`; training needs CUDA-enabled PyTorch. The input archives preserve checkpoints and environment records. No training is required for the scalar reconstruction or certificate replay.

## Rebuild the documents

Install Tectonic; use Perl and latexdiff for marked changes. From `code`:

```sh
python run.py build-paper --tectonic PATH_TO_TECTONIC
python run.py build-supplement --tectonic PATH_TO_TECTONIC
```

Add `--only-cached` for offline TeX builds after its resources have been cached. The builders update `paper/` and `supplementary_materials/`. The Source Data archive at `data/Source_Data.zip` has one annotated file for each of the six main figures, eight supplementary figures and sixteen supplementary tables, plus exact fixtures, README and checksums.

The supplied T1–T5 response, line references, numerical-occurrence CSV and marked PDFs document the preceding edition. Their original paper and source remain available at [commit 98874b4](https://github.com/pooya-hejazi/uplink-scheduling/tree/98874b4e66491251c2e403de38c22e9ef3bfdf78). To reproduce those historical documents, run the response and diff builders at that commit.

## Six-user receiver and timing results

Each Rice distributed chain-A recording has six transmitters sharing one data slot. The first 512 frames were reserved for amplitude calibration. The receiver scored 1,488 of the 1,489 subsequent frames per recording. Frame 2,000 contained zero samples. Each user contributed 714,240 QPSK symbols or 1,428,480 uncoded bits. Each clock configuration contributed one acquisition.

| Clock | Symbol errors / 4,285,440 | Bit errors / 8,570,880 | BER | Pooled RMS EVM |
|---|---:|---:|---:|---:|
| HUB | 4,717 | 5,084 | 0.0593% | 19.97% |
| LO | 2,593,589 | 3,182,737 | 37.13% | 163.92% |

Obtain a source HDF5 and the accompanying files beginning with `ul_data_b_`, `ul_data_f_` and `ul_data_t_` for users 0–5 from the Rice collection. The capture names are in Supplementary Note 6. The receiver verifies the acquisition SHA-256, the frequency-bin order, the constellation labels and a synthetic zero-noise control. The CSVs contain per-user counts, squared errors and reference energies. The JSON files identify the transmitter-reference digests and calibration gains. These commands accept source files directly. [Rice collection](https://renew.rice.edu/dataset-distributed.html) · [Control records](code/manuscript/revision/payload_data) · [Per-user Fig. 6 data](code/manuscript/source_data)

```sh
python run.py hardware-payload --mode HUB --capture /path/to/hub-chain-A.hdf5 --references /path/to/HUB-sidecars
python run.py hardware-payload --mode LO --capture /path/to/lo-chain-A.hdf5 --references /path/to/LO-sidecars
python run.py lo-alignment --capture /path/to/lo-chain-A.hdf5
```

The separate LO timing sensitivity uses the original four calibration frames and the original pilot energy criterion. Extending its search limits from ±64 to ±96 or ±128 samples moved the sixth user's selected offset from +64 to −94. The six-user data receiver used its fixed common FFT offset throughout. The recordings contain no packet or CRC log for the scheduler's two-user decisions.

For the seven-ceiling comparison, the median sum of seven representative solver calls was 208.45 ms at 32 users and 1,429.72 ms at 64 users. Summing all fifteen archived calls gave 539.58 and 3,732.28 ms. The underlying calls were timed separately. The 395/512 and 426/512 counts apply the rate threshold alone. [Per-topology timings](code/manuscript/supplementary/data/seven_method_call_times.csv)

## Recorded-pilot replay

Obtain original recordings under their source terms from [Rice RENEW](https://renew-wireless.org/dataset-distributed.html) and [Argos](https://renew-wireless.org/dataset-argos.html). Optional original ray scenes come from [DeepMIMO](https://www.deepmimo.net/). Capture identifiers, decoding conventions and scalar summaries are included.

```sh
python run.py hardware-decode --mode HUB
python run.py hardware-evaluate --mode HUB
python run.py round2-hardware --mode HUB
python run.py round3-hardware --mode HUB
python run.py hardware-decode --mode LO
python run.py hardware-evaluate --mode LO
python run.py round2-hardware --mode LO
python run.py round3-hardware --mode LO
```

The decoder checks HTTPS byte ranges, ETags and early-channel hashes. Reconstructed complex channels stay inside the ignored execution workspace; only scalar summaries are copied to `results`. Configure `REQUESTS_CA_BUNDLE` if an institutional TLS proxy requires its trusted CA bundle. TLS verification stays enabled.

The first 256 eligible post-prefix frames calibrate radii (rank 251); 1,614 HUB and 1,513 LO frames test them. Raw and phase-invariant results refer to the observable second LTS. Phase-invariant floors reach median paired fractions 27.51%/24.46%, but LO joint residual coverage remains 75.74%, below nominal 95%. Rate-floor coverage through slack is not evidence of successful nominal calibration. One dependent capture per clock mode does not establish population coverage, oscillator causality or decoded payload throughput.

The third-round check pools per-entry raw and phase-aligned pilot difference powers, their ratios to mean early power, and individual scheduled magnitude residuals before frame maximization. Table 13 states the aggregation. HUB and LO aligned mean powers are 12.249 and 43.954 against an independent unit-noise reference of two. These observations do not identify active-period noise variance or a physical impairment mechanism. Rates are conditional on the quiet-slot noise metric; no correction factor is inferred. `round3-bounds` confirms that the tangent is binding for all 507,904 checked O1 entries. Included scalar data support table regeneration without source recordings.

The illustrations in Figures 1–3 are vector drawings generated by `python run.py figures`. Figure 2 uses the exact rational channel vectors in `code/manuscript/source_data/fig2_channels.csv`. Figure 3 shows a real slice through the complex channel space. Its first two panels are illustrative. The data panels use the archived calibration and test records.

`python run.py round2-summary` also reproduces the zero-price schedule's threshold counts using the smallest verified ceiling on each known topology (Table 6). After preparing the five input archives, `python run.py verify-action-rates` regenerates the per-action rational evaluations for Table 8 under `results/action_rates/`. The frozen scores and archived timings are used in their original cohorts.

## Other stages and integrity

`python run.py --help` lists all entry points, including `build-native`, `verify-scheduler`, `generate-training`, `train`, `confirmatory-test` and `summarize`. These write to the prepared workspace and may require native/GPU dependencies.

`REPOSITORY_SHA256SUMS` covers the delivered files. `code/SOURCE_MAP.csv` records archived source identifiers and original hashes. First-round numerical records and original confirmatory releases are unchanged. Third-party notices remain in place; this review deposit grants no new license to third-party software/data.

The persistent archival DOI is **not yet registered**. At the authors’ request, the prepared deposit remains private and DOI registration is deferred until acceptance. No completed external deposit is implied by the GitHub URL. Confidential editorial documents and related manuscripts are excluded from this repository.
