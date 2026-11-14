"""Stored-pilot noise-scale and O1 binding-bound checks; distribute scalars only."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import reviewer_hardware as original
from round2_hardware import phase_scores

OUT = Path(__file__).resolve().parent / 'round3_data'


def hardware(mode):
    with np.load(original.PRIVATE / (mode+'.npz')) as z:
        frames, early, later = z['frames'][256:], z['early'][256:], z['later'][256:]
    expected = pd.read_csv(OUT.parent/'round2_data'/f'hardware_phase_{mode}.csv').query("split == 'test'").set_index('frame')
    assert np.array_equal(frames, expected.index) and len(frames) == {'HUB': 1614, 'LO': 1513}[mode]
    phase = np.angle(np.sum(early.conj()*later, axis=2))
    aligned = later*np.exp(-1j*phase)[:, :, None, :]
    raw_power, phase_power, early_power = abs(later-early)**2, abs(aligned-early)**2, abs(early)**2
    assert np.all(phase_power.sum(axis=2) <= raw_power.sum(axis=2)+1e-8)
    projections, rows = [], []
    I, J = np.triu_indices(6, 1)
    for frame, h, ref, raw, adjusted in zip(frames, early, later, raw_power, phase_power):
        old = expected.loc[frame]
        assert original.solver.digest(h) == old.early_input_sha256
        assert original.solver.digest(ref) == old.later_input_sha256
        act = original.solver.make_action(h, I, J, 'subgrad')
        pairs, _, receivers = act
        terms = []
        for t in (0, 1):
            d = receivers[:, t]/np.linalg.norm(receivers[:, t], axis=1)[:, None]
            for j in (0, 1):
                a = abs(np.sum(d.conj()*h[pairs[:, j], :, np.arange(3)], axis=1))
                b = abs(np.sum(d.conj()*ref[pairs[:, j], :, np.arange(3)], axis=1))
                terms.extend(abs(b-a))
        assert len(terms) == 12 and np.isclose(max(terms), old.P_score, rtol=1e-12, atol=1e-10)
        if not projections:
            rotated = ref*np.exp(1j*np.random.default_rng(717).uniform(-np.pi, np.pi, (6, 1, 3)))
            assert np.allclose(phase_scores(h, ref, act), phase_scores(h, rotated, act), rtol=1e-12, atol=1e-10)
        projections.extend(terms)
        rows.append(dict(mode=mode, frame=int(frame), raw_mean=float(raw.mean()), phase_mean=float(adjusted.mean()),
                         early_mean=float((abs(h)**2).mean()), projection_max=float(max(terms)),
                         early_input_sha256=old.early_input_sha256, later_input_sha256=old.later_input_sha256))
    report = dict(mode=mode, frames=len(frames), users=6, streams=early.shape[2], tones=3,
                  entries=early.size, projections=len(projections), early_mean=float(early_power.mean()),
                  raw_mean=float(raw_power.mean()), raw_median=float(np.median(raw_power)),
                  phase_mean=float(phase_power.mean()), phase_median=float(np.median(phase_power)),
                  raw_relative_db=float(10*np.log10(raw_power.mean()/early_power.mean())),
                  phase_relative_db=float(10*np.log10(phase_power.mean()/early_power.mean())),
                  projection_median=float(np.median(projections)), projection_q975=float(np.quantile(projections, .975)),
                  aggregation='Equal-weight pooling over held-out frames, users, retained RF streams and three tones; projection quantiles pool 12 individual scheduled magnitudes per frame before maximization. Ratios divide pooled means, not per-entry ratios.',
                  interpretation='Descriptive pilot-to-pilot relative error in quiet-slot whitened units, not an active-period noise or transmitter EVM estimate. Stored pairs cannot identify signal-dependent error versus underestimated pilot-period noise/distortion.')
    cells = []
    for a in range(early.shape[2]):
        for s in range(3):
            x, y, p = raw_power[:, :, a, s], phase_power[:, :, a, s], early_power[:, :, a, s]
            cells.append(dict(mode=mode, retained_stream_index=a, tone=(-13, 1, 14)[s], entries=x.size,
                              raw_mean=float(x.mean()), raw_median=float(np.median(x)),
                              phase_mean=float(y.mean()), phase_median=float(np.median(y)), early_mean=float(p.mean())))
    pd.DataFrame(rows).to_csv(OUT/f'hardware_scale_frames_{mode}.csv', index=False)
    pd.DataFrame(cells).to_csv(OUT/f'hardware_scale_stream_tone_{mode}.csv', index=False)
    (OUT/f'hardware_scale_{mode}.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


def bounds():
    import round2_refinement as ref
    from enclosures import priced, up, dn, PLO
    rows = []
    for block in range(64):
        h, _ = ref.normalized(ref.source('O1_60', block), 32, 10)
        H, _, I, J, lam, _ = ref.polish.table(h)
        g, G, rho, _, _ = ref.polish.endpoints(h, 0.)
        root, pen = ref.polish.cached_roots(g, G, rho, I, J, ref.polish.T)
        anchor = np.clip(1/max(lam, 1)-1/np.maximum(G, 1e-280), .05, .2)
        parent = priced(g, G, rho, I, J, ref.polish.T, root, pen, lam, anchor)
        # Reuse the exact production tangent arithmetic while disabling the competing box bound.
        tangent = priced(g, G, rho, I, J, ref.polish.T, np.full_like(root, np.inf), pen, lam, anchor)
        box = np.nextafter(root-dn(lam*dn(2*PLO)), np.inf)
        assert np.array_equal(parent, np.minimum(box, tangent))
        child = np.full_like(parent, np.inf)
        ref.subdivide(child, np.arange(child.size), g, G, rho, I, J, ref.polish.T, lam, 4)
        assert np.array_equal(H, np.ceil(np.minimum(parent, child)*ref.polish.Q).astype('int64'))
        rows.append(dict(block=block, entries=parent.size, tangent_strict=int((tangent < box).sum()),
                         box_strict=int((box < tangent).sum()), ties=int((box == tangent).sum()),
                         child_below_tangent=int((child < tangent).sum()), min_box_minus_tangent=float((box-tangent).min()),
                         min_child_minus_tangent=float((child-tangent).min()), input_sha256=ref.polish.digest(h)))
    data = pd.DataFrame(rows)
    data.to_csv(OUT/'o1_binding_bounds.csv', index=False)
    print(data.drop(columns=['block', 'input_sha256']).agg(['sum', 'min']).to_string(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=['HUB', 'LO', 'bounds'])
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    with threadpool_limits(1):
        bounds() if args.task == 'bounds' else hardware(args.task)
