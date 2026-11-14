"""Timing-only budget selection and a separate paired deterministic/learned rerun."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
for folder in ('Gate_2', 'Gate_2B', 'Gate_3'):
    sys.path.insert(0, str(ROOT / folder))
from grid import source
from solver import normalized
from verify import replay
import evaluate
import campaign
from reviewer_polish import solve
from round2_summary import paired

OUT = Path(__file__).resolve().parent / 'round2_data'
OUT.mkdir(exist_ok=True)
FAMILIES = ('A', 'B', 'C', 'UMa')


def warm(pred):
    for k in (32, 64):
        h, _ = normalized(source('A', 0), k, 10)
        for method in ('time', 'hybrid'):
            r, _, _ = solve(h, extra_iterations=12) if method == 'time' else campaign.solve(h, 'hybrid', pred)
            replay(h, r)


def tune(pred):
    path = OUT/'time_budget.json'
    if path.exists():
        print('Using the saved timing-only budget selection.', flush=True); return
    pilot = [(f, i) for f in FAMILIES for i in sorted(range(128), key=lambda i: hashlib.sha256(f'round2-time|{f}|{i}'.encode()).digest())[:4]]
    rows, chosen = [], {}
    for k in (32, 64):
        cache = {}
        def measure(extra):
            part = []
            for index, (family, block) in enumerate(pilot):
                h, _ = normalized(source(family, block), k, 10)
                for rep in range(3):
                    order = ['time', 'hybrid'] if (index+rep) % 2 == 0 else ['hybrid', 'time']
                    for method in order:
                        r, _, t = solve(h, extra_iterations=extra) if method == 'time' else campaign.solve(h, 'hybrid', pred)
                        replay(h, r)
                        part.append(dict(k=k, family=family, block=block, rep=rep, extra_iterations=extra,
                                         method=method, ms=t['total_ns']/1e6))
            rows.extend(part)
            d = pd.DataFrame(part).groupby(['family', 'block', 'method']).ms.median().groupby('method').median()
            cache[extra] = (float(d['time']), float(d.hybrid))
            pd.DataFrame(rows).to_csv(OUT/'time_budget_pilot.csv', index=False)
            print('Timing pilot', k, 'extra', extra, 'det/hybrid medians', *cache[extra], flush=True)
            return cache[extra]
        extra = 24 if k == 32 else 36
        for attempt in range(5):
            det, neural = measure(extra)
            if 1.03 <= det/neural <= 1.16:
                break
            base = 7 if k == 32 else 6
            proposed = max(3, int(np.ceil((base+extra)*(1.09*neural/det)))-base)
            extra = proposed if proposed not in cache else proposed+2
        eligible = [(e, d, n) for e, (d, n) in cache.items() if d >= n]
        assert eligible, ('No deterministic budget reaches the learned median', k, cache)
        extra, det, neural = min(eligible, key=lambda row: abs(row[1]/row[2]-1.09))
        chosen[str(k)] = dict(extra_iterations=extra, total_iterations=extra+(7 if k == 32 else 6),
                              pilot_deterministic_ms=det, pilot_learned_ms=neural, pilot_ratio=det/neural)
    path.write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(), target='Approximately 1.09 times contemporaneous learned median; timing-only selection',
                                    pilot_blocks=pilot, repeats=3, outcome_selection=False, budgets=chosen), indent=2))


def run(pred):
    budget = json.loads((OUT/'time_budget.json').read_text())['budgets']
    for family in FAMILIES:
        for block in range(128):
            path = OUT/f'time_control_{family}_{block:03d}.csv'
            if path.exists():
                old = pd.read_csv(path)
                assert len(old) == 12 and not old.isna().any().any()
                assert all((old.query('k == @k and method == "time"').iterations == budget[str(k)]['total_iterations']).all() for k in (32, 64))
                continue
            rows = []
            for k in (32, 64):
                h, _ = normalized(source(family, block), k, 10)
                extra = budget[str(k)]['extra_iterations']
                for rep in range(3):
                    order = ['time', 'hybrid'] if (block+rep+(k == 64)) % 2 == 0 else ['hybrid', 'time']
                    for method in order:
                        r, _, t = solve(h, extra_iterations=extra) if method == 'time' else campaign.solve(h, 'hybrid', pred)
                        replay(h, r)
                        norm = int(r['den'])*(k/2)*np.log(2)
                        rows.append(dict(family=family, block=block, k=k, rep=rep, method=method, G=r['G'],
                                         L=int(r['L'])/norm, U=int(r['U'])/norm, ms=t['total_ns']/1e6,
                                         iterations=r['branch_count'], input_sha256=r['raw_sha'],
                                         receipt_sha256=hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()))
            pd.DataFrame(rows).to_csv(path, index=False)
            if block % 8 == 7: print('Time-matched control', family, block+1, '/128', flush=True)
    summarize()


def summarize():
    files = sorted(OUT.glob('time_control_[ABCU]*_*.csv'))
    assert len(files) == 512, len(files)
    d = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
    assert len(d) == 6144
    d.to_csv(OUT/'time_control_calls.csv', index=False)
    blocks = d.groupby(['family', 'block', 'k', 'method'], as_index=False).agg(G=('G', 'max'), L=('L', 'min'), U=('U', 'min'), ms=('ms', 'median'), iterations=('iterations', 'first'))
    blocks['ok'] = (blocks.G <= .15) & (blocks.ms <= blocks.k.map({32: 250, 64: 1000}))
    blocks.to_csv(OUT/'time_control_blocks.csv', index=False)
    summary = blocks.groupby(['k', 'method']).agg(n=('ok', 'size'), passes=('ok', 'sum'), median_G=('G', 'median'), median_ms=('ms', 'median'), median_L=('L', 'median'), median_U=('U', 'median'), iterations=('iterations', 'first')).reset_index()
    summary.to_csv(OUT/'time_control_summary.csv', index=False)
    tests = paired(blocks, 'time', 'hybrid', 'time-budget rerun')
    tests.to_csv(OUT/'time_control_paired_tests.csv', index=False)
    prior = pd.read_csv(Path(__file__).resolve().parent/'reviewer_data/compute_blocks.csv').query('method == "hybrid"')
    checked = blocks.query('method == "hybrid"').merge(prior, on=['family', 'block', 'k', 'method'], suffixes=('_new', '_old'))
    assert len(checked) == 1024 and (checked.ok_new == checked.ok_old).all()
    drift = float(abs(checked.G_new-checked.G_old).max())
    # GPU reruns need not be bit-identical; every returned certificate is replayed.
    assert drift < 5e-7, ('Change exceeds the reported gap precision', drift)
    (OUT/'time_control_validation.json').write_text(json.dumps(dict(
        compared_learned_blocks=len(checked), unchanged_pass_fail=True,
        maximum_absolute_gap_difference=drift, all_6144_certificates_replayed=True), indent=2))
    print(summary.to_string(index=False), flush=True)
    print(tests.to_string(index=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=['tune', 'run', 'summarize'])
    args = parser.parse_args()
    if args.task == 'summarize':
        summarize()
    else:
        cfg = json.loads((ROOT/'Gate_2B/results/freeze.json').read_text())
        evaluate.res = OUT
        with threadpool_limits(1), evaluate.worker(cfg['seed']) as pred:
            warm(pred)
            tune(pred) if args.task == 'tune' else run(pred)
