"""Build aggregate hardware supplement figures and verify their archived evidence."""
from pathlib import Path
import csv
import hashlib
import json
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / 'data'
FIG = HERE / 'figures'
AUDIT = ROOT / 'Gate_4/audit/results'
DATA.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)


def read(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (DATA / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def argos():
    # Reuse the published decoder without running its file-writing entry point.
    sys.path.insert(0, str(ROOT / 'Gate_3'))
    import argos as decoder
    decoder.control()
    cached = ROOT / 'Gate_3/rice_private/argos'
    source = ROOT / 'Gate_3/results/argos'
    saved = read(source / 'pair_frames.csv')
    saved = {(r['regime'], int(r['frame']), int(r['user_i']), int(r['user_j'])): r for r in saved}
    summary = load(ROOT / 'Gate_3/results/argos_summary.json')
    rows, frame_rows, hash_rows = [], [], []
    for regime in summary['regimes']:
        mode = regime['regime']
        ranges = load(source / f'{mode}_ranges.json')
        assert ranges['policy_sha256'] == hashlib.sha256((ROOT / 'Gate_3/ARGOS_PROTOCOL.md').read_bytes()).hexdigest()
        with np.load(cached / f'{mode}.npz', allow_pickle=False) as archive:
            cal, evaluation, frames = (archive[k] for k in ('cal', 'evaluation', 'frame'))
        parts = ranges['raw_ranges']
        assert len(cal) == 64 and len(frames) == len(evaluation) == 32 and len(parts) == 33
        assert digest(cal) == parts[0]['sha256']
        assert digest(cal[0]) == ranges['initial_h5py_frame0_sha256']
        assert np.array_equal(frames, 64 + ((2 * np.arange(32) + 1) * (ranges['total_frames'] - 64)) // 64)
        cc, coherence = decoder.quality(decoder.transform(cal))
        active = np.flatnonzero(np.any((np.median(cc, axis=0) >= 6) & (np.median(coherence, axis=0) >= .60), axis=0))
        assert active.tolist() == regime['rf_indices'] == list(range(8))
        transformed = decoder.transform(evaluation)
        cc, coherence = decoder.quality(transformed)
        accepted = []
        for index, (raw, frame, part) in enumerate(zip(evaluation, frames, parts[1:])):
            assert digest(raw) == part['sha256'] and int(frame) == part['start']
            channels = transformed[index, :, :6][:, :, active][..., decoder.BINS]
            values = np.stack([decoder.pairs(channel) for channel in channels])
            good = np.min(np.median(cc[index][:, active], axis=1)) >= 3 and np.min(np.median(coherence[index][:, active], axis=1)) >= .50
            for pair_index, (u, v) in enumerate(decoder.IJ):
                original = saved[mode, int(frame), int(u + 1), int(v + 1)]
                assert good == bool(int(original['quality_pass']))
                assert np.allclose(values[:, pair_index].mean(axis=-1), [float(original['rho_first']), float(original['rho_second'])], rtol=1e-12, atol=2e-13)
            means = values.mean(axis=(1, 2))
            frame_rows.append(dict(regime=mode, frame=int(frame), retained=int(good), first=means[0], second=means[1], paired_change=means[1]-means[0]))
            if good:
                accepted.append(values.mean(axis=-1))
        accepted = np.stack(accepted)
        assert len(accepted) == regime['frames_accepted']
        assert np.allclose(np.quantile(accepted[:, 0].mean(axis=1), [.25, .5, .75]), regime['first_lts_quartiles'])
        for pair_index, (u, v) in enumerate(decoder.IJ):
            values = np.median(accepted[:, :, pair_index], axis=0)
            rows.append(dict(regime=mode, user_i=int(u+1), user_j=int(v+1), frames=len(accepted), first=values[0], second=values[1]))
        hash_rows.append(dict(regime=mode, source_ranges_verified=len(parts), frame_zero_verified=1, retained=len(accepted), planned=32))
    write('hardware_argos_pairs.csv', rows)
    write('hardware_argos_frames.csv', frame_rows)
    write('hardware_argos_hash_checks.csv', hash_rows)
    plot_argos(frame_rows)


def plot_argos(frame_rows):
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.8), constrained_layout=True)
    rng=np.random.default_rng(382)
    for j,(mode,col) in enumerate(zip(('static','env','mob'),('#244a70','#007e83','#7967a6'))):
        z=[r for r in frame_rows if r['regime']==mode and int(r['retained'])]
        first=np.array([float(r['first']) for r in z]);second=np.array([float(r['second']) for r in z])
        axes[0].scatter(j+rng.uniform(-.13,.13,len(z)),first,s=12,color=col,alpha=.5,edgecolors='none')
        axes[0].plot([j-.22,j+.22],[np.median(first)]*2,color='#173546',lw=2)
        for x,y in zip(first,second):axes[1].plot([j-.19,j+.19],[x,y],color=col,alpha=.25,lw=.6)
        axes[1].plot([j-.19,j+.19],[np.median(first),np.median(second)],'o-',color=col,ms=4)
        axes[1].text(j,.315,f'{len(z)}/32',ha='center',fontsize=8)
    for ax,letter in zip(axes,'ab'):
        ax.set(xlim=(-.45,2.45),xticks=range(3),xticklabels=['Static','Environmental','Mobile'],ylabel='Mean squared correlation',ylim=(.135,.335))
        ax.set_title(letter,loc='left',fontweight='bold');ax.grid(axis='y',alpha=.2)
    axes[1].set_xlabel('Left: first pilot; right: second pilot')
    fig.savefig(FIG/'sfig8.pdf',bbox_inches='tight');plt.close(fig)



def renew():
    frames = read(AUDIT / 'renew_all_postprefix_frames.csv')
    assert len(frames) == 3746
    aliases = load(ROOT / 'Gate_2/results/rice_alias_audit.json')
    assert [(r['overlapping_chunks'], r['equal_hashes']) for r in aliases] == [(24, 24), (22, 22)]
    alias_rows = []
    for entry in aliases:
        chain = entry['chain']
        colocated = load(ROOT / f'Gate_2/results/rice_activity_colocated_HUB_NLoS_{chain}.json')
        distributed = load(ROOT / f'Gate_2/results/rice_activity_distributed_HUB_LoS_{chain}.json')
        common = sorted(set(colocated['range_sha256']) & set(distributed['range_sha256']))
        assert len(common) == entry['overlapping_chunks']
        assert colocated['pilot_adc_power_by_frame'] == distributed['pilot_adc_power_by_frame']
        assert colocated['noise_adc_power_by_frame'] == distributed['noise_adc_power_by_frame']
        for byte_range in common:
            value = colocated['range_sha256'][byte_range]
            assert value == distributed['range_sha256'][byte_range]
            alias_rows.append(dict(chain=chain, byte_range=byte_range, matching_sha256=value))
    write('hardware_renew_mirror_ranges.csv', alias_rows)
    mappings = []
    for path in sorted((ROOT / 'Gate_2/results').glob('rice_meta_*.json')):
        attrs = load(path)['attrs']
        time = np.asarray(attrs['OFDM_PILOT'])
        frequency = np.asarray(attrs['OFDM_PILOT_F'])
        pilot = time[::2] + 1j*time[1::2]
        recorded = frequency[::2] + 1j*frequency[1::2]
        spectrum = np.fft.fft(pilot)
        shifted = np.max(abs(np.fft.fftshift(spectrum)-recorded)) < 1e-5
        assert shifted or np.max(abs(spectrum-recorded)) < 1e-5
        data = np.sort(attrs['OFDM_DATA_SC'])
        physical = data-32 if shifted else (data+32) % 64-32
        positions = np.argsort(physical)[[12, 24, 36]]
        assert physical[positions].tolist() == [-13, 1, 14]
        for signed, storage in zip(physical[positions], data[positions]):
            mappings.append(dict(stratum=path.stem.removeprefix('rice_meta_'), fft_shifted=int(shifted), signed_bin=int(signed), storage_bin=int(storage)))
    assert len(mappings) == 24
    write('hardware_renew_bin_mapping.csv', mappings)
    nested = read(ROOT / 'Gate_3/results/rice_field_summary.csv')
    assert len(nested) == 21 and {int(r['k']) for r in nested} == {2, 4, 6}
    write('hardware_renew_nested.csv', nested)
    write('hardware_renew_frames.csv', frames)
    totals = read(AUDIT / 'renew_capture_totals.csv')
    for row in totals:
        selected = [r for r in frames if r['mode'] == row['mode']]
        assert len(selected) == int(row['denominator']) == 1873
        assert sum(int(r['retained']) for r in selected) == int(row['retained'])
        assert sum(int(r['useful']) for r in selected) == int(row['useful'])
    write('hardware_renew_totals.csv', totals)
    fig, axes = plt.subplots(1, 3, figsize=(8, 2.7), constrained_layout=True)
    for mode, color in [('HUB', '#277da1'), ('LO', '#d76b27')]:
        selected = [r for r in frames if r['mode'] == mode and int(r['retained'])]
        for ax, field in zip(axes[:2], ('gap', 'later_minus_early')):
            values = np.sort([float(r[field]) for r in selected])
            ax.step(values, np.arange(1, len(values)+1)/1873, where='post', color=color, label=mode)
    axes[0].set_xscale('log')
    axes[0].set_xlabel('Recorded-input gap (bit/s/Hz)')
    axes[1].set_xlabel('Later-LTS rate minus early L (bit/s/Hz)')
    axes[0].set_ylabel('Fraction of all 1,873 post-prefix frames')
    axes[0].legend(frameon=False)
    for ax in axes[:2]:
        ax.set_ylim(0, 1.02)
    for chain, marker in [('A', 'o'), ('B', 's')]:
        for prefix, color in [('colocated_HUB_LoS_', '#777777'), ('distributed_HUB_LoS_', '#277da1'), ('distributed_LO_LoS_', '#d76b27')]:
            selected = [r for r in nested if r['stratum'] == prefix+chain]
            if selected:
                axes[2].plot([int(r['k']) for r in selected], [float(r['median_G']) for r in selected], marker=marker, color=color, label=prefix.replace('colocated_HUB_LoS_', 'Coloc. ').replace('distributed_HUB_LoS_', 'HUB ').replace('distributed_LO_LoS_', 'LO ')+chain)
    axes[2].set_yscale('log')
    axes[2].set_xticks([2, 4, 6])
    axes[2].set_xlabel('Nested users K')
    axes[2].set_ylabel('Median gap (bit/s/Hz)')
    axes[2].legend(fontsize=6, frameon=False)
    for ax, letter in zip(axes, 'abc'):
        ax.set_title(letter, loc='left', fontweight='bold')
    fig.savefig(FIG / 'sfig7.pdf')
    plt.close(fig)


def audit():
    receipts = read(AUDIT / 'receipt_checks.csv')
    sample = read(AUDIT / 'sample_dp.csv')
    nested = read(AUDIT / 'nested_small_dp.csv')
    exact = read(AUDIT / 'exact_two_replay.csv')
    controls = load(AUDIT / 'negative_controls.json')
    assert len(receipts) == len({r['receipt_sha256'] for r in receipts}) == 8192
    assert len(sample) == 232 and all(r['sealed_dp_H'] == r['forward_dp_H'] for r in sample)
    assert len(nested) == 120 and all(r['forward_dp_H'] == r['bruteforce_H'] for r in nested)
    assert sum(int(r['enumerated_labelled_schedules']) for r in nested) == 78510
    assert len(exact) == 512 and len(controls['rejected']) == 7 and controls['unexpected_acceptances'] == 0
    commitment = load(AUDIT / 'sample_commitment.json')
    assert len(read(AUDIT / 'precommitted_sample.csv')) == commitment['selected'] == 58
    assert hashlib.sha256((AUDIT / 'precommitted_sample.csv').read_bytes()).hexdigest() == commitment['sample_sha256']
    summary = load(AUDIT / 'receipt_summary.json')
    assert summary['timing_links'] == 12288 and summary['violations'] == 0
    timings = read(ROOT / 'Gate_3/results/times.csv')
    by_digest = {r['receipt_sha256']: r for r in receipts}
    assert len(timings) == 12288 and {r['receipt_sha'] for r in timings} == set(by_digest)
    for timing in timings:
        receipt = by_digest[timing['receipt_sha']]
        assert all(timing[key] == receipt[key] for key in ('family', 'block', 'k', 'db', 'method', 'witness'))
        assert int(timing['rep']) >= int(receipt['first_rep'])
        assert float(timing['G']) == float(receipt['G'])
    rows = [dict(check='distinct_receipts', count=len(receipts)), dict(check='archived_timing_links', count=summary['timing_links']), dict(check='precommitted_units', count=58), dict(check='k16_integer_dp_matches', count=len(sample)), dict(check='small_bruteforce_tables', count=len(nested)), dict(check='small_labelled_schedules', count=78510), dict(check='two_user_global_intervals', count=len(exact)), dict(check='rejected_corruptions', count=len(controls['rejected']))]
    write('hardware_audit_counts.csv', rows)


if __name__ == '__main__':
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'pdf.fonttype': 42})
    argos()
    renew()
    audit()
    print('Verified Argos cached-IQ aggregates, RENEW archived rows, and audit counts; wrote Supplementary Figures 7 and 8.')
