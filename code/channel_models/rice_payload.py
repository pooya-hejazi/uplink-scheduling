"""Six-user QPSK replay of the two Rice distributed chain-A recordings.

Use the locally obtained HDF5 and matching transmitter sidecars. Only scalar
scores, counts and digests are written. No packet framing is assumed.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import h5py
import numpy as np


CAPTURES = {
    "HUB": "aec556198de39208757fddc294af77d4f701d7a24b9f1feb3f1fdc09d36bc0d2",
    "LO": "e5fabc009dce96e527b6919ce744f0b41408f337e0d5334b8dadfa0f13699844",
}
CALIBRATION_END = 512
BIT_ERRORS = np.array([0, 1, 1, 2])


def labels(z):
    return 2 * (z.real > 0).astype(np.uint8) + (z.imag > 0)


def complex_pairs(x):
    return x[..., ::2].astype(np.float64) + 1j * x[..., 1::2].astype(np.float64)


def fft(x):
    return np.fft.fftshift(np.fft.fft(x, axis=-1), axes=-1)


def references(attrs, directory):
    data_bins = np.asarray(attrs["OFDM_DATA_SC"], dtype=int)
    pilot_bins = np.asarray(attrs["OFDM_PILOT_SC"], dtype=int)
    pilot_values = complex_pairs(np.asarray(attrs["OFDM_PILOT_SC_VALS"]))
    lts = complex_pairs(np.asarray(attrs["OFDM_PILOT_F"]))
    assert np.allclose(fft(complex_pairs(np.asarray(attrs["OFDM_PILOT"]))), lts, atol=1e-6)
    occupied = np.r_[data_bins, pilot_bins]
    assert len(data_bins) == 48 and len(pilot_bins) == 4 and len(np.unique(occupied)) == 52
    assert np.all(np.abs(lts[occupied]) > 0.99)
    truth, symbols, checks = [], [], []
    for user, entry in enumerate(attrs["TX_FD_DATA_FILENAMES"]):
        name = entry.decode() if isinstance(entry, bytes) else str(entry)
        assert name == f"ul_data_f_QPSK_52_64_10_1_1_A_{user}.bin"
        def read(kind):
            return (directory / name.replace("ul_data_f_", f"ul_data_{kind}_")).read_bytes()
        bit_file, fd_file, td_file = (read(k) for k in "bft")
        # Only the first 48 entries in each 52-byte symbol record label data bins.
        tx = np.frombuffer(bit_file, "u1").reshape(10, 52)[:, :48]
        fd = np.frombuffer(fd_file, "<c8").reshape(10, 64)
        td = complex_pairs(np.frombuffer(td_file, "<i2"))
        assert td.size == 1120 and not np.any(td[:160]) and not np.any(td[960:])
        spectrum = fft(td[160:960].reshape(10, 80)[:, 16:])
        gain = (np.vdot(fd, spectrum) / np.vdot(fd, fd)).real
        residual = np.linalg.norm(spectrum - gain * fd) / np.linalg.norm(spectrum)
        wrong_order = np.linalg.norm(np.fft.ifftshift(spectrum, axes=-1) - gain * fd) / np.linalg.norm(spectrum)
        assert gain > 0 and residual < 0.001 and wrong_order > 0.5
        assert np.array_equal(labels(fd[:, data_bins]), tx) and set(tx.ravel()) == {0, 1, 2, 3}
        assert np.allclose(abs(fd[:, data_bins]), 1) and np.allclose(fd[:, pilot_bins], pilot_values)
        truth.append(tx)
        symbols.append(fd[:, data_bins])
        checks.append(dict(user=user, matched_symbols=tx.size, tx_fft_relative_error=float(residual),
                           unshifted_fft_relative_error=float(wrong_order),
                           sha256={k: hashlib.sha256(v).hexdigest() for k, v in
                                   zip(("labels", "frequency", "time"), (bit_file, fd_file, td_file))}))
    assert len(truth) == 6
    return occupied, lts[occupied], pilot_values, np.array(truth), np.array(symbols), checks


def equalize(h, y, pilot_values):
    # Each tone has one 64-by-6 pilot channel; its weights stay fixed across all ten data symbols.
    left, singular, right = np.linalg.svd(h, full_matrices=False)
    if np.any(singular[:, -1] <= 1e-6 * singular[:, 0]):
        return None
    weights = (right.conj().swapaxes(-1, -2) / singular[:, None, :]) @ left.conj().swapaxes(-1, -2)
    z = (weights @ y).transpose(1, 2, 0)
    common_pilot = (z[:, :, 48:] * pilot_values.conj()).mean(axis=-1)
    corrected = z[:, :, :48] * np.exp(-1j * np.angle(common_pilot))[:, :, None]
    return corrected, np.abs(common_pilot)


def receiver(pilot, payload, occupied, lts, pilot_values):
    # Both pilot and payload FFTs start four samples before the nominal CP end.
    start = 160 + 16 - 4
    early = complex_pairs(pilot[..., 2*start:2*(start+64)])
    guard = complex_pairs(pilot[..., :128])
    signal = np.mean(abs(early)**2, axis=(1, 2))
    background = np.mean(abs(guard)**2, axis=(1, 2))
    if np.any(signal < 2 * np.maximum(background, 1)):
        return "weak_or_missing_user_pilot", None
    if not np.any(payload):
        return "missing_uplink", None
    h = (fft(early)[..., occupied] / lts).transpose(2, 1, 0)
    y = complex_pairs(payload)
    windows = y[:, start + 80*np.arange(10)[:, None] + np.arange(64)]
    estimate = equalize(h, fft(windows)[..., occupied].transpose(2, 0, 1), pilot_values)
    return ("rank_deficient", None) if estimate is None else ("scored", estimate)


def check_receiver(symbols, truth, pilot_values):
    rng = np.random.default_rng(708)
    h = rng.normal(size=(52, 8, 6)) + 1j*rng.normal(size=(52, 8, 6))
    pilots = np.broadcast_to(pilot_values, (6, 10, 4))
    tx = np.concatenate((symbols, pilots), axis=2)
    phases = np.exp(1j*rng.uniform(-np.pi, np.pi, size=(6, 10, 1)))
    y = h @ (tx * phases).transpose(2, 0, 1)
    decoded, gains = equalize(h, y, pilot_values)
    assert np.allclose(gains, 1) and np.allclose(decoded, symbols) and np.array_equal(labels(decoded), truth)
    assert np.sum(BIT_ERRORS[np.bitwise_xor(labels(decoded), truth)]) == 0
    assert np.array_equal(BIT_ERRORS[np.bitwise_xor([0, 0, 0, 0], [0, 1, 2, 3])], [0, 1, 1, 2])


def analyze(mode, group, directory, output, digest):
    assert digest == CAPTURES[mode]
    attrs = group.attrs
    def scalar(name):
        return int(np.asarray(attrs[name]).item())
    assert [scalar(k) for k in ("FFT_SIZE", "CP_LEN", "PREFIX_LEN", "POSTFIX_LEN", "UL_SLOTS", "UL_DATA_FRAME_NUM")] == [64, 16, 160, 160, 1, 1]
    p, d = group["Pilot_Samples"], group["UplinkData"]
    assert p.shape == (2001, 1, 6, 64, 2240) and d.shape == (2001, 1, 1, 64, 2240)
    schedules = np.asarray(attrs["CL_FRAME_SCHED"]).astype(str)
    assert len(schedules) == 6 and all(s.count("U") == 1 and s.index("U") == 47 for s in schedules)
    occupied, lts, pilot_values, truth, symbols, checks = references(attrs, directory)
    check_receiver(symbols, truth, pilot_values)
    output.mkdir(parents=True, exist_ok=True)
    status_counts = {"calibration": Counter(), "test": Counter()}
    gains = []
    totals = np.zeros((6, 6))
    columns = ("mode", "frame", "user", "status", "symbols", "bits", "symbol_errors", "bit_errors",
               "squared_error", "reference_energy", "shifted_reference_bit_errors")
    scalar_path = output / f"payload_frames_{mode}.csv"
    staging = scalar_path.with_suffix(".partial")
    with staging.open("w", encoding="ascii", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        for frame in range(p.shape[0]):
            if frame == CALIBRATION_END:
                if not gains:
                    raise ValueError("No usable calibration pilots")
                gain = np.median(np.concatenate(gains, axis=1), axis=1)
                assert np.all(np.isfinite(gain)) and np.all(gain > 0)
            calibration = frame < CALIBRATION_END
            status, result = receiver(p[frame, 0], d[frame, 0, 0], occupied, lts, pilot_values)
            status_counts["calibration" if calibration else "test"][status] += 1
            if calibration:
                if result is not None:
                    gains.append(result[1])
                continue
            if result is None:
                for user in range(6):
                    writer.writerow([mode, frame, user, status, 0, 0, "", "", "", "", ""])
                continue
            estimated = result[0] / gain[:, None, None]
            hard = labels(estimated)
            delta = hard ^ truth
            axes = (1, 2)
            errors = np.count_nonzero(delta, axis=axes)
            bits = BIT_ERRORS[delta].sum(axis=axes)
            sse = np.square(np.abs(estimated-symbols)).sum(axis=axes)
            energy = np.square(np.abs(symbols.astype(np.complex128))).sum(axis=axes)
            shifted = BIT_ERRORS[hard ^ np.roll(truth, 1, axis=1)].sum(axis=axes)
            assert np.all(np.isfinite(sse)) and np.all(bits >= errors) and np.all(bits <= 2*errors)
            for user in range(6):
                writer.writerow([mode, frame, user, status, 480, 960, errors[user], bits[user],
                                 sse[user], energy[user], shifted[user]])
            totals += np.stack((np.full(6, 480), errors, bits, sse, energy, shifted), axis=1)
    scored = status_counts["test"]["scored"]
    assert scored > 0 and sum(status_counts["test"].values()) == 1489
    assert sum(status_counts["calibration"].values()) == CALIBRATION_END
    summary = []
    for user, (n, se, be, sse, energy, shifted) in enumerate(totals):
        assert n == scored*480
        summary.append(dict(mode=mode, user=user, frames_planned=1489, frames_scored=scored,
                            frames_abstained=1489-scored, symbols=int(n), symbol_errors=int(se),
                            bits=int(2*n), bit_errors=int(be), evm_rms_percent=100*np.sqrt(sse/energy),
                            ser=se/n, ber=be/(2*n), shifted_reference_ber=shifted/(2*n)))
    staging.replace(scalar_path)
    with (output / f"payload_summary_{mode}.csv").open("w", encoding="ascii", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=summary[0])
        writer.writeheader()
        writer.writerows(summary)
    receipt = dict(mode=mode, capture_sha256=digest, calibration_inclusive=[0, 511], test_inclusive=[512, 2000],
                   frame_counts=status_counts, calibration_amplitude_gain=gain.tolist(), reference_controls=checks,
                   zero_noise_control="passed", frequency_order="fftshift", receiver_streams=64,
                   data_bins=occupied[:48].tolist(), control_pilot_bins=occupied[48:].tolist(),
                   independent_acquisitions=1, frame_csv_sha256=hashlib.sha256(scalar_path.read_bytes()).hexdigest())
    (output / f"payload_controls_{mode}.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    print(mode, json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=CAPTURES)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--references", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with args.capture.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    with h5py.File(args.capture, "r", rdcc_nbytes=16*2**20) as recording:
        analyze(args.mode, recording["Data"], args.references, args.output, digest)
