"""Build the article bibliography and supplementary literature comparison."""
import csv
import json
import re
from pathlib import Path


REVISION = Path(__file__).resolve().parent
ARTICLE = REVISION.parent
COMMAND = re.compile(r"\\(input|cite)\s*\{([^}]+)\}")
COMPARISON = ("contribution", "strength", "limitation", "distance")
ESCAPE = str.maketrans({
    "&": r"\&", "%": r"\%", "_": r"\_", "#": r"\#", "$": r"\$",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}", "\\": r"\textbackslash{}",
})
VENUES = {
    "Nature Communications": "Nat. Commun.", "Scientific Reports": "Sci. Rep.",
    "npj Wireless Technology": "npj Wirel. Technol.",
}


def cited_keys(path):
    source = re.sub(r"(?<!\\)%[^\n]*", "", path.read_text(encoding="utf-8"))
    for command, argument in COMMAND.findall(source):
        if command == "cite":
            yield from (key.strip() for key in argument.split(","))
        elif argument not in ("references", "references.tex"):
            yield from cited_keys(path.parent / Path(argument).with_suffix(".tex"))


def records():
    catalog = {}
    for path in sorted(REVISION.glob("refs_*.json")):
        for row in json.loads(path.read_text(encoding="utf-8-sig")):
            if row["key"] in catalog:
                raise ValueError(f"Repeated reference key: {row['key']}")
            catalog[row["key"]] = row
    return catalog


def select(catalog, keys):
    selected = [catalog[k] for k in dict.fromkeys(keys)]
    if not selected:
        raise ValueError("The article has no numbered references.")
    for row in selected:
        if "manuscript" in row["venue"].lower():
            raise ValueError(f"Unpublished manuscript in numbered references: {row['key']}")
        for field in ("title", "authors", "evidence_url", *COMPARISON):
            if not row.get(field, "").strip():
                raise ValueError(f"Missing {field} for {row['key']}")
    return selected


def tex(text):
    return text.translate(ESCAPE)


def reference(row):
    authors = tex(row["authors"]).rstrip(".") + "."
    url = row["url"]
    title = rf"\href{{{url}}}{{{tex(row['title'])}}}"
    venue = VENUES.get(row["venue"], row["venue"])
    details = rf"\emph{{{tex(venue)}}}"
    if row["volume"]:
        volume = tex(str(row["volume"]))
        details += (", " + volume) if row["key"] == "tr" else rf" \textbf{{{volume}}}"
    if row["pages"]:
        details += ", " + tex(str(row["pages"]))
    ref = f"{authors} {title}. {details} ({row['year']})."
    return ref


def bibliography(rows):
    items = [rf"\bibitem{{{r['key']}}} {reference(r)}" for r in rows]
    return "\n".join([rf"\begin{{thebibliography}}{{{len(rows)}}}\small", *items,
                      r"\end{thebibliography}", ""])


def supplement(rows):
    comparisons = [
        ('viterbo','Viterbo and Hottinen','Equal-energy paired uplink; MMSE/ML detection','Optimal pairing','Optimum in its pairing model','Tone-dependent conflicts and continuous powers'),
        ('fan','Fan et al.','LTE uplink; linear MMSE','Pairing and contiguous allocation','Discrete search with prescribed powers','Full power-domain ceiling for a delivered action'),
        ('ruder2013','Ruder et al. (2013)','SC-FDMA; receiver-specific metrics','Blossom pairing and joint grouping','Small full-enumeration benchmark','Scalable checked relaxation across labelled tones'),
        ('ruder2014','Ruder et al. (2014)','SC-FDMA; imperfect scheduling CSI','MMSE prediction and grouping','Small perfect-CSI search benchmark','Calibrated errors along stored receive directions'),
        ('prasad','Prasad et al.','LTE-A; matroid/knapsack constraints','Submodular scheduling','Approximation and restricted-model upper bounds','Additive action-specific interval in the paired model'),
        ('shenfptwo','Shen and Yu','Interfering uplinks; powers/beamformers','Fractional programming and matching','Iterative objective improvement','Upper endpoint covers alternative feasible decisions'),
        ('matthiesen','Matthiesen et al.','Continuous interference optimization','Mixed-monotonic branch and bound','Global enclosures at the search tolerance','Pairwise boxes combined with a matching relaxation'),
        ('dinitz','Dinitz et al.','Weighted bipartite matching','Predicted duals and feasibility repair','Exact matching after repair','General-graph pairing with continuous rate scores'),
        ('lei','Lei et al.','Regression with exchangeable examples','Split-conformal prediction','Finite-sample marginal coverage','Policy-specific vector and directional block maxima'),
        ('johnstone','Johnstone and Cox','Robust optimization','Conformal ellipsoidal uncertainty','Coverage-calibrated uncertainty sets','Distinct uncertainty needs of action and oracle'),
    ]
    known={r['key'] for r in rows}
    assert all(r[0] in known for r in comparisons)
    with (ARTICLE/'supplementary/data/closest_studies.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['key','study','system_receiver','optimization_learning','guarantee','relation'])
        writer.writerows(comparisons)
    body='\n'.join(tex(author)+rf'~\cite{{{key}}} & '+' & '.join(tex(x) for x in rest)+r'\\\addlinespace[3pt]'
                   for key,author,*rest in comparisons)
    return r'''\section{Comparison with closely related work}
\label{suppnote:literature}
The closest wireless studies address pairing, frequency allocation or continuous powers. The optimization and inference studies supply matching witnesses, power enclosures or coverage guarantees. Table~\ref{supp:comparison} lists the receiver or model in which each guarantee applies and the step it informs here.
\begin{table}[htbp]\centering\small
\setlength{\tabcolsep}{3pt}
\caption{Ten closely related studies and their relation to the paired scheduling interval.}\label{supp:comparison}
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{.14\linewidth}>{\raggedright\arraybackslash}p{.20\linewidth}>{\raggedright\arraybackslash}p{.21\linewidth}>{\raggedright\arraybackslash}p{.19\linewidth}>{\raggedright\arraybackslash}p{.20\linewidth}@{}}\toprule
Study & System and receiver & Optimization / learning & Guarantee & Relation to this work\\\midrule
''' +body+r'''
\bottomrule\end{tabular}\end{table}
'''


def main():
    selected = select(records(), cited_keys(ARTICLE / "main_nature.tex"))
    (ARTICLE / "references.tex").write_text(bibliography(selected), encoding="utf-8")
    supplementary = ARTICLE / "supplementary"
    supplementary.mkdir(exist_ok=True)
    (supplementary / "note7_literature.tex").write_text(supplement(selected), encoding="utf-8")
    (supplementary / "references.tex").write_text(bibliography(selected), encoding="utf-8")
    columns = ("number", "key", "authors", "year", "title", "venue", "volume", "pages", "doi",
               "url", "evidence_url", "publication_date", *COMPARISON, "topic")
    with (REVISION / "reference_comparison.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, columns, extrasaction="ignore")
        writer.writeheader()
        for number, row in enumerate(selected, 1):
            writer.writerow({"number": number, **row})
    print(f"Generated bibliography and Supplementary Note 1 for {len(selected)} citations.")


if __name__ == "__main__":
    main()
