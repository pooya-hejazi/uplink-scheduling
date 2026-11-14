"""Reproduce Note 5 tables and figures from frozen channels and archived measurements."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "data"
FIGURES = HERE / "figures"

def collect_geometry(o1, asu):
    spec = importlib.util.spec_from_file_location("ray_geometry", ROOT / "Gate_4/revision/ray_geometry.py")
    geometry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geometry)
    folders = {"O1_60": o1, "asu_campus1": asu}
    archive = ROOT / "Gate_3"
    rows = []
    for scene, folder in folders.items():
        metadata = geometry.ray_metadata(folder, archive, scene)
        manifest = pd.read_csv(archive / "ray_manifest.csv")
        for entry in manifest[manifest.scene == scene].itertuples():
            path = archive / "data" / f"pilot_{scene}_{entry.block:04d}.npz"
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry.file_sha256
            with np.load(path) as channel:
                raw = channel["h"]
                rays = np.asarray([metadata[int(u)] for u in channel["perm"]])
                assert np.array_equal(rays[:, 0], channel["paths"])
            runs = pd.read_csv(archive / "results/grid_ray" / f"{scene}_{entry.block:03d}.csv")
            for run in runs[runs.db == 10].itertuples():
                overlap, rank, span = geometry.describe(raw, run.k, run.scale)
                assert abs(sum(getattr(run, f"term{i}") for i in range(1, 5)) - run.G) < 1e-10
                rows.append(dict(scene=scene, block=entry.block, k=run.k, overlap=overlap,
                                 rank=rank, partner_span=span, paths=np.median(rays[:run.k, 0]),
                                 los=int(rays[:run.k, 1].sum()), gap=run.G,
                                 **{f"T{i}": getattr(run, f"term{i}") for i in range(1, 5)}))
    frame = pd.DataFrame(rows)
    assert len(frame) == 384
    frame.to_csv(DATA / "physics_geometry.csv", index=False)
    summary = frame.groupby(["scene", "k"]).median(numeric_only=True).drop(columns=["block", "los"])
    summary["los_links"] = frame.groupby(["scene", "k"]).los.sum()
    summary.to_csv(DATA / "physics_geometry_summary.csv")
    old = pd.read_csv(ROOT / "Gate_4/revision/ray_geometry.csv")
    check = frame.merge(old, left_on=["scene","block","k"], right_on=["family","block","k"])
    assert len(check) == 256
    assert np.allclose(check["rank"], check.mean_effective_rank)
    phase = pd.read_csv(archive / "results/phase_summary.csv")
    cross = pd.read_csv(archive / "results/cross_tap.csv")
    horizon = pd.read_csv(archive / "results/net_summary.csv")
    assert cross.minimum_augmented_eigenvalue.min() > -1e-12
    phase.to_csv(DATA / "physics_phase.csv", index=False)
    cross.groupby(["m1","law","regime"]).agg(cross_tap_mean=("cross_tap_abs","mean"),
                min_eigenvalue=("minimum_augmented_eigenvalue","min")).to_csv(DATA / "physics_cross_tap.csv")
    horizon.to_csv(DATA / "physics_horizon.csv", index=False)
    return frame

def make_figures():
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":8, "axes.titlesize":9,
                         "pdf.fonttype":42, "axes.spines.top":False, "axes.spines.right":False})
    geo = pd.read_csv(DATA / "physics_geometry.csv")
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 4.8), layout="constrained")
    colors = ["#244a70", "#c6682e"]
    for scene, color in zip(["O1_60", "asu_campus1"], colors):
        name = "O1" if scene == "O1_60" else "ASU"
        for k, style in zip([16, 32, 64], [":", "--", "-"]):
            group = geo[(geo.scene == scene) & (geo.k == k)]
            for ax, field in zip(axes.flat, ["overlap", "rank", "partner_span"]):
                ax.step(np.sort(group[field]), np.arange(1,65)/64, where="post",
                        color=color, ls=style, label=f"{name}, {k}")
    for ax, label, title in zip(axes.flat, ["Mean squared overlap", "Effective rank", "Partner-rate span (bit/s/Hz)"],
                                ["a   Spatial overlap", "b   Spatial degrees of freedom", "c   Fixed-power partner choice"]):
        ax.set(xlabel=label, ylabel="Fraction of 64 tiles")
        ax.set_title(title[0],loc="left",fontweight="bold")
        ax.grid(alpha=.2)
    axes[0,1].legend(fontsize=6.5, ncol=2, frameon=False)
    median = geo.groupby(["scene","k"])[["T1","T2","T3","T4"]].median()
    x = np.arange(6)
    for j, col in enumerate(["#244a70","#007e83","#c6682e","#7967a6"]):
        axes[1,1].bar(x+(j-1.5)*.19, median.iloc[:,j], .18, label=f"$T_{j+1}$", color=col)
    axes[1,1].set(xticks=x, xticklabels=[f"{'O1' if s=='O1_60' else 'ASU'}\n{k}" for s,k in median.index],
                  ylabel="Median component (bit/s/Hz)", yscale="log")
    axes[1,1].set_title("d",loc="left",fontweight="bold")
    axes[1,1].set_ylim(3e-7, 8)
    axes[1,1].legend(ncol=4, fontsize=7, frameon=False, loc="upper center")
    fig.savefig(FIGURES/"sfig5.pdf", bbox_inches="tight")
    plt.close(fig)
    horizon=pd.read_csv(DATA/'physics_horizon_intervals.csv')
    fig,axes=plt.subplots(1,2,figsize=(7.1,2.8),layout='constrained')
    for ax,arm,letter in zip(axes,['fixed','scaled'],['a','b']):
        for m,style,marker in zip([0,16,64,256,1024],['-','--','-.',':','-'],['o','s','^','D','x']):
            z=horizon[(horizon.family=='UMa')&(horizon.arm==arm)&(horizon.M==m)&(horizon.affordable==1)]
            line,=ax.plot(z.H,z.wins/z.n,ls=style,marker=marker,label=f'{m} extra blocks')
            ax.fill_between(z.H,z.lower,z.upper,color=line.get_color(),alpha=.10,lw=0)
        ax.set(xscale='log',xlabel='Stationary horizon (blocks)',ylabel='Fraction with certified net gain',ylim=(-.02,1.02))
        ax.set_title(letter,loc='left',fontweight='bold');ax.legend(fontsize=6.2,frameon=False);ax.grid(alpha=.2)
    fig.savefig(FIGURES/'sfig6.pdf',bbox_inches='tight');plt.close(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true",
                        help="Recompute geometry from original scene files before drawing figures")
    parser.add_argument("--o1", type=Path, help="Original O1_60 scene directory (required with --collect)")
    parser.add_argument("--asu", type=Path, help="Original asu_campus1 scene directory (required with --collect)")
    args = parser.parse_args()
    if args.collect:
        if args.o1 is None or args.asu is None:
            parser.error("--collect requires both --o1 PATH and --asu PATH")
        collect_geometry(args.o1, args.asu)
    make_figures()
