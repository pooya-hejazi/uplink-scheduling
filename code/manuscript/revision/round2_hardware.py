"""Phase-invariant pilot diagnostics; only scalar outputs are distributable."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import quad
from threadpoolctl import threadpool_limits

import reviewer_hardware as original
from audit import replay

OUT = Path(__file__).resolve().parent / 'round2_data'
OUT.mkdir(exist_ok=True)


def phase_scores(h, later, act):
    phase = np.angle(np.sum(h.conj()*later, axis=1))
    aligned = later*np.exp(-1j*phase)[:, None, :]
    full = float(np.linalg.norm(aligned-h, axis=1).max())
    pairs, powers, receivers = act
    tones = np.arange(3)
    projected = 0.
    for t in (0, 1):
        d = receivers[:, t]/np.linalg.norm(receivers[:, t], axis=1)[:, None]
        for j in (0, 1):
            a = abs(np.sum(d.conj()*h[pairs[:, j], :, tones], axis=1))
            b = abs(np.sum(d.conj()*later[pairs[:, j], :, tones], axis=1))
            projected = max(projected, float(abs(b-a).max()))
    return full, projected


def thermal_benchmark(actions, dimensions, seed):
    # A fixed-filter noise-only reference, not a fitted model of the observed residuals.
    rng = np.random.default_rng(seed)
    maxima = []
    tones = np.arange(3)
    for pairs, _, receivers in actions[:256]:
        noise = rng.normal(size=(64, 6, dimensions, 3))+1j*rng.normal(size=(64, 6, dimensions, 3))
        scores = np.zeros(64)
        for t in (0, 1):
            d = receivers[:, t]/np.linalg.norm(receivers[:, t], axis=1)[:, None]
            for j in (0, 1):
                selected = np.stack([noise[:, user, :, tone] for user, tone in zip(pairs[:, j], tones)], axis=1)
                projection = np.sum(selected*d.conj()[None, :, :], axis=2)
                scores = np.maximum(scores, abs(projection).max(axis=1))
        maxima.extend(scores)
    a = np.asarray(maxima)
    independent_mean = quad(lambda x: -np.expm1(12*np.log1p(-np.exp(-x*x/2))) if x > 0 else 1., 0, 12, epsabs=1e-10)[0]
    return dict(draws=len(a), seed=seed, expected_max=float(a.mean()), monte_carlo_se=float(a.std(ddof=1)/np.sqrt(len(a))),
                q975=float(np.quantile(a, .975)), independent_12_projection_expected_max=independent_mean,
                union_bound_q975=float(np.sqrt(2*np.log(12/.025))),
                assumptions='Independent unit-variance proper complex noise in each pilot; difference variance 2; observed early filters held fixed. This isolates thermal noise and does not model filter-selection dependence or hardware drift.')


def evaluate(mode):
    z = np.load(original.PRIVATE / (mode+'.npz'))
    raw = pd.read_csv(original.OUT / ('hardware_calibration_'+mode+'.csv')).set_index('frame')
    assert np.array_equal(z['frames'], raw.index.to_numpy())
    I, J = np.triu_indices(6, 1)
    actions, scores, phase_rows = [], [], []
    for index, (frame, h, later) in enumerate(zip(z['frames'], z['early'], z['later'])):
        assert original.solver.digest(h) == raw.loc[frame, 'early_input_sha256']
        assert original.solver.digest(later) == raw.loc[frame, 'later_input_sha256']
        act = original.solver.make_action(h, I, J, 'subgrad')
        actions.append(act)
        scores.append(phase_scores(h, later, act))
        phase = np.angle(np.sum(h.conj()*later, axis=(1, 2)))
        for user, value in enumerate(phase):
            phase_rows.append(dict(mode=mode, frame=int(frame), user=user, split='calibration' if index < 256 else 'test',
                                   phase_rad=float(value), absolute_phase_rad=float(abs(value)),
                                   equivalent_cfo_khz=float(value/(2*np.pi*16e-6)/1000)))
        if index == 0:
            rotated = later*np.exp(1j*np.random.default_rng(717).uniform(-np.pi, np.pi, (6, 1, 3)))
            assert abs(original.rate(later, act)-original.rate(rotated, act)) < 1e-10
            assert np.allclose(phase_scores(h, later, act), phase_scores(h, rotated, act), rtol=1e-12, atol=1e-10)
    scores = np.asarray(scores)
    rank = math.ceil(257*.975)
    assert rank == 251
    qf, qp = np.nextafter(np.sort(scores[:256], axis=0)[rank-1], np.inf)
    rows = []
    for index, (frame, h, later, act) in enumerate(zip(z['frames'], z['early'], z['later'], actions)):
        observed = original.rate(later, act)
        assert abs(observed-raw.loc[frame, 'later_rate']) < 1e-10
        row = dict(mode=mode, frame=int(frame), split='calibration' if index < 256 else 'test',
                   F_score=scores[index, 0], P_score=scores[index, 1], qF=qf, qP=qp, later_rate=observed,
                   early_input_sha256=raw.loc[frame, 'early_input_sha256'], later_input_sha256=raw.loc[frame, 'later_input_sha256'])
        if index >= 256:
            rec, _, _ = original.solver.solve(h, 'subgrad', eps=qf, proj=qp, action=act)
            replay(h, rec, qf, qp)
            norm = 3*np.log(2)
            lp = sum(rec['LP_pair'])/original.Q/norm
            lf = sum(rec['LF_pair'])/original.Q/norm
            upper = int(rec['U'])/int(rec['den'])/norm
            hitf, hitp = scores[index] <= [qf, qp]
            assert not hitp or observed >= lp-1e-10
            assert not hitf or lf-1e-10 <= observed <= upper+1e-10
            row.update(LP=lp, LF=lf, U_F=upper, projected_width=upper-lp,
                       covered_floor=int(observed >= lp-1e-10), covered_interval=int(max(lp, lf)-1e-10 <= observed <= upper+1e-10),
                       hitF=int(hitf), hitP=int(hitp), joint=int(hitf and hitp))
        rows.append(row)
        if index % 128 == 127:
            print(mode, 'phase-invariant replay', index+1, '/', len(raw), flush=True)
    data = pd.DataFrame(rows)
    data.to_csv(OUT / ('hardware_phase_'+mode+'.csv'), index=False)
    phases = pd.DataFrame(phase_rows)
    phases.to_csv(OUT / ('hardware_phase_rotations_'+mode+'.csv'), index=False)
    reports = []
    for method, d in [('raw complex difference', raw.reset_index()), ('phase invariant', data)]:
        test = d.query("split == 'test'")
        reports.append(dict(mode=mode, method=method, n_calibration=256, n_test=len(test), rank=rank,
                            qF=float(d.qF.iloc[0]), qP=float(d.qP.iloc[0]), radius_ratio=float(d.qF.iloc[0]/d.qP.iloc[0]),
                            median_LF=float(test.LF.median()), median_LP=float(test.LP.median()), median_UF=float(test.U_F.median()),
                            median_later_rate=float(test.later_rate.median()), median_width=float(test.projected_width.median()),
                            median_paired_floor_pct=float((100*test.LP/test.later_rate).median()),
                            ratio_of_median_floor_to_rate_pct=float(100*test.LP.median()/test.later_rate.median()),
                            floor_coverage=float(test.covered_floor.mean()), interval_coverage=float(test.covered_interval.mean()),
                            joint_score_coverage=float(test.joint.mean()), positive_floors=int((test.LP > 0).sum())))
    pd.DataFrame(reports).to_csv(OUT / ('hardware_comparison_'+mode+'.csv'), index=False)
    p = phases.query("split == 'test'")
    phase_summary = {key: float(p.absolute_phase_rad.quantile(q)) for key, q in [('q25_absolute_phase_rad', .25), ('median_absolute_phase_rad', .5), ('q75_absolute_phase_rad', .75)]}
    phase_summary.update({key.replace('phase_rad', 'cfo_khz'): value/(2*np.pi*16e-6)/1000 for key, value in list(phase_summary.items())})
    report = dict(mode=mode, phase_distribution_unit='user-frame; pooled six users on test frames, inner product across receive coordinates and the three selected tones',
                  **phase_summary, thermal=thermal_benchmark(actions, z['early'].shape[2], 714 if mode == 'HUB' else 715), summaries=reports,
                  interpretation='Equivalent phase/CFO descriptors are not an identification of oscillator drift. Phase-invariant scores use per-user/per-tone vector alignment and direct projection magnitudes. Coverage is descriptive within one temporally dependent recording per mode.')
    (OUT / ('hardware_phase_'+mode+'.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['HUB', 'LO'])
    args = parser.parse_args()
    with threadpool_limits(1):
        evaluate(args.mode)
