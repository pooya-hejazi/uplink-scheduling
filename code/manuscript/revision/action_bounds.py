"""Enclose the gap between each reported floor and its actual fixed-filter rate."""
import base64
import csv
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / name) for name in ("Gate_3", "Gate_2B", "Gate_2")]
from grid import source
from inputs import analytic
from polish import solve
from solver import PT, normalized
from verify import replay


def squared_inner(left, right):
    real = imag = 0
    for (a, b), (c, d) in zip(left, right):
        real += a * c + b * d
        imag += a * d - b * c
    return real * real + imag * imag


def components(vector):
    return [(Fraction(float(x.real)), Fraction(float(x.imag))) for x in vector]


def rate_margin(h, rec):
    dtype, shape, payload = rec["receiver"]
    filters = np.frombuffer(base64.b64decode(payload), dtype=dtype).reshape(shape)
    powers = [Fraction(int(tick), PT) for tick in rec["power"]]
    product = Fraction(1)
    for tone, pair in enumerate(rec["pair"]):
        channels = [components(h[i, :, tone]) for i in pair]
        for a in (0, 1):
            v = components(filters[tone, a])
            noise = sum(x*x + y*y for x, y in v)
            assert noise > 0
            signal = powers[pair[a]] * squared_inner(v, channels[a])
            interference = powers[pair[1-a]] * squared_inner(v, channels[1-a])
            product *= 1 + signal / (noise + interference)
    floor = Fraction(int(rec["L"]), int(rec["den"]))
    with localcontext() as ctx:
        ctx.prec = 75
        ctx.rounding = ROUND_FLOOR
        log_lo = (Decimal(product.numerator) / Decimal(product.denominator)).ln().next_minus()
        floor_lo = Decimal(floor.numerator) / Decimal(floor.denominator)
        norm_lo = Decimal(len(filters)) * Decimal(2).ln().next_minus()
        ctx.rounding = ROUND_CEILING
        log_hi = (Decimal(product.numerator) / Decimal(product.denominator)).ln().next_plus()
        floor_hi = Decimal(floor.numerator) / Decimal(floor.denominator)
        norm_hi = Decimal(len(filters)) * Decimal(2).ln().next_plus()
        assert log_lo >= floor_hi
        hi = (log_hi - floor_lo) / norm_lo
        ctx.rounding = ROUND_FLOOR
        lo = (log_lo - floor_hi) / norm_hi
    return lo, hi


def main():
    records = {}
    sources = (HERE / "reviewer_data/gap_decomposition.csv", HERE / "round2_data/o1_small_references.csv")
    for path in sources:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if int(row["k"]) < 16:
                    records.setdefault((row["family"], int(row["block"])), []).append(row)
    result = []
    for (family, block), group in sorted(records.items()):
        raw = source(family, block) if family == "O1_60" else analytic(family, block)
        for row in group:
            k = int(row["k"])
            if family == "O1_60":
                h, _ = normalized(raw, k, 10)
            else:
                scale = np.sqrt(10 / (.1 * np.median(np.mean(abs(raw.astype(complex))**2, axis=1))))
                tones = np.floor(np.arange(k // 2) * raw.shape[2] / (k // 2)).astype(int)
                h = np.ascontiguousarray(raw[:k, :, tones].astype(complex) * scale)
            rec, _, _ = solve(h)
            replay(h, rec)
            assert row.get("input_sha256", rec["raw_sha"]) == rec["raw_sha"]
            for key in ("L", "U"):
                reported = int(rec[key]) / int(rec["den"]) / ((k // 2) * np.log(2))
                assert abs(reported - float(row[key])) < 2e-12, (family, block, k, key)
            lo, hi = rate_margin(h, rec)
            result.append(dict(family=family, block=block, k=k, channel_sha256=rec["raw_sha"],
                               lower_numerator=rec["L"], denominator=rec["den"],
                               rate_minus_floor_lo=lo, rate_minus_floor_hi=hi))
    assert len(result) == len({(r["family"], r["block"], r["k"]) for r in result}) == 2176
    dest = HERE / "action_data/fixed_filter_checks.csv"
    dest.parent.mkdir(exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=result[0])
        writer.writeheader()
        writer.writerows(result)
    with (ROOT / "Gate_3/results/exact_two.csv").open(encoding="utf-8-sig", newline="") as stream:
        roots = list(csv.DictReader(stream))
    assert len(roots) == len({(r["family"], r["block"]) for r in roots}) == 512
    for row in roots:
        width = float(row["hi_nats"]) - float(row["lo_nats"])
        normalized_width = np.nextafter(width / np.nextafter(np.log(2.), -np.inf), np.inf)
        assert normalized_width == float(row["G_oracle"]) and int(row["resolved"]) == 1
    with dest.with_name("two_user_root_widths.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=roots[0])
        writer.writeheader()
        writer.writerows(roots)
    print(f"{len(result)} verified fixed-filter rates, maximum rate minus floor "
          f"{max(r['rate_minus_floor_hi'] for r in result):.8E} bit/s/Hz.")


if __name__ == "__main__":
    main()
