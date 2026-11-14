"""Issue a scoped machine record only after the required independent jobs pass; verify an existing issuance."""
from pathlib import Path
import csv,datetime,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare import AUD,OUT,path_hash
def rj(n):return json.loads((OUT/(n+'.json')).read_text(encoding='utf-8'))
def rc(n):
    with (OUT/(n+'.csv')).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(p,body):p.write_text(body,encoding='utf-8')
def sig(p):return path_hash(p)+'  '+p.relative_to(AUD).as_posix()+'\n'
def check(man):
    for line in man.read_text().splitlines():
        expected,rel=line.split('  ',1);p=(AUD/rel).resolve()
        assert p.is_relative_to(AUD) and path_hash(p)==expected,rel
def main():
    if not __debug__:raise RuntimeError('Audit assertions must be enabled')
    if sys.argv[1:]==['verify']:
        check(AUD/'CERTIFICATE_SHA256SUMS');check(AUD/'EVIDENCE_SHA256SUMS');print('PASS: both manifests verified');return
    assert not sys.argv[1:]
    files={'receipts':'receipts','sample_dp':'sample_dp','fixtures':'fixtures','statistics_audit':'statistics','hardware':'hardware','exact_small':'exact_small','negative_controls':'negative_controls'}
    for stage,log in files.items():
        assert ('PASS '+stage+'; elapsed ') in (OUT/(log+'.log')).read_text(encoding='utf-8'),stage
    packs=rj('release_integrity');sam=rj('sample_dp_summary');seal=rj('sample_commitment');rec=rj('receipt_summary');fix=rj('fixture_summary');env=rj('environment');build=rj('build');fig=rj('figure_numerics');hw=rj('hardware_scope');ex=rj('exact_two_summary');neg=rj('negative_controls');pt=rc('primary_table');pair=rc('paired_transitions')
    assert sum(v['manifest_entries'] for v in packs.values())==5791
    assert seal['sample_sha256']==path_hash(OUT/'precommitted_sample.csv') and seal['release_sha256']==packs['Gate_3']['sha256']
    assert sam['sampled_units']==58 and sam['k16_registered_optima_checked']==232 and sam['exact_tick_mismatches']==0 and sam['nested_analytic_tables_exhaustively_enumerated']==120
    assert rec['violations']==0 and (rec['distinct'],rec['timing_links'],rec['four_term_nonnegative_identities'])==(8192,12288,8192)
    assert ex['sealed_global_values_enclosed']==512 and fix['violations']==0 and not neg['unexpected_acceptances']
    assert len(hw['argos'])==3 and hw['renew_replayed_frame_rows']==3746 and sum(r['validated_source_ranges'] for r in hw['argos'])==99
    assert [int(r['passed']) for r in pt if r['method']=='det']==[506,504] and [float(r['exact_mcnemar_two_sided']) for r in pair]==[.03125,.0625]
    assert len(rc('receipt_checks'))==8192 and len(rc('rebuilt_block_decisions'))==4096
    spotfile=OUT/'renew_spot_replay.json';spot=rj('renew_spot_replay') if spotfile.is_file() else None
    if spot:
        assert 'PASS renew_ranges; elapsed' in (OUT/'renew_ranges.log').read_text()
        assert [v['mode'] for v in spot['results']]==['HUB','LO']
        ranges_table=rc('renew_spot_range_hashes')
        assert len(ranges_table)==sum(v['verified_http_pages'] for v in spot['results'])
    evidence=sorted([*OUT.glob('*'),*AUD.glob('*.py'),AUD/'README.md'],key=lambda p:p.relative_to(AUD).as_posix())
    manifest=AUD/'EVIDENCE_SHA256SUMS';write(manifest,''.join(sig(p) for p in evidence if p.is_file()))
    issued=datetime.datetime.now(datetime.timezone.utc).isoformat()
    cs=dict(schema='research-gate4-cpu-audit/v1',issued_utc=issued,disposition='PASS_WITH_SCOPE_LIMITS',human_signature=None,
        issuer=dict(role='Separate computational audit role in this session',trained_or_selected_policy=False,wrote_manuscript=False,external_human_or_lab_attestation=False,physical_host_independent=False),
        evidence_sha256=path_hash(manifest),evidence_files=len(evidence),release_packages=packs,sample_commitment=seal,integer_oracle=sam,continuous_two_user=ex,rational_and_compiled_fixtures=fix,receipt_reconstruction=rec,negative_controls=neg,environment=env,native_rebuild=build,
        primary=[dict(k=int(r['k']),method=r['method'],passed=int(r['passed']),n=512,median_gap=float(r['median_G']),median_ms=float(r['median_ms'])) for r in pt],
        paired=[{k:(int(v) if k in ('k','both_pass','det_only','warm_only','neither') else float(v)) for k,v in r.items()} for r in pair],
        structural=fig['native_structure'],hardware=hw,
        verified_claims=['All released Gate 3 primary receipt payloads and all corresponding timing crosslinks and integer ledgers verified from raw simulated channels; no certificate violation detected.','Both locked deterministic usefulness endpoints and both stratified bootstrap lower limits reproduced.','Positive paired warm-start point estimates, strictly below the predeclared K=32 ten-point benefit.','Posterior (not prior) resource conflict is associated with relaxation loss on the stated native K=16 population. No predeclared selectivity crossing.','Archived calibration, phase and net decision summaries on their declared domains; no implication for actual unobserved future propagation.','Two RENEW derived full-capture distributions and raw-window Argos descriptive correlation summaries; no new physical acquisitions.'],
        withheld=['No external human signature or independent laboratory replication.','RENEW complete raw distributed IQ was not re-accessed; only the released derived frame rows and recorded capture identifiers and digests were audited in this run.','Neither clock mode supplies twelve independent layouts; LO also misses 75% usefulness. Original elapsed times were rejoined and summarized, not newly benchmarked.','No blanket two-sided p<0.05 at K=64, preregistered AI superiority, universal phase transition, universal CSI coverage, deployment throughput, or journal acceptance.','Clean build is a functional source rebuild, not a binary-identical build; the released enclosure primitives are shared numerical specifications. CPUs and base mathematical libraries are on the original workstation.'])
    if spot:
        cs['renew_authenticated_source_spot_check']=spot
        cs['withheld'][1]='The complete raw distributed IQ was not re-accessed; one authenticated pilot frame per mode and its eligible calibration noise frames (three HUB, two LO) were checked. Full distributions were independently reconstructed from archived derived frame rows.'
    dest=AUD/'Gate_4_Audit_Certificate.json';write(dest,json.dumps(cs,indent=2,allow_nan=False)+'\n')
    native=rec['witnesses'];md=f"""# Gate 4 audit certificate

**Qualified computational pass · {issued[:10]} UTC**  
**Disposition:** The frozen simulated-input certificates and the two deterministic primary endpoints passed independent CPU replay. The evidence supports a descriptive measured-input result, not an externally replicated hardware or learned-superiority claim.

**Issuer and scope.** A separate computational audit role executed this work on the same workstation. It did not train or select a policy or write the manuscript. This record does not represent a signature by a human auditor, a separate institution or a second experimental laboratory. There is no human signatory or digital signing key. SHA-256 binds the results to the examined bytes; it is not a personal identity credential.

## 1. What was checked

Every entry in each sealed release manifest matched: Gate 1 **11**, Gate 2 **227**, Gate 2B **224** and Gate 3 **5,329**. Gate 2B and Gate 3 also matched their supplied detached archive hashes; Gate 1 matched the ZIP embedded in Gate 2. Gates 1 and 2 did not supply separate detached SHA files. The frozen source/checkpoint entries, pre-test lock, data-manifest, timing-table and decision-table crosslinks matched. Gate 3 archive SHA-256: `{packs['Gate_3']['sha256']}`.

The independent sample was committed before numerical tests. A deterministic SHA-256 ranking of the release-hash-seeded sampling frame selected **58/1,152** topology/tile IDs without replacement (21 native, 30 analytic, seven ray tiles); no block, SNR or failure was replaced. The sample list SHA-256 is `{seal['sample_sha256']}`. At each selected ID, the four registered K=16 optima at −5, 0, 10 and 20 dB agreed **exactly in integer ticks** with a new forward labelled subset program. On the 30 analytic IDs, all **120** nested K=2/4/6/8 tables at 10 dB also matched brute-force enumeration of **78,510** labelled schedules. Only K=16 has an archived discrete objective. Separately, independent rational derivative isolation enclosed all **512/512** released two-user continuous global optima. The K=4/6/8 continuous-power search intervals are not asserted to resolve the optimum.

The original rational and compiled audit suites passed unmodified. An alternative rational enumeration reproduced all six four-user products (four 91/25 and two 1764/625) and the exact aggregate obstruction **2 ln(100/91) = 0.18862135894248… nats**. The six-user example gave relaxation loss and posterior conflict 37/84 and prior spread bound 52/7. A survival-function integration, independent of the archived quadratures, gave vector/projected Gaussian mean gaps of **3.153709814/1.335321612** under per-antenna 10 dB and **5.278436475/3.006443079** under combined 10 dB, with the common full-vector upper endpoint within each convention.

**All 8,192** distinct native receipt hashes matched their compact serialized payloads; **all 12,288** timing entries mapped to their topology, user count, SNR and method. Reconstructed channel bytes and interval tables, full-service pairings, powers, fixed filters, assignment duals and integer blossom inequalities passed. The witness counts were **{native['odd-set']:,} half-scale** and **{native['odd-set4']:,} quarter-scale**. Every individual ledger term matched its recomputed integer and was nonnegative, and every sum equalled U−L. Exact dyadic inner products and outward decimal logarithms separately bounded the achieved rate of **{rec['raw_independent_primal_actions']:,}** distinct actions; repetitions share the identical verified inputs/action. All 4,096 block/size/method classifications and 3,072 cold/warm repeated endpoint comparisons passed. The closest exact gap to the locked threshold was {rec['smallest_threshold_distance']:.8g} bit/s/Hz; the largest displayed upward rounding pad was {rec['largest_upward_display_pad']:.3g} bit/s/Hz. **No numerical violation was found.** Seven intentional corruption controls, including a sum-preserving transfer between two ledger terms, were rejected.

## 2. Confirmatory outcomes

Gap is the worst of the three repeated gaps; reported time is the within-block median, then its across-block median. Values below reproduce the historical complete-call timings from the archive, not a newly timed scheduler. Each size has 128 topologies per native profile; the limit is 0.15 bit/s/Hz and the deadlines are 250/1,000 ms.

| K | Policy | Useful / 512 | Median gap (bit/s/Hz) | Median ms |
|---:|:-------|-------------:|----------------------:|----------:|
"""
    labels={'legacy':'Legacy subgradient','det':'Conflict-polished','standalone':'One-shot neural','hybrid':'Learned warm start'}
    for r in pt:md+=f"| {r['k']} | {labels[r['method']]} | {r['passed']} | {float(r['median_G']):.5f} | {float(r['median_ms']):.2f} |\n"
    md+="""
The stratified 10,000-replicate one-sided 97.5% bootstrap lower bounds for the deterministic method were **0.978515625** (K=32) and **0.97265625** (K=64). Both pass the locked minima. The learned addition rescued **6/6** (K=32) and **5/8** (K=64), losing no previously useful block; three K=64 blocks failed both. Absolute paired gains were 1.171875 and 0.9765625 percentage points, with 95% stratified bootstrap intervals [0.390625, 2.1484375] and [0.1953125, 1.953125] points. The predeclared ten-point learning criterion failed. As a separately labelled descriptive check, two-sided exact McNemar p-values were **0.03125 and 0.0625** (one-sided in the favourable direction: 0.015625 and 0.03125). A claim of two-sided p<0.05 at both sizes is not supported.

Native K=16, 10 dB: the posterior correlation with exact labelled relaxation loss was 0.665177, 95% topology bootstrap [0.601494, 0.723115]; the prior correlation was −0.005082 [−0.092949, 0.079959]. None of the 128 analytic topologies was conflict-dominant at any of nine registered interpolation settings. At K=32, 10 dB, both CDL-C pilot arms passed the utility rule on 128/128 blocks; UMa passed on 83/128 (fixed) and 127/128 (scaled). Joint hit counts were 120/128 on CDL-C and 127/128 on UMa. No per-profile exact binomial flag fired; non-rejection does not mean no missed blocks. The underlying phase and net summaries and both guarded ray-scene median curves were independently regenerated. A conditional association, performance under these rules, or a recorded-input certificate does not guarantee arbitrary deployment performance.

## 3. Measurement boundary and reproducibility

The released RENEW frame ledger yielded **1,867/1,873 (99.68%) HUB** and **1,037/1,873 (55.37%) LO**, including three and 104 abstentions, respectively. Median eligible-frame times were 2.755 and 2.708 ms; median later-pilot rate minus early lower bound was −2.501 and −4.873 bit/s/Hz. There is one primary distributed capture per clock mode; LO missed the 75% target. Their source-file hashes and the entire post-prefix frame ledger/empirical distributions were checked against the immutable release. The complete 4.67-GB-per-file RENEW IQ was **not re-accessed**; published file digests were crosschecked as identifiers, not recomputed against absent bytes. No population-level clock-mode or latent-channel sign-off is issued.

For Argos, all 99 authenticated private recording ranges and three first-frame hashes matched. A separate FFT and quality-mask implementation reproduced all 96 planned frame decisions and all 1,440 finite pair/frame statistics. Of 32 planned frames per condition, 31 static, 32 environmental and 22 mobile frames passed. Median first-pilot squared user-channel correlations were 0.225020, 0.240239 and 0.224980 on one array. No IQ or estimated channel is redistributed. This secondary measurement does not increase the number of independent distributed-clock layouts.

The clean isolated CPU environment used Python 3.13.5, NumPy 2.3.4, SciPy 1.16.3, Numba 0.62.1, llvmlite 0.45.1 and NetworkX 3.4.2. The original outward rounding primitives were rebuilt without fast-math, while the DP, combinatorial ledger checker and exact physical action tests were written separately. The C++14 LEMON 1.3.1 helper was compiled from the authenticated release source with Zig 0.13.0, `-std=c++14 -O3 -DNDEBUG -DWIN32 -shared`, in new local and global compiler caches. Its rebuilt DLL digest differs from the published DLL, so only **functional** rebuild, not bitwise binary reproducibility, is certified; 21 matching controls passed. Python assertions were enabled, CUDA disabled, training/inference absent and numerical thread counts fixed at one. The compiler hashes, native-library and optional-MKL initialization notes are provided with the reproduction instructions.

**Disposition.** Qualified sign-off covers the numerical and simulation claims above, and the two descriptive levels of hardware evidence exactly as stated. The requirements for external hardware replication and preregistered AI superiority were not met. The recommended publication route in the roadmap is therefore Communications Engineering; submission and editorial assessment are separate.

The accompanying machine-readable certificate lists the evidence manifest digest. The sample frame, sample selections, primary table/figure, per-receipt results, DP ticks, exact paired analyses, exclusions, raw-input identifiers and full rerun instructions are supplied in the audit directory.
"""
    if spot:
        hx,lx=spot['results'];rechecked=sum(v['verified_http_bytes'] for v in spot['results']);pages=sum(v['verified_http_pages'] for v in spot['results'])
        note=f"A separate fresh HTTPS range read authenticated **{pages} source pages ({rechecked:,} bytes)** against archived digests and ETags. For the first preregistered six-user sensitivity frame (128) and its eligible calibration noise windows ({len(hx['noise_calibration_frames'])} HUB, {len(lx['noise_calibration_frames'])} LO), independent FFT/whitening reproduced the three-tone mean pair correlation: **{hx['recomputed_three_tone_mean_pair_rho']:.9f} HUB** and **{lx['recomputed_three_tone_mean_pair_rho']:.9f} LO**. The spot check is distinct from the full-frame primary distributions and does not verify all original IQ. The complete capture digests remain source identifiers; raw samples were held only in memory."
        md=md.replace('No population-level clock-mode or latent-channel sign-off is issued.',note+' No population-level clock-mode or latent-channel sign-off is issued.')
    mdpath=AUD/'Gate_4_Audit_Certificate.md';write(mdpath,md)
    write(AUD/'CERTIFICATE_SHA256SUMS',''.join(sig(p) for p in [manifest,dest,mdpath]))
    check(manifest);check(AUD/'CERTIFICATE_SHA256SUMS');print(f'Issued qualified certificate, {len(evidence)} evidence files. SHA256 {path_hash(dest)}',flush=True)
if __name__=='__main__':main()
