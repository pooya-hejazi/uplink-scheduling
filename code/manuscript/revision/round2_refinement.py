"""O1 enclosure diagnostics with frozen actions/prices and validated small references."""
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
for folder in ('Gate_2', 'Gate_2B', 'Gate_3'):
    sys.path.insert(0, str(ROOT / folder))
import reviewer_polish as polish
import verify
from grid import source
from solver import normalized
from enclosures import mix, up, dn, PLO, PHI

OUT = Path(__file__).resolve().parent / 'round2_data'
OUT.mkdir(exist_ok=True)


@njit(cache=True, fastmath=False)
def subdivide(H, chosen, g, G, rho, I, J, T, lam, steps):
    S = H.shape[1]
    grid = np.linspace(PLO, PHI, steps+1)
    for index in chosen:
        e, s = index//S, index % S
        value = -np.inf
        for i in range(steps):
            for j in range(steps):
                a, A, b, B = grid[i], grid[i+1], grid[j], grid[j+1]
                value = max(value, up(mix(g, G, I[e], J[e], s, rho[e, s], a, A, b, B, T)-dn(lam*dn(a+b))))
        H[e, s] = min(H[e, s], value)


def frozen_receipt(old, H, I, J, chosen):
    r = copy.deepcopy(old)
    k, S = r['k'], r['k']//2
    beta = np.asarray(r['beta'])
    w = (H-beta).max(1)
    m, y, z, value = polish.match(k, I, J, w)
    e = polish.edgeid(k, *m.T)
    cols, ay, ab = polish.assignment(H[e])
    A, R = int(H[e, cols].sum()), int(value)+int(beta.sum())
    r.update(witness='odd-set4', pairs=m.tolist(), y4=y.tolist(), z4=[(list(B), int(v)) for B, v in z],
             cols=cols.tolist(), ay=ay.tolist(), ab=ab.tolist(), A_tick=A, dc_tick=R-A,
             H_sha=polish.digest(H), leaves=chosen.tolist(), R_tick=R,
             Sd_tick=int(np.ptp(H-beta, axis=1).max())*S)
    pa, p = np.asarray(r['pair']), np.asarray(r['power'])
    pool = [np.asarray(r['pool_pair']), pa, m[np.argsort(cols)]]
    best = max(pool, key=lambda a: int(H[polish.edgeid(k, *a.T), np.arange(S)].sum()))
    r['pool_pair'] = best.tolist()
    r['A_pool_tick'] = int(H[polish.edgeid(k, *best.T), np.arange(S)].sum())
    ids = polish.edgeid(k, *pa.T)
    wt, hs, bs = int(w[ids].sum()), int(H[ids, np.arange(S)].sum()), int(beta.sum())
    P, lam, Q, PT = k*polish.PT//10, r['lambda_price'], polish.Q, polish.PT
    U, L = lam*P*Q+R*PT, int(r['L'])
    terms = [(R-bs-wt)*PT, (wt-hs+bs)*PT, lam*(P-int(p.sum()))*Q,
             (hs-sum(r['L_pair']))*PT+lam*int(p.sum())*Q]
    assert min(terms) >= 0 and sum(terms) == U-L
    r.update(U=str(U), terms=list(map(str, terms)), G=float(np.nextafter((U-L)/int(r['den'])/(S*np.log(2)), np.inf)))
    assert r['G'] <= old['G']+1e-10
    return r


