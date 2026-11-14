# Independent CPU audit: reproduction and evidence

The authoritative inputs are the four sealed Gate 1/2/2B/3 ZIPs. The audited source tree is extracted into a new scratch directory. Apart from restricted Argos IQ windows, none of the input data or scientific code are taken from the editable project checkout. No network, training, learned inference or GPU is needed for the computational audit of released inputs. Only the separate RENEW source-window re-fetch needs a network connection. The verifier recomputes evidence for frozen decisions; its wall times are not scheduler benchmarks.

## Reproduce

Use a 64-bit Windows CPython 3.13.5 with the distribution versions in `results/environment.json` available locally. The original machine uses Anaconda. `prepare.py environment` installs only the named packages in a new virtual environment (hard links or copies; no inherited site-packages), with a clear boundary around the base Python standard library and native math libraries. Python runs in isolated mode, with assertions enabled, eager imports from the extracted sources, a fresh Numba cache and one numerical thread. No model checkpoint, released match DLL, PYTHONPATH, or user site directory is imported. Under this isolated installation NumPy emits a warning about absent optional mkl-service; it is retained in the logs. The fixed-thread calculations and raw-channel hashes passed. Use a new scratch directory for each audit; allow about 3 GB for local compilation.

Set `GATE_RELEASES` to the containing directory of the unchanged ZIPs (and Gate 2B/3 sidecars); `GATE4_SCRATCH` to a new directory; and `GATE4_TOOL_ARCHIVES` to the directory containing the Zig 0.13.0 Windows archive **and its extracted distribution**, and the LEMON 1.3.1 source tarball. `prepare.py build` checks the complete installed compiler distribution against its release ZIP and the ZIP and LEMON tarball against the recorded digests. It unpacks LEMON afresh; its local and global Zig caches begin empty. Use the two source URLs in the sealed `Gate_2B/build_native.py` if obtaining the archives normally.

For the optional independently decoded Argos branch, set `GATE4_ARGOS_PRIVATE` to the authorized private directory containing `static.npz`, `env.npz` and `mob.npz` made by the archived `Gate_3/argos_fetch.py`. The extractor specifies the public file IDs, HTTP ranges, ETags, calibration window and 32 evaluation-frame IDs per recording; follow the original data provider's access terms. Each window is checked against the cryptographic hashes in the released range manifest before use. No private file is redistributed. The RENEW distribution calculation uses publicable, release-hashed derived records. Whole source hashes, sizes and IDs are given in `results/hardware_scope.json`.

In PowerShell, from this audit directory:

```powershell
$py = 'C:/ProgramData/anaconda3/python.exe'
& $py -I prepare.py sample
& $py -I prepare.py validate
& $py -I prepare.py environment
& $py -I prepare.py hardware_io
& $py -I prepare.py build
$jobs = 'receipts','sample_dp','fixtures','negative_controls','exact_small','statistics_audit','hardware'
foreach ($job in $jobs) {
    if ($LASTEXITCODE -ne 0) { throw 'Previous audit command failed.' }
    & $py -I driver.py $job
}
if ($LASTEXITCODE -ne 0) { throw 'Audit job failed.' }
& $py -I driver.py renew_ranges *> results/renew_ranges.log
if ($LASTEXITCODE -ne 0) { throw 'Optional raw Rice spot replay did not complete.' }
& $py -I issue.py
```

The original run redirected each job's stdout/stderr to `results/*.log`. To regenerate the archived logs, apply `*> results/<job>.log` to its command. `issue.py` checks signed-off result counts; write the normal log names listed there when issuing a new certificate. Timestamps, paths, elapsed times and compiler output are necessarily machine-dependent; compare integer answers, receiver/table hashes, package digests and numerical decisions. To verify an existing local evidence manifest, run `python -I issue.py verify`. A regenerated manifest records the new environment and attestation date.

## What the checks mean

- **Sampling:** `prepare.py sample`, `results/sample_commitment.json`, full eligible population and selected list. Rank all 1,152 native/analytic/ray IDs by a domain-separated SHA-256 hash seeded by the sealed Gate 3 ZIP. Take the first 58, without replacement, before numerical checks. Analytical siblings, nested user counts and the four SNRs do not count as new independent units.
- **Integer optima:** `sample_dp.py` uses a newly written forward subset DP; it does not import the released DP for the 232 sealed K=16 comparisons. Every subset stores a score for its first |subset|/2 labelled tones; the recurrence adds an unused pair to the next tone. Independently enumerate the smaller available K=2/4/6/8 analytic problem sizes on the sampled units (78,510 labelled schedules in total). Only K=16 has an archived integer DP value. The small-instance comparison is exhaustive on a rebuilt integer table; it does not equate a priced table optimum with a continuous-power maximum.
- **Raw receipt verification:** `receipts.py` uses the released, freshly JIT-compiled enclosure primitives as the numerical specification. The surrounding checker was reimplemented: input and every covered weighted-table hash, every blossom edge inequality and dual objective, the assignment certificate, resource bijections, power feasibility, pairwise lower rates, four signed integer terms, normalized gap and all timing joins. Common table reconstructions are reused only for identical witness inputs. A separate exact binary-rational evaluation of the implemented receiver, plus outward decimal logarithms, checks the physical rate without using the released rate enclosure. A repeated action's independently verified rate is reused after requiring the exact same channel, assignment, power, receiver and pairwise lower ticks. Thresholds are bracketed with 70-digit arithmetic; the stated conclusions do not depend on a decimal printed in the paper. `negative_controls.py` verifies that corrupt numerical certificates are actually rejected.
- **Fixtures and native build:** `fixtures.py` independently enumerates the exact tables and the physical four-user example, compares compiled log endpoints to Decimal, tests the rebuilt half/quarter-scale matching witnesses, and integrates the Gaussian order law via the survival function. The two complete archived rational and compiled suites are also executed unmodified. `exact_small.py` independently bounds every two-user analytic global optimum by a rational cubic derivative in the Bernstein basis; no numerical optimizer is invoked.
- **Statistics:** `statistics_audit.py` regenerates the primary table, paired transition counts, one-/two-sided exact paired sign probabilities, 10,000-replicate stratified bootstrap and an independent vector primary figure. It checks the native structural correlations and topology bootstrap, all 1,152 interpolation decisions, 12 calibration/utility cells, component swaps, DeepMIMO median cells, phase risks, net horizons and RENEW frame totals. Statistical estimates check archived study claims; neither a bootstrap interval nor a coverage non-rejection is a proof of conditional coverage.
- **Measurements:** `hardware.py` decodes authenticated private Argos windows with independent FFT, calibration, quality screening and 15-by-52 user-pair/tone calculations. It regenerates complete RENEW gap/time/aging distributions from the released frame ledger, leaving abstentions in the denominator. It does not re-acquire the two complete distributed-clock IQ recordings.

The resulting certificate is a machine-issued, scoped record by a technically separate audit role within the same authoring session/workstation. The parent commissions the work and handles the manuscript; the computational audit role did not develop or train any study policy or write the manuscript. No external laboratory affiliation, named auditor, handwritten signature, independent hardware acquisition or new site replication is implied.

The separately requested `renew_ranges.py` source-window check uses h5py 3.12.1 plus Python’s standard HTTPS library. It reads only pages already hashed in the Gate 3 range manifest and rejects a changed HTTP range, ETag, length, host or digest. It requests one six-user pilot frame (128) in each distributed-clock sensitivity trace and its eligible calibration noise frames (three HUB and two LO), calculates the mean pair correlation, and keeps the IQ only in memory. The full RENEW all-frame primary timings are still reconstructed only from archived numerical rows.
