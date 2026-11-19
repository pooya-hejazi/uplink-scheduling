"""Repeat the LO user-5 timing search on the four original calibration frames."""
import argparse
import csv
import hashlib
from pathlib import Path

import h5py
import numpy as np

from rice_payload import CAPTURES, complex_pairs


FRAMES = [64, 72, 80, 88]


def evaluate(pilots, output):
    samples = complex_pairs(np.stack([pilots[f, 0, 5] for f in FRAMES])) / 32768
    occupied, guard = np.r_[1:27, 38:64], np.r_[0, 27:38]
    scores = {}
    for offset in range(-128, 129, 2):
        starts = 176 + offset + 80 * np.arange(1, 9)
        power = abs(np.fft.fft(samples[..., starts[:, None] + np.arange(64)], axis=-1)) ** 2
        signal_power = power[..., occupied].mean(axis=(-1, -2))
        guard_power = power[..., guard].mean(axis=(-1, -2))
        scores[offset] = float(np.median(np.log((signal_power + 1e-20) / (guard_power + 1e-20))))
    selected = {}
    for limit in (64, 96, 128):
        selected[limit] = min((i for i in scores if abs(i) <= limit), key=lambda i: (-scores[i], abs(i), i))
    assert selected == {64: 64, 96: -94, 128: -94}
    with output.open("w", encoding="ascii", newline="") as stream:
        rows = csv.writer(stream)
        rows.writerow(["offset_samples", "median_log_occupied_to_null_energy", "selected_64", "selected_96", "selected_128"])
        for offset, score in scores.items():
            rows.writerow([offset, score, *[int(offset == winner) for winner in selected.values()]])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.capture.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != CAPTURES["LO"]:
            parser.error("Expected the original LO distributed chain-A HDF5 file.")
    with h5py.File(args.capture, "r") as recording:
        evaluate(recording["Data/Pilot_Samples"], args.output)
