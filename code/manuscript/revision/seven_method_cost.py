"""Account for the seven archived solver calls used in the retrospective ceiling."""
import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


METHODS = ("det", "hybrid", "standalone", "legacy", "sequential", "equal_match", "cold")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def key(row):
    return row["family"], int(row["block"]), int(row["k"]), row["method"]


def run(experiments, rates_path, output):
    calls = defaultdict(list)
    endpoints = defaultdict(list)
    for row in read(experiments / "times.csv"):
        assert int(row["db"]) == 10
        k = key(row)
        calls[k].append(int(row["total_ns"])/1e6)
        endpoints[k].append(float(row["Ubit"]))
    for path in sorted((experiments / "controls_native").glob("*.csv")):
        for row in read(path):
            if int(row["db"]) == 10 and int(row["k"]) in (32, 64):
                k = key(row)
                calls[k].append(float(row["ms"]))
                endpoints[k].append(float(row["U"]))
    cohorts = defaultdict(dict)
    all_calls = defaultdict(float)
    outcomes = {}
    for row in read(rates_path):
        k = key(row)
        if k[2] not in (32, 64):
            continue
        assert len(calls[k]) == (3 if k[3] in METHODS[:4] else 1)
        assert abs(min(endpoints[k]) - float(row["U"])) < 1e-11
        cohorts[k[:3]][k[3]] = statistics.median(calls[k])
        all_calls[k[:3]] += sum(calls[k])
        if k[3] == "cold":
            outcomes[k[:3]] = float(row["U_best"]) - float(row["L"]) <= 0.15
    assert len(cohorts) == len(outcomes) == 1024
    fields = ["family", "block", "users", *METHODS, "seven_call_sum_ms", "all_15_calls_ms", "certified"]
    with output.open("w", encoding="ascii", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for k, times in sorted(cohorts.items()):
            assert set(times) == set(METHODS)
            writer.writerow(dict(family=k[0], block=k[1], users=k[2], **times,
                                 seven_call_sum_ms=sum(times.values()), all_15_calls_ms=all_calls[k],
                                 certified=int(outcomes[k])))
    for users, expected in [(32, 395), (64, 426)]:
        keys = [k for k in cohorts if k[2] == users]
        assert len(keys) == 512 and sum(outcomes[k] for k in keys) == expected
        print(users, "median seven-call sum and all 15 call times (ms):",
              statistics.median(sum(cohorts[k].values()) for k in keys),
              statistics.median(all_calls[k] for k in keys))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiments",type=Path)
    parser.add_argument("rates",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    run(args.experiments,args.rates,args.output)
