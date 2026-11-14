"""Reconstruct Supplementary Note 4 from frozen records without rerunning a solver."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "data"
FIGURES = HERE / "figures"
FAMILIES = ("A", "B", "C", "UMa")
METHODS = ("legacy", "det", "standalone", "hybrid")
LABELS = {"legacy": "Subgradient baseline", "det": "Deterministic search", "standalone": "Network only", "hybrid": "Learned warm start"}
COLORS = dict(zip(METHODS, ("#7b8091", "#175d83", "#b66b27", "#157b70")))
SOURCES = {}
MANIFESTS = {}
for gate in ("Gate_2", "Gate_2B", "Gate_3"):
    manifest = ROOT / gate / "SHA256SUMS"
    MANIFESTS.update({name.replace("\\", "/"): digest for digest, name in
                      (line.split(None, 1) for line in manifest.read_text().splitlines() if line.strip())})


def checked(name):
    path = ROOT / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == MANIFESTS[name], name
    SOURCES[name] = actual
    return path


def read(name):
    return pd.read_csv(checked(name))


def csv(name, frame):
    frame.to_csv(DATA / ("sim_" + name + ".csv"), index=False)


def quantiles(series):
    return np.quantile(series, [.05, .5, .95])


def save(fig, name):
    name={"sfig1":"sfig3","sfig2":"sfig4","sfig3":"sfig2","sfig4":"sfig1"}[name]
    for index, ax in enumerate(fig.axes):
        old=ax.get_title()
        if 'rho' in old or '\u03c1' in old:
            ax.text(.97,.06,old.split(' ',1)[-1],transform=ax.transAxes,ha='right',fontsize=7)
        ax.set_title(chr(97+index),loc='left',fontweight='bold')
        ax.set_title('')
    fig.savefig(FIGURES / (name + ".pdf"), bbox_inches="tight", pad_inches=.06)
    with plt.rc_context({"svg.fonttype":"none"}):
        fig.savefig(FIGURES/(name+".svg"),bbox_inches="tight",pad_inches=.06)
    plt.close(fig)


def table(caption, label, columns, records, widths=None):
    alignment = widths or ("l" * len(columns))
    lines = [r"\begin{table}[htbp]\centering\small",
             r"\setlength{\tabcolsep}{3pt}",
             r"\caption{" + caption + r"}\label{supp:" + label + "}",
             r"\begin{tabular}{" + alignment + r"}\toprule",
             " & ".join(columns) + r"\\\midrule"]
    lines += [" & ".join(map(str, row)) + r"\\" for row in records]
    return "\n".join(lines + [r"\bottomrule\end{tabular}\end{table}", ""])


def figure(number, caption):
    asset={1:3,2:4,3:2,4:1}[number]
    return (r"\begin{figure}[htbp]\centering" + "\n" +
            rf"\includegraphics[width=\linewidth]{{supplementary/figures/sfig{asset}.pdf}}" + "\n" +
            r"\caption{" + caption + rf"}}\label{{supp:fig{number}}}" + "\n" + r"\end{figure}" + "\n")


def main():
    DATA.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    for name in ("Gate_2/network.py", "Gate_2/teachers.py", "Gate_2/solver.py",
                 "Gate_2/train_gpu.py", "Gate_2B/polish.py", "Gate_2B/learn.py",
                 "Gate_2B/campaign.py", "Gate_3/structure.py", "Gate_3/grid.py",
                 "Gate_3/baselines.py", "Gate_3/matrix_methods.py", "Gate_3/ablations.py"):
        checked(name)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9,
                         "axes.labelsize": 8, "legend.fontsize": 7, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "lines.linewidth": 1.15})
    decisions = read("Gate_3/results/block_decisions.csv")
    times = read("Gate_3/results/times.csv")
    grid = read("Gate_3/results/sensitivity_grid.csv")
    ledger = read("Gate_3/results/conflict_attribution.csv")
    transition = read("Gate_3/results/transition.csv")
    load = read("Gate_3/results/load_sensitivity.csv")
    teachers = read("Gate_2/teachers/manifest.csv")
    validation = read("Gate_2B/results/validation.csv")
    freeze = json.loads(checked("Gate_2B/results/freeze.json").read_text())
    assert (len(decisions), len(times), len(grid), len(transition), len(teachers)) == (4096, 12288, 13824, 1152, 4096)
    assert teachers.groupby("K").size().to_dict() == {8:1368, 16:1364, 32:1364}
    assert (teachers.num_visited.sum(), teachers.strict_priority_comparisons.sum()) == (57296,56571)
    assert not grid.duplicated(["family", "block", "k", "db"]).any()
    assert set(grid.method) == {"det"}
    assert len(grid[grid.campaign == "native"]) == len(grid[grid.campaign == "analytic"]) == 6144
    assert len(grid[grid.campaign == "ray"]) == 1536
    assert np.allclose(grid[["term1", "term2", "term3", "term4"]].sum(axis=1), grid.G, atol=2e-12)
    assert np.allclose(transition[["term1", "term2", "term3", "term4"]].sum(axis=1), transition.total, atol=2e-12)
    assert transition.dominant.sum() == 0 and transition.total.max() < 3
    stage_fields = ["total_ns", "enclosure_ns", "dual_ns", "primal_ns", "neural_ns", "gpu_ms", "serialize_ns"]
    block_times = times.groupby(["family", "block", "k", "method"])[stage_fields].median().reset_index()
    for field in stage_fields:
        if field.endswith("_ns"):
            block_times[field.replace("_ns", "_ms")] = block_times[field] / 1e6
    primary = decisions.merge(block_times, on=["family", "block", "k", "method"], validate="one_to_one")
    assert np.allclose(primary.ms, primary.total_ms)
    assert np.array_equal(primary.ok, ((primary.G <= .15) & (primary.ms <= primary.k.map({32: 250, 64: 1000}))).astype(int))
    assert decisions.groupby(["k", "method"]).ok.sum().to_dict() == {
        (32, "det"): 506, (32, "hybrid"): 512, (32, "legacy"): 359, (32, "standalone"): 303,
        (64, "det"): 504, (64, "hybrid"): 509, (64, "legacy"): 294, (64, "standalone"): 340}
    summaries = []
    for k in (32, 64):
        for family in FAMILIES:
            for method in METHODS:
                part = primary[(primary.k == k) & (primary.family == family) & (primary.method == method)]
                assert len(part) == 128
                row = dict(k=k, family=family, method=method, n=len(part), hits=int(part.ok.sum()))
                for field in ["G", "total_ms", "enclosure_ms", "dual_ms", "primal_ms", "neural_ms", "gpu_ms", "serialize_ms"]:
                    row.update({field + "_" + name: value for name, value in zip(("p05", "p50", "p95"), quantiles(part[field]))})
                summaries.append(row)
    summary = pd.DataFrame(summaries)
    csv("primary_profiles", summary)
    csv("primary_blocks", primary)
    csv("primary_timed_calls", times)
    csv("sensitivity_cells", grid)
    csv("optimized_ledger", ledger)
    csv("fixed_policy_selectivity", transition)
    csv("teacher_records", teachers)
    teacher_summary = teachers.groupby(["K", "db"]).agg(n=("id", "size"),
        median_gap=("G", "median"), median_teacher_ns=("teacher_ns", "median"),
        visited=("num_visited", "sum"), comparisons=("strict_priority_comparisons", "sum")).reset_index()
    csv("teacher_summary", teacher_summary)
    seed_rows = []
    for seed in (1729, 2718, 3141):
        record = json.loads(checked(f"Gate_2B/results/seed_{seed}.json").read_text())
        vals = validation[validation.seed == seed]
        assert len(vals) == 256 and record["epochs"] == 15 and record["per_epoch"] == 4096
        score = next(r for r in freeze["scores"] if r["seed"] == seed)
        assert np.isclose(score["ecdf"], (vals.G.to_numpy()[:, None] <= np.array([.02, .05, .10, .15])).mean())
        seed_rows.append(dict(seed=seed, selected=int(seed == freeze["seed"]), validation_ecdf=score["ecdf"],
            validation_median_gap=score["median_G"], validation_median_ms=score["median_ms"],
            updates=record["optimizer_steps"], first_loss=record["loss"][0], final_loss=record["loss"][-1],
            training_seconds=record["seconds"]))
    seeds = pd.DataFrame(seed_rows)
    csv("seed_selection", seeds)
    csv("validation_records", validation)
    ablations = pd.concat([read(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/"Gate_3/results/ablations").glob("*.csv"))], ignore_index=True)
    assert len(ablations) == 3584 and not ablations.duplicated(["family", "block", "mode"]).any()
    csv("component_swaps", ablations)
    ablation_summary = ablations.groupby(["mode", "family"]).G.median().unstack("family")
    # Single-call grid and component-assembled neural timings remain separate cohorts.
    controls = pd.concat([read(p.relative_to(ROOT).as_posix())
        for group in ("native", "analytic", "ray")
        for p in sorted((ROOT/f"Gate_3/results/controls_{group}").glob("*.csv"))], ignore_index=True)
    extra = pd.concat([read(p.relative_to(ROOT).as_posix())
        for p in sorted((ROOT/"Gate_3/results/matrix_methods").glob("*.csv"))], ignore_index=True)
    complete = pd.concat([
        grid[["family", "block", "k", "db", "method", "G", "Lbit", "Ubit", "total_ns"]].rename(
            columns={"Lbit": "L", "Ubit": "U"}).assign(ms=grid.total_ns/1e6, timing_cohort="single_call_grid"),
        controls.assign(timing_cohort="single_call_classical"),
        extra.rename(columns={"component_ms": "ms"}).assign(timing_cohort="assembled_shared_proposal"),
        decisions[decisions.method != "det"].rename(columns={"ok": "primary_pass"}).assign(
            db=10, timing_cohort="three_repeat_primary")
    ], ignore_index=True)
    assert len(complete) == 96768 and not complete.duplicated(["family", "block", "k", "db", "method"]).any()
    assert complete.G.notna().all() and (complete.G >= 0).all()
    counts = complete.groupby(["family", "block", "k", "db"]).size()
    assert len(counts) == 13824 and (counts == 7).all()
    campaign = grid.set_index("family").campaign.to_dict()
    complete["campaign"] = complete.family.map(campaign)
    csv("sensitivity_methods", complete)
    grouped = complete.groupby(["campaign", "family", "k", "db", "method", "timing_cohort"])
    grid_summary = grouped.agg(n=("G", "size"), gap_p05=("G", lambda s:s.quantile(.05)),
        gap_p50=("G", "median"), gap_p95=("G", lambda s:s.quantile(.95)), median_ms=("ms", "median")).reset_index()
    csv("sensitivity_summary", grid_summary)
    paired_load = load.merge(primary[["family", "block", "k", "method", "ms"]], on=["family", "block", "k", "method"],
                            validate="one_to_one").rename(columns={"ms": "primary_median_ms"})
    paired_load["shuffled_ms"] = paired_load.total_ns/1e6
    paired_load["ratio"] = paired_load.shuffled_ms/paired_load.primary_median_ms
    assert len(paired_load) == 416
    csv("shuffled_load", paired_load)
    exact = grid.query("campaign=='native' and k==16 and db==10")
    assert len(exact) == 512 and (exact.loss <= exact.posterior+1e-12).all()
    csv("exact_dp_profiles", exact)

    fig, axes = plt.subplots(2, 4, figsize=(7, 3.8), sharex=True, sharey=True, layout="constrained")
    for row, k in enumerate((32, 64)):
        for col, family in enumerate(FAMILIES):
            ax = axes[row, col]
            for method in METHODS:
                values = primary[(primary.k == k) & (primary.family == family) & (primary.method == method)]
                x = np.sort(values.loc[values.ms <= (250 if k == 32 else 1000), "G"])
                ax.step(x, np.arange(1,len(x)+1)/128, where="post", label=LABELS[method], color=COLORS[method])
            ax.axvline(.15, color="#444444", lw=.7, ls=":")
            ax.set(xlim=(0,.4), ylim=(0,1.03), title=f"{family if family=='UMa' else 'CDL-'+family}, {k} users")
            if col == 0:ax.set_ylabel("Fraction of 128 blocks")
            if row == 1:ax.set_xlabel("Gap (bit/s/Hz)")
    axes[0,0].legend(loc="lower right", fontsize=6)
    save(fig, "sfig1")
    fig, axes = plt.subplots(1, 3, figsize=(7, 2.8), layout="constrained")
    stage_names = ["enclosure_ms", "dual_ms", "primal_ms", "neural_ms", "gpu_ms"]
    for ax, k in zip(axes[:2], (32,64)):
        for j, method in enumerate(METHODS):
            part = primary[(primary.k == k) & (primary.method == method)]
            x = np.arange(5)+(j-1.5)*.16
            qs = np.array([quantiles(part[s]) for s in stage_names])
            positive = qs[:,1] > 0
            ax.errorbar(x[positive], qs[positive,1], yerr=[qs[positive,1]-qs[positive,0],
                        qs[positive,2]-qs[positive,1]],
                        fmt="o", ms=2.2, lw=.7, color=COLORS[method], label=LABELS[method])
        ax.set(yscale="log", xticks=range(5), xticklabels=["Box","Dual","Primal","Host NN","GPU"],
               title=f"{k} users", ylabel="Stage time (ms)")
        ax.tick_params(axis="x", labelsize=6.5, rotation=30)
    ax = axes[2]
    for k, marker, offset in [(32,"o",-.10),(64,"s",.10)]:
        for j,method in enumerate(METHODS):
            qs = quantiles(paired_load[(paired_load.k == k) & (paired_load.method == method)].ratio)
            ax.errorbar(j+offset,qs[1],yerr=[[qs[1]-qs[0]],[qs[2]-qs[1]]],fmt=marker,ms=3,
                        color=COLORS[method],lw=.8)
    ax.axhline(1,color="#444444",ls=":",lw=.7)
    ax.set(yscale="log",xticks=range(4),xticklabels=["Subgradient baseline","Deterministic search","Network only","Learned warm start"],ylabel="Shuffled / primary time",
           title="52 paired blocks")
    ax.tick_params(axis="x", labelsize=6.5, rotation=30)
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", rotation_mode="anchor")
    axes[0].legend(fontsize=5.7,loc="upper left")
    save(fig, "sfig2")
    fig = plt.figure(figsize=(7,5.2),layout="constrained")
    layout = fig.add_gridspec(3,4)
    axes = np.array([[fig.add_subplot(layout[row,col]) for col in range(4)] for row in range(2)])
    term_colors = ["#244a70","#007e83","#c6682e","#7967a6"]
    for row,k in enumerate((32,64)):
        for col,family in enumerate(FAMILIES):
            ax=axes[row,col]
            means=grid[(grid.campaign == "native") & (grid.k == k) & (grid.family == family)].groupby("db")[["term1","term2","term3","term4"]].mean()
            bottom=np.zeros(4)
            for j,color in enumerate(term_colors):
                ax.bar(np.arange(4),means.iloc[:,j],bottom=bottom,color=color,width=.7,label=f"$T_{j+1}$")
                bottom+=means.iloc[:,j].to_numpy()
            ax.set(xticks=range(4),xticklabels=["−5","0","10","20"],title=f"{family if family=='UMa' else 'CDL-'+family}, {k}")
            if col==0:ax.set_ylabel("Mean gap (bit/s/Hz)")
            if row==1:ax.set_xlabel("SNR (dB)")
    axes[0,0].set_ylim(top=axes[0,0].get_ylim()[1]*1.4)
    axes[0,0].legend(ncol=2,fontsize=6,loc="upper right")
    ax = fig.add_subplot(layout[2,:2])
    for field,color,label in [("total","#244a70","Frozen-action gap"),("term2","#007e83","Action component $T_2$"),("dc","#c6682e","Matching conflict")]:
        group=transition.groupby("t")[field]
        med=group.median()
        ax.plot(med.index,med,color=color,label=label)
        ax.fill_between(med.index,group.quantile(.25),group.quantile(.75),color=color,alpha=.12)
    ax.set(xlabel="Selectivity interpolation",ylabel="bit/s/Hz",title="Frozen sequential action, 16 users")
    ax.legend(fontsize=6,loc="upper left")
    ax = fig.add_subplot(layout[2,2:])
    ratios=transition.assign(action_ratio=transition.term2/transition.total,matching_ratio=transition.dc/transition.total)
    for field,color,label in [("action_ratio","#007e83","Action $T_2/G$"),("matching_ratio","#c6682e","Matching conflict / $G$")]:
        group=ratios.groupby("t")[field]
        med=group.median()
        ax.plot(med.index,med,color=color,label=label)
        ax.fill_between(med.index,group.quantile(.25),group.quantile(.75),color=color,alpha=.12)
    ax.axhline(.5,color="#444444",ls=":",lw=.7)
    ax.set(xlabel="Selectivity interpolation",ylabel="Fraction of interval",ylim=(0,1),title="Different pairings in numerator")
    ax.legend(fontsize=6,loc="upper left")
    save(fig,"sfig3")
    fig,axes=plt.subplots(1,4,figsize=(7,2.2),sharey=True,layout="constrained")
    for ax,family in zip(axes,FAMILIES):
        part=exact[exact.family==family]
        ax.scatter(part.posterior,part.loss,s=7,alpha=.5,color="#157b70",edgecolors="none")
        end=max(part.posterior.max(),part.loss.max())*1.03
        ax.plot([0,end],[0,end],ls=":",color="#444444",lw=.7)
        rho=spearmanr(part.posterior,part.loss).statistic
        ax.set(xlim=(0,end),title=f"{family if family=='UMa' else 'CDL-'+family}, ρ={rho:.2f}",xlabel="Posterior conflict")
    axes[0].set_ylabel("Exact table loss")
    axes[0].set_ylim(0, exact.loss.max()*1.08)
    save(fig,"sfig4")
    write_note(summary,seeds,ablation_summary,complete,transition,ledger)
    csv("source_hashes",pd.DataFrame([dict(path=k,sha256=v) for k,v in sorted(SOURCES.items())]))
    print("Verified 4,096 primary blocks, 12,288 timed calls, 13,824 grid cells and 96,768 method-cell records.")


NOTE = "\n\\section{Deterministic price search and extended simulation benchmarks}\\label{supp:note4}\n\n\\subsection{Executable price and action updates}\nThe implementation uses the interval table from Supplementary Note~7 and integer\nscores \\(H_{es}=\\lceil\\Gamma\\overline q_{es}\\rceil\\), where \\(e=\\{i,j\\}\\),\n\\(\\Gamma=2^{40}\\) and \\(\\overline q\\) already subtracts the total-power price.\nWrite \\(F=H/\\Gamma\\), \\(g_{is}=\\|h_{is}\\|^2\\), and\n\\(r_{es}=|h_{is}^{H}h_{js}|^2/(g_{is}g_{js})\\).\nThe deterministic price is the nearest integer to\n\\(\\operatorname{median}_{i,s}g_{is}/(1+0.1g_{is})\\), clipped to \\([0,10]\\).\nIts initial concave-envelope anchor is\n\\(\\operatorname{clip}(1/\\max(1,\\lambda)-1/G_{is},0.05,0.20)\\), with\nthe positive upper norm endpoint \\(G_{is}\\) protected against underflow.\nFor every pair the two highest-scoring tones enter a refinement pool.\nAt most \\(\\max(2,\\lfloor K^2/32\\rfloor)\\) pair--tone roots are refined.\nThe deterministic priority is the priced upper score, and a learned-only run uses\nthe predicted priority. All roots remain covered.\n\nDefine the implemented price quantizer\n\\[\n {\\cal T}(v)=\\Gamma^{-1}\\operatorname{rint}\n \\{\\Gamma\\operatorname{clip}(v-\\overline v,-32,32)\\}.\n\\]\nAt a price iterate \\(\\beta\\), exact general matching uses\n\\(w_e=\\max_s(H_{es}-\\Gamma\\beta_s)\\).\nBipartite assignment of the resulting matching uses the unpriced \\(H\\).\nIts tone dual potentials, divided by \\(\\Gamma\\) and centred, form \\(a\\).\nThe update uses the lowest-bound iterate found within the current branch,\ndenoted \\((\\beta_*,M_*)\\). For this iterate let\n\\[\n n_s=\\sum_{e\\in M_*}{\\bf1}\n \\{s=\\arg\\max_t(F_{et}-\\beta_{*,t})\\}-1,\\qquad\n c_s=\\tfrac12\\sum_i{\\bf1}\\{s=s_i\\}-1 ,\n\\]\nwhere \\((j_i,s_i)\\) maximizes \\(F_{\\{i,j\\},s}-\\beta_{*,s}-u_j\\) over\n\\(j\\ne i,s\\), and \\(u_j=S^{-1}\\sum_s\\log(1+0.1g_{js})\\).\nThe next price is\n\\begin{equation}\\label{supp:priceupdate}\n \\beta_{\\rm next}={\\cal T}\\!\\left[\n 0.42\\beta_*+0.58a+\n \\frac{0.05}{1+0.35\\max(0,\\ell-2)}\n (0.75n+0.25c)\\right].\n\\end{equation}\nHere \\(\\ell\\) starts at zero in each branch. Discrete ties follow the ordered\narray operations in the released code. The following steps specify the search.\n\n\\begin{enumerate}\n\\item Build and quantize \\(H\\). Initialize a nominal matching using the\nbest equal-power rate of each pair over tones.\n\\item In the deterministic branch evaluate seven price iterates at \\(K\\le32\\) and six\nat \\(K=64\\). The first three initializers are zero, the centred tone-wise\nmean of \\(F\\), and a centred tone price from assigning users to two duplicate\nslots per tone with scores \\(\\log(1+0.1g_{is})\\).\nSubsequent iterates use equation~\\eqref{supp:priceupdate}.\n\\item Retain the smallest valid upper objective over the branch. Check its\nodd-set witness. On an arithmetic failure, the vertex-price repair supplies\na valid upper witness and the conflict statistic is left undefined.\n\\item Form feasible candidates from the sequential pairing and all matchings\nvisited so far. Assign distinct tones using nominal equal-power rates,\nthen perform up to four sweeps over pairs of assigned tones.\nEach sweep considers a tone swap and the four ordered allocations obtained\nby exchanging partners between the two pairs.\n\\item Candidate edges include every incumbent edge and up to\n\\(\\min(6,S)\\) disjoint edges per tone selected by a user-centred nominal score.\nAccept a local exchange only if both edges are allowed and the score rises\nby more than \\(10^{-11}\\). Deduplicate complete assignments, rank their\nnominal rates, and refine the best three.\n\\item Certify each refined action with its actual powers and receive filters.\nRetain the largest checked lower endpoint. In learned warm start, append\nthree learned-price iterates while preserving the deterministic upper and lower\nincumbents. A learned-only run uses one learned-price iterate and one\nmatched/assigned action.\n\\end{enumerate}\n\nFor fixed assigned partners, let \\(x=p_i g_i\\), \\(y=p_j g_j\\) and\n\\(D=1+x+y+(1-r)xy\\). The rate gradient is\n\\[\n \\partial_{p_i}q=g_i\\!\\left[\\frac{2\\{1+(1-r)y\\}}{D}\n                  -\\frac{1}{1+x}\\right],\n\\]\nwith the symmetric expression for \\(j\\).\nFour trial steps use\n\\(p'=\\Pi[p+\\eta\\,0.05\\,\\nabla q/\\max(10^{-12},\\|\\nabla q\\|_\\infty)]\\),\n\\(\\eta\\in\\{1,\\tfrac12,\\tfrac14,\\tfrac18\\}\\).\nEach is accepted only when the nominal sum rate does not decrease.\nHere \\(\\Pi\\) is the implemented feasible integer map. With\n\\(P_T=20\\,2^{20}\\), first round \\(P_Tp_i\\) and clip to\n\\([P_T/20,P_T/5]\\). If the sum exceeds \\(KP_T/10\\), scale each excess\nabove \\(P_T/20\\) by \\(KP_T/20\\) divided by the total excess and round\ndown. Dividing the final ticks by \\(P_T\\) gives physical powers.\nThis map can leave power unused. Separate MMSE combining vectors\nare recomputed at the accepted powers before the lower endpoint is checked.\n\n\\subsection{Message passing, supervision and the held-out seed choice}\nLet \\(E=K(K-1)/2\\) be the number of pairs.\nThe network has user, pair, tone and pair--tone factor states of width\n\\(d=32\\). Its seven factor inputs are\n\\[\n x_{es}=(a_i+a_j,\\ |a_i-a_j|,\\ r_{es},\\\n        s/\\max(1,S-1),\\ 0,\\tfrac12,2),\\qquad\n a_i=\\tfrac15\\log(1+0.1g_{is}),\n\\]\nwith zero-based tone indices and coordinate zero when \\(S=1\\). Initial factor states are\n\\(f^0_{es}=\\operatorname{ReLU}(W_xx_{es}+b_x)\\).\nInitial pair and tone states are their means over tones and pairs.\nThe initial user state is the mean of its \\(K-1\\) incident pair states.\nEach of three residual layers applies independent two-affine-layer maps\n\\(\\phi(z)=W_2\\operatorname{ReLU}(W_1z+b_1)+b_2\\), with hidden width 32.\nThe ordered updates are\n\\begin{align*}\n f^{\\ell+1}_{es}&=f^\\ell_{es}+\n \\phi_f^\\ell([f^\\ell_{es},e^\\ell_e,t^\\ell_s,\n                         u^\\ell_i+u^\\ell_j,|u^\\ell_i-u^\\ell_j|]),\\\\\n e^{\\ell+1}_e&=e^\\ell_e+\n \\phi_e^\\ell([e^\\ell_e,S^{-1}\\textstyle\\sum_s f^{\\ell+1}_{es}]),\\\\\n t^{\\ell+1}_s&=t^\\ell_s+\n \\phi_t^\\ell([t^\\ell_s,E^{-1}\\textstyle\\sum_e f^{\\ell+1}_{es}]),\\\\\n u^{\\ell+1}_i&=u^\\ell_i+\n \\phi_u^\\ell([u^\\ell_i,(K-1)^{-1}\\textstyle\\sum_{e\\ni i}e^{\\ell+1}_e]).\n\\end{align*}\nThus pair permutation and user exchange are respected by the shared maps,\nwhile tone position is explicitly present in the input.\n\nTwo user outputs give \\(p_i=0.05+0.15\\sigma(z_{i1})\\) and the centred\n\\(\\alpha_i=z_{i2}-K^{-1}\\sum_jz_{j2}\\).\nA tone head gives centred \\(\\beta_s\\), a global mean-user head gives\n\\(\\lambda=12\\sigma(z_\\lambda)\\), and a factor head adds a residual\n\\(0.1z_{es}\\) to the observed equal-power pair rate.\nA shared box head reads \\([f_{es},l_1,u_1,l_2,u_2]\\) in normalized box\ncoordinates and returns two sigmoid-mapped anchors in \\([0.05,0.20]\\)\nand one unconstrained priority. The same head scores root boxes and\nthe two half-boxes used in priority supervision. At inference the worker\nevaluates both half-boxes for the \\(\\max(2,\\lfloor K^2/32\\rfloor)\\)\nhighest-priority factors and adds \\(0.05\\) times the larger child score\nto each selected root priority. Pair-endpoint anchor suggestions are\naveraged over the \\(K-1\\) incident pairs to produce each user's anchor\non a tone. GPU timing includes these head evaluations and aggregation.\nThere are 52,776 trainable\nparameters. The hybrid search consumes the predicted tone prices\nwhile retaining the deterministic power-price/enclosure table and its deterministic\naction pool. The network-only comparator additionally uses the predicted\npower price, anchors, priorities, pair scores and powers.\nThe predicted user-price head is supervised but is not used by the\ndeterministic solver's upper certificate.\n\nTeachers were generated on 4,096 fitting blocks only, comprising 1,024\nblocks from each of the analytic, CDL-A, CDL-B and CDL-C generators.\nUser counts were \\(8,16,32\\), with \\(1,368,1,364,1,364\\) examples,\nrespectively. SNRs were \\(0,10,20\\) dB. The teacher solver produced\nfeasible actions, power-price and dual targets, enclosure anchors, 57,296\nvisited-root labels and 56,571 strict sibling-priority comparisons.\nThe median teacher interval was 0.083914 bit/s/Hz and median recorded\nteacher time was 9.487 ms. Before this training run, tone-price targets\nwere recomputed from an exact assignment of equal-power nominal scores\nfor the teacher's selected pairs.\n\nThe loss sums an equally positive/negative-weighted logistic pair-assignment\nloss, mean-square power and anchor errors divided by \\(0.15^2\\), centred\nuser/tone-price errors divided by \\(4^2\\), power-price error divided by\n\\(10^2\\), and softplus ranking losses for strict sibling and visited-root\npriority comparisons. Priority pairs whose target difference is at most\n\\(10^{-10}\\) are omitted. Batches have at most eight examples of one size.\nEach of seeds 1729, 2718 and 3141 receives 15 epochs over all 4,096 examples,\n7,695 Adam updates at learning rate \\(10^{-3}\\), and gradient-norm clipping\nat 3. TensorFloat-32 matrix products are disabled.\nThe recorded GPU was an NVIDIA Quadro RTX 4000 with Max-Q Design.\n\nSeed selection uses 256 separate validation blocks and the mean empirical\ncoverage of gap cutoffs \\(0.02\\), \\(0.05\\), \\(0.10\\) and \\(0.15\\) bit/s/Hz. Ties are broken\nby median gap, median latency, then seed. Seed 1729 was locked before\nthe primary test. Table~\\ref{supp:table4} also gives component swaps on a\nseparate post-freeze benchmark of all 512 native 32-user blocks.\nThose swaps retain the deterministic power price and replace the named\nfield. Their baseline is rerun within that benchmark.\n\n\\subsection{Timing cohorts, sensitivity records and the selectivity diagnostic}\nTable~\\ref{supp:table3} and Fig.~\\ref{supp:fig1} use the 12,288 timed\nprimary calls. For each topology and method, the primary gap is the\nlargest of three returned gaps and latency is the median of three\ncomplete calls. A pass requires \\(G\\le0.15\\) bit/s/Hz and median time\nat most 250 ms for 32 users or 1,000 ms for 64 users.\nThere are 128 independent blocks per profile. Timers start after channel\ncropping and normalization, with kernels and the GPU worker already warmed.\nStage summaries first take\nthe median of the three stage times within each block, then the indicated\nquantile over blocks. Host neural time includes the prediction request\nand response. GPU time is the worker's synchronized forward measurement\nand overlaps host neural time. It is not an additional stage to sum.\nSerialization and other orchestration are included in complete time.\nMedians of separate stages need not add to the median complete time.\n\nThe separate shuffled-order experiment draws 52 blocks by a fixed hash\nranking and makes one additional call per size and method in permuted\nmethod order (416 calls). Figure~\\ref{supp:fig2} compares each such time\nwith the same block's original median. These data describe load/order\nsensitivity and do not replace the primary deadline decisions.\n\nThe sensitivity grid contains 13,824 deterministic cells\n\\((6,144\\ {\\rm native},6,144\\ {\\rm analytic},1,536\\ {\\rm ray})\\),\ncovering four SNRs, three user counts and 1,152 base topologies.\nThree classical controls are evaluated on every cell.\nThe network-only, learned-warm-start and subgradient-baseline controls use a shared learned\nproposal in 12,800 non-primary cells. Their recorded component times include\nthe shared proposal's time and cannot be substituted for complete primary\ntimings. The remaining 1,024 native 10-dB cells use the three-repeat\nprimary records for those methods. The full 96,768 method-cell records\nand all family/size/SNR/method summaries accompany\nTable~\\ref{supp:table5}. Classical control runs use the same native\nmatching implementation as the deterministic solver, whereas the primary\nsubgradient baseline retains its original matching implementation.\nNo timing cohorts are pooled for a new pass/fail claim.\n\nThe fixed-policy selectivity experiment uses 128 analytic 16-user channels\ninterpolated at nine values between the first-tone channel and the\nfrequency-selective channel. At each interpolation the sequential pairing,\ntone order and 0.10-W powers are fixed, with its receiver recomputed for\nthat input. Its interval ranges from 0.035915 to 2.343011 bit/s/Hz.\nThe ratio of the \\emph{price-selected matching's} conflict bound to this\nfixed action's interval never exceeds 0.377035.\nHowever, the actual fixed-action decomposition \\(T_2\\) exceeds half the interval\nin 980 of 1,152 cases. The two numerators belong to different pairings,\nas shown in Fig.~\\ref{supp:fig3}.\nFor the separate optimized native primary cohort, mean \\(T_2\\) is\n0.041201 of a 0.065232-bit/s/Hz mean interval at 32 users and\n0.058741 of 0.072248 at 64 users. These observations do not identify a\nuniversal transition of optimized schedules from the frozen-action\ncrossing test. Figure~\\ref{supp:fig4} tests the posterior bound against\nthe exact optimum of the same rounded table at 16 users, separately\nwithin each native profile.\n\n"


def write_note(summary, seeds, swaps, complete, transition, ledger):
    gap_rows = []
    stage_rows = []
    for r in summary.itertuples():
        gap_rows.append([r.k, r.family, LABELS[r.method], f"{r.hits}/128",
            f"{r.G_p05:.3f}",f"{r.G_p50:.3f}",f"{r.G_p95:.3f}","",""])
        stage_rows.append([r.k, r.family, LABELS[r.method],
            f"{r.enclosure_ms_p50:.1f}",f"{r.dual_ms_p50:.1f}",f"{r.primal_ms_p50:.1f}",
            f"{r.neural_ms_p50:.1f}",f"{r.gpu_ms_p50:.1f}",f"{r.total_ms_p50:.1f}"])
    s3 = r"\begingroup\small\setlength{\tabcolsep}{4pt}"+'\n'
    s3 += r"\begin{longtable}{lrlrrrr}\caption{Native 10-dB primary results by profile. Panel A gives gap quantiles (bit/s/Hz) and joint passes; Panel B gives median stage times (ms). GPU time is included in host prediction time.}\label{supp:table3}\\"+'\n'
    s3 += r"\toprule Method & $K$ & Profile & Pass & p05 & p50 & p95\\\midrule\endfirsthead\toprule Method & $K$ & Profile & Pass & p05 & p50 & p95\\\midrule\endhead\bottomrule\endfoot"+'\n'
    s3 += '\n'.join(' & '.join(map(str,[r[2],r[0],r[1],*r[3:7]]))+r'\\' for r in gap_rows)
    s3 += r"\end{longtable}\addtocounter{table}{-1}\renewcommand{\theHtable}{\arabic{table}B}\begin{longtable}{lrlrrrrrr}\multicolumn{9}{l}{\textbf{B. Median stage and complete times}}\\\toprule Method & $K$ & Profile & Box & Dual & Primal & NN & GPU & All\\\midrule\endfirsthead\toprule Method & $K$ & Profile & Box & Dual & Primal & NN & GPU & All\\\midrule\endhead\bottomrule\endfoot"+'\n'
    s3 += '\n'.join(' & '.join(map(str,[r[2],r[0],r[1],*r[3:]]))+r'\\' for r in stage_rows)
    s3 += r"\end{longtable}\endgroup"+'\n'
    s4 = r"\begin{table}[htbp]\centering\small" + "\n" + r"\caption{Frozen seed selection and post-freeze component swaps. Validation scores average four prespecified gap cutoffs. Swap values are median gaps in bit/s/Hz at 32 users and 10 dB, with 128 blocks per profile.}\label{supp:table4}" + "\n"
    s4 += r"\begin{tabular}{rrrrrr}\toprule Seed & Score & Median gap & Median ms & Final loss & Train s\\\midrule" + "\n"
    for r in seeds.itertuples():
        s4 += f"{r.seed}{'*' if r.selected else ''} & {r.validation_ecdf:.6f} & {r.validation_median_gap:.6f} & {r.validation_median_ms:.2f} & {r.final_loss:.4f} & {r.training_seconds:.1f}" + r"\\" + "\n"
    s4 += r"\bottomrule\end{tabular}\par\smallskip" + "\n" + r"\begin{tabular}{lrrrr}\toprule Component setting & CDL-A & CDL-B & CDL-C & UMa\\\midrule" + "\n"
    names={"deterministic_polish":"Deterministic baseline","swap_learned_beta":"Learned tone price",
           "swap_learned_primal":"Learned primal proposal","swap_learned_anchor":"Learned enclosure anchor",
           "swap_learned_priority":"Learned refinement priority","P3_repair_only":"Vertex-price repair",
           "one_shot_MLP_projected":"One-hidden-layer MLP"}
    for key,name in names.items():
        s4 += name+" & "+" & ".join(f"{swaps.loc[key,f]:.6f}" for f in FAMILIES)+r"\\"+"\n"
    s4 += r"\bottomrule\end{tabular}\par\smallskip\footnotesize *Selected before testing. The MLP has 32 hidden units and five fitting passes. Its inputs are matched to the pair features used by the message-passing model.\end{table}" + "\n"
    small = complete[complete.method.isin(["det","cold","equal_match","sequential"])]
    agg = small.groupby(["campaign","k","db","method"]).G.median().unstack("method")
    rows=[]
    for campaign in ("native","analytic","ray"):
        for k in (16,32,64):
            for db in (-5,0,10,20):
                values=agg.loc[campaign,k,db]
                rows.append([campaign,k,db,*[f"{values[m]:.3f}" for m in ("det","cold","equal_match","sequential")]])
    s5=table("Sensitivity-grid summary. Each entry is a median certified gap in bit/s/Hz over "
             "512 native, 512 analytic or 128 ray-traced topologies at the indicated size and SNR. "
             "Zero denotes the zero-price baseline, Match the equal-power-initialized matching with power refinement "
             "control and Seq. sequential pairing. Full per-family quantiles and seven-method comparisons "
             "are supplied in the accompanying CSV files.",
             "table5",["Campaign","$K$","SNR (dB)","Deterministic search","Zero","Match","Seq."],rows)
    f1=figure(1,r"Deadline-aware empirical gap distributions within each native profile. Panels a--d show 32 users and e--h show 64 users; within each row the profiles are CDL-A, CDL-B, CDL-C and UMa. Each panel contains 128 independent blocks. Only on-time outcomes increment the curve, and the denominator remains 128. The vertical line is the 0.15-bit/s/Hz criterion. The horizontal display ends at 0.4 bit/s/Hz and retains the full denominator for larger gaps.")
    f2=figure(2,r"Stage-time and load sensitivity. Panels a and b show 32 and 64 users, respectively; panel c shows the shuffled-order comparison. Left and centre, dots show medians and whiskers show p05--p95 across 512 block-level stage medians. Zero GPU/host-network times for the classical methods are omitted on the log axis. GPU and host neural intervals overlap. Right, p05/median/p95 of shuffled-call latency divided by the same block's original median, for 52 blocks. Circles denote 32 users and squares 64 users. Colours identify the same methods throughout.")
    f3=figure(3,r"Four-term decomposition and the fixed-policy selectivity test. Panels a--d show 32 users and e--h show 64 users, with CDL-A, CDL-B, CDL-C and UMa from left to right. Panels i and j show absolute and relative contributions for the fixed sequential action at 16 users. The upper eight panels stack mean terms over 128 native blocks per profile, size and SNR in the separately timed sensitivity grid. All four means sum to the mean interval, including the small unused-power term. The lower panels show medians and interquartile bands over 128 analytic 16-user blocks at each interpolation. The sequential action's \(T_2\) and the price-selected matching's conflict statistic use different pairings. The dotted line marks one half of the action interval.")
    f4=figure(4,r"Exact labelled-table comparisons at 16 users and 10 dB. Panels a--d show CDL-A, CDL-B, CDL-C and UMa, respectively. Each panel shows 128 independent native blocks. Both axes are in bit/s/Hz. The vertical value is \(R_\beta-D(H)\), and the horizontal value is \(R_\beta-A_\beta\). The dotted diagonal is equality, and each annotation reports its within-profile Spearman correlation. The comparison concerns the rounded integer table.")
    extra = r'The original learned-versus-deterministic pass increases were 1.17 percentage points at 32 users (95\% stratified bootstrap interval 0.39--2.15) and 0.98 at 64 users (0.20--1.95). The original resource-subgradient baseline passed on 359 of 512 and 294 of 512 topologies, respectively, with a median complete time of 715 ms at 64 users.'
    heading = r'\subsection{Timing cohorts, sensitivity records and the selectivity diagnostic}'
    assert NOTE.count(heading) == 1
    note = NOTE.replace(heading, extra+'\n\n'+heading)
    (HERE/"note4_solver.tex").write_text(note+"\n"+s3+s4+s5+"\n"+'\\input{reviewer_rates}\n\\input{reviewer_compute}\n\\input{reviewer_decomposition}\n'+f4+f3+f1+f2,encoding="utf-8")


if __name__ == "__main__":
    main()