def refinement():
    budgets, depths = [], []
    for block in range(64):
        a, b = OUT/f'o1_budget_{block:03d}.csv', OUT/f'o1_depth_{block:03d}.csv'
        if a.exists() and b.exists():
            budgets.extend(pd.read_csv(a).to_dict('records')); depths.extend(pd.read_csv(b).to_dict('records')); continue
        h, _ = normalized(source('O1_60', block), 32, 10)
        rec, _, _ = polish.solve(h)
        verify.replay(h, rec)
        H0, nom, I, J, lam, initial = polish.table(h)
        g, G, rho, _, _ = polish.endpoints(h, 0.)
        root, pen = polish.cached_roots(g, G, rho, I, J, polish.T)
        anchor = np.clip(1/max(lam, 1)-1/np.maximum(G, 1e-280), .05, .2)
        parent = polish.priced(g, G, rho, I, J, polish.T, root, pen, lam, anchor)
        parent_ticks = np.ceil(parent*polish.Q).astype('int64')
        scheduled = polish.edgeid(32, *np.asarray(rec['pair']).T)*16+np.arange(16)
        base = parent.copy()
        subdivide(base, initial, g, G, rho, I, J, polish.T, lam, 4)
        assert np.array_equal(np.ceil(base*polish.Q).astype('int64'), H0)
        rows = []
        for budget in (32, 128, 512, 7936):
            H, _, _, _, _, selected = polish.table(h, refinement_budget=budget)
            assert np.all(H <= parent_ticks)
            rows.append(dict(block=block, budget=budget, changed_from_parent=int((H != parent_ticks).sum()),
                             changed_from_top32=int((H != H0).sum()), scheduled_entries_in_shortlist=int(np.isin(scheduled, selected).sum()),
                             scheduled_entries_changed=int((H.ravel()[scheduled] != parent_ticks.ravel()[scheduled]).sum()),
                             maximum_tick_reduction=int((parent_ticks-H).max()), H_sha256=polish.digest(H)))
        pd.DataFrame(rows).to_csv(a, index=False); budgets.extend(rows)
        rows = []
        combined = np.union1d(initial, scheduled)
        saved_leaves = verify.leaves
        for steps in (4, 8, 16):
            H = base.copy()
            subdivide(H, scheduled, g, G, rho, I, J, polish.T, lam, steps)
            H = np.ceil(H*polish.Q).astype('int64')
            result = frozen_receipt(rec, H, I, J, combined)
            def replay_leaves(table, selected, gg, GG, rr, ii, jj, tt, ll):
                assert np.array_equal(selected, combined)
                saved_leaves(table, initial, gg, GG, rr, ii, jj, tt, ll)
                subdivide(table, scheduled, gg, GG, rr, ii, jj, tt, ll, steps)
            try:
                verify.leaves = replay_leaves
                verify.replay(h, result)
            finally:
                verify.leaves = saved_leaves
            scale = int(result['den'])*16*np.log(2)
            rows.append(dict(block=block, children=steps*steps, frozen_action=True, frozen_prices=True,
                             G=result['G'], T4=int(result['terms'][3])/scale, L=int(result['L'])/scale, U=int(result['U'])/scale,
                             baseline_G=rec['G'], changed_from_top32=int((H != H0).sum()),
                             scheduled_entries_changed=int((H.ravel()[scheduled] != H0.ravel()[scheduled]).sum()),
                             original_shortlist_contains=int(np.isin(scheduled, initial).sum()), H_sha256=polish.digest(H)))
        pd.DataFrame(rows).to_csv(b, index=False); depths.extend(rows)
        if block % 8 == 7: print('O1 budget/depth', block+1, '/64', flush=True)
    pd.DataFrame(budgets).to_csv(OUT/'o1_budget_entries.csv', index=False)
    d = pd.DataFrame(depths); d.to_csv(OUT/'o1_depth.csv', index=False)
    d.groupby('children').agg(n=('block', 'size'), median_G=('G', 'median'), median_T4=('T4', 'median'),
                               median_changed=('changed_from_top32', 'median')).reset_index().to_csv(OUT/'o1_depth_summary.csv', index=False)
    print(d.groupby('children')[['G', 'T4', 'changed_from_top32']].median(), flush=True)


def small(limit, tiles):
    from exact_two import bound as exact_two
    from oracle import schedules
    from round2_oracle import single, self_check
    self_check()
    mats = schedules(4)
    rows = []
    for block in range(tiles):
        path = OUT/f'o1_small_{block:03d}.csv'
        if path.exists():
            old = pd.read_csv(path)
            if 'reference_version' in old and (old.resolved.all() or old.split_budget.max() >= limit):
                rows.extend(old.to_dict('records')); continue
        raw = source('O1_60', block)
        records = []
        for k in (2, 4):
            h, _ = normalized(raw, k, 10)
            rec, _, _ = polish.solve(h); verify.replay(h, rec)
            norm = k/2*np.log(2)
            if k == 2:
                lo, hi = exact_two(h[:, :, 0]); count = 0; kind = 'exact polynomial-root enclosure'
            else:
                ref = single(h, mats, limit=limit)
                lo, hi, count = ref['lo_nats'], ref['hi_nats'], ref['split_boxes']; kind = 'validated continuous box reference'
            L, U = int(rec['L'])/int(rec['den'])/norm, int(rec['U'])/int(rec['den'])/norm
            lo, hi = max(L, lo/norm), min(U, hi/norm)
            assert L <= lo <= hi+1e-10 <= U+1e-10
            records.append(dict(block=block, k=k, family='O1_60', reference=kind, input_sha256=polish.digest(h),
                                reference_version='tight-Gram Taylor / full-power slice v1',
                                L=L, U=U, V_lo=lo, V_hi=hi, reference_width=max(0., hi-lo), resolved=int(hi-lo <= 1e-6),
                                split_boxes=count, split_budget=limit, slack_lo=max(0., U-hi), slack_hi=U-lo,
                                suboptimality_lo=max(0., lo-L), suboptimality_hi=hi-L))
        pd.DataFrame(records).to_csv(path, index=False); rows.extend(records)
        print('O1 continuous', block+1, '/', tiles, 'widths', [r['reference_width'] for r in records], flush=True)
    pd.DataFrame(rows).to_csv(OUT/'o1_small_references.csv', index=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('task', choices=['refinement', 'small'])
    p.add_argument('--limit', type=int, default=32768)
    p.add_argument('--tiles', type=int, default=64)
    args = p.parse_args()
    with threadpool_limits(1):
        refinement() if args.task == 'refinement' else small(args.limit, args.tiles)
