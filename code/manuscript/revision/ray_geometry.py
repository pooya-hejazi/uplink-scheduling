"""Describe archived 10-dB channel geometry and join the checked gap decomposition."""
import argparse
import csv
import json
import hashlib
from pathlib import Path

import numpy as np


def describe(raw, k, scale):
    tones = k // 2
    h = np.asarray(raw[:k, :, ::64 // tones], dtype=np.complex128).transpose(2, 0, 1)
    norms = np.linalg.norm(h, axis=2, keepdims=True)
    snr = 0.1 * (scale * norms[:, :, 0]) ** 2
    h = h / norms
    gram = h @ h.conj().transpose(0, 2, 1)
    i, j = np.triu_indices(k, 1)
    overlap = np.abs(gram[:, i, j]) ** 2
    # The nonzero spectra of the user and antenna Gram matrices coincide.
    spectrum = np.linalg.eigvalsh(h.conj().transpose(0, 2, 1) @ h).clip(min=0)
    prob = spectrum / spectrum.sum(axis=1, keepdims=True)
    rank = np.exp(-np.sum(prob * np.log(np.maximum(prob, np.finfo(float).tiny)), axis=1))
    assert np.allclose(np.diagonal(gram, axis1=1, axis2=2), 1)
    assert np.all((rank >= 1 - 1e-12) & (rank <= h.shape[2] + 1e-10))
    partner_snr = snr[:, None, :]
    sinr = snr[:, :, None] * (1 - np.abs(gram) ** 2 * partner_snr / (1 + partner_snr))
    pair_mask = ~np.eye(k, dtype=bool)
    rates = np.log2(1 + sinr[:, pair_mask].reshape(tones, k, k - 1))
    lo, hi = np.quantile(rates, [0.1, 0.9], axis=2)
    return overlap.mean(), rank.mean(), (hi - lo).mean()


def ray_metadata(folder, archive, scene):
    """Decode BS1 ray power, departure angles and LOS flags using the source v2 layout."""
    from scipy.io import loadmat
    spec = json.loads((archive.parent / 'Gate_2' / 'data' / f'{scene}_source.json').read_text())
    def read(kind):
        name = f'{scene}.1.{kind}.mat'
        path = folder / name
        with path.open('rb') as fp:
            assert hashlib.file_digest(fp, 'sha256').hexdigest() == spec['files'][name]
        matrix, = [v for key, v in loadmat(path).items() if not key.startswith('_')]
        return matrix.ravel()
    flags, cir, departure = read('LoS'), read('CIR'), read('DoD')
    user_ids = {u for tile in json.loads((archive / f'{scene}_tiles.json').read_text()) for u in tile['users']}
    selected = {}
    offset = 1
    for user in range(max(user_ids) + 1):
        count = int(departure[offset + 1])
        first = offset + 2
        if user in user_ids:
            count_used = min(25, count)
            take = slice(first, first + 4 * count_used)
            angles = departure[take].reshape(-1, 4)
            powers = cir[take].reshape(-1, 4)[:, 3].astype(float)
            weights = 10 ** ((powers - powers.max()) / 10)
            weights /= weights.sum()
            # BS element response uses the 3D direction; the first stored path is the LOS when flagged.
            phi, theta = np.deg2rad(angles[:, 1:3].astype(float)).T
            direction = np.array([np.sin(theta)*np.cos(phi), np.sin(theta)*np.sin(phi), np.cos(theta)])
            selected[user] = (count, flags[user + 1], weights.max(), weights[0] * flags[user + 1],
                              np.linalg.norm(direction @ weights))
        offset = first + count * 4
    assert len(selected) == len(user_ids) == 4096
    return selected


def main():
    revision = Path(__file__).resolve().parent
    archive = revision.parents[1] / 'Gate_3'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--o1', type=Path, required=True, help='Original O1_60 scene directory')
    parser.add_argument('--asu', type=Path, required=True, help='Original asu_campus1 scene directory')
    args = parser.parse_args()
    metadata = {f: ray_metadata(folder, archive, f)
                for f, folder in [('O1_60', args.o1), ('asu_campus1', args.asu)]}
    rows = []
    for kind, manifest in [('native', 'data_manifest.csv'), ('ray', 'ray_manifest.csv')]:
        with (archive / manifest).open() as fp:
            entries = list(csv.DictReader(fp))
        for entry in entries:
            family = entry.get('family') or entry['scene']
            block = int(entry['block'])
            path = archive / 'data' / f'pilot_{family}_{block:04d}.npz'
            with path.open('rb') as fp:
                assert hashlib.file_digest(fp, 'sha256').hexdigest() == entry['file_sha256']
            with np.load(path) as data:
                raw = data['h']
                if kind == 'ray':
                    rays = np.asarray([metadata[family][int(u)] for u in data['perm']])
                    assert np.array_equal(rays[:, 0], data['paths'])
            with (archive / 'results' / f'grid_{kind}' / f'{family}_{block:03d}.csv').open() as fp:
                for run in csv.DictReader(fp):
                    k = int(run['k'])
                    if k not in (32, 64) or float(run['db']) != 10:
                        continue
                    assert run['method'] == 'det' and run['family'] == family and int(run['block']) == block
                    overlap, rank, spread = describe(raw, k, float(run['scale']))
                    terms = [float(run[f'term{i}']) for i in range(1, 5)]
                    gap = float(run['G'])
                    assert np.isclose(sum(terms), gap, rtol=1e-10, atol=1e-12)
                    rows.append(dict(family=family, block=block, k=k, mean_pair_overlap=overlap,
                                     mean_effective_rank=rank, gap=gap, tone_conflict=terms[1],
                                     local_enclosure_and_action=terms[3],
                                     mean_partner_rate_interdecile=spread))
                    keys = ('median_path_count', 'n_los', 'median_strongest_power_fraction',
                            'median_direct_power_fraction', 'median_direction_resultant')
                    for col, key in enumerate(keys):
                        rows[-1][key] = ((np.sum if col == 1 else np.median)(rays[:k, col])
                                         if kind == 'ray' else '')
    assert len(rows) == 1280
    with (revision / 'ray_geometry.csv').open('w', newline='') as fp:
        writer = csv.DictWriter(fp, rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
