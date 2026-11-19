"""Rebuild the single-file Springer Nature article from the editorial sources."""
import argparse
import re
import runpy
import shutil
import subprocess
import zipfile
from pathlib import Path


def refresh_submission(source_directory):
    """Rebuild the editorial alias using its canonical expansion implementation."""
    builder = runpy.run_path(str(source_directory / "build_submission.py"))
    return builder["build"](source_directory)


def expand(path, parents=()):
    if path in parents:
        raise ValueError(f"Cyclic input at {path}")
    text = path.read_text(encoding="utf-8")
    def include(match):
        child = path.parent / match[1]
        if not child.suffix:
            child = child.with_suffix(".tex")
        return expand(child.resolve(), (*parents, path))
    return re.sub(r"(?m)^\\input\{([^}]+)\}.*$", include, text)


def figures(text):
    items = []
    while (start := text.find(r"\fig{")) >= 0:
        pos = start + 4
        args = []
        for _ in range(4):
            assert text[pos] == "{"
            begin = pos + 1
            depth = 1
            pos += 1
            while depth:
                if text[pos] in "{}" and text[pos - 1] != "\\":
                    depth += 1 if text[pos] == "{" else -1
                pos += 1
            args.append(text[begin:pos - 1])
        items.append(args)
        text = text[:start] + text[pos:]
    assert len(items) == 6 and len({item[3] for item in items}) == 6
    return text, items


def inline_macros(text):
    replacements = {"dc": r"\Delta_{\mathrm{conflict}}", "fix": r"{R_{\mathrm{fix}}}",
                    "rank": r"\operatorname{rank}"}
    text = re.sub(r"\\(dc|fix|rank)\b", lambda match: replacements[match[1]], text)
    while (start := text.find(r"\pos{")) >= 0:
        begin = start + 5
        pos, depth = begin, 1
        while depth:
            if text[pos] in "{}" and text[pos - 1] != "\\":
                depth += 1 if text[pos] == "{" else -1
            pos += 1
        text = text[:start] + r"\left[" + text[begin:pos - 1] + r"\right]_{+}" + text[pos:]
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "reproduction" / "Gate_4")
    parser.add_argument("--tectonic", help="Compile main.tex with this executable after assembling it.")
    parser.add_argument("--only-cached", action="store_true", help="Compile without fetching any TeX resources.")
    args = parser.parse_args()
    paper = Path(__file__).resolve().parents[2] / "paper"
    source = refresh_submission(args.source).read_text(encoding="utf-8")
    title = re.search(r"pdftitle=\{([^}]+)\}", source)[1]
    abstract = source.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0].strip()
    body = source.split(r"\end{abstract}", 1)[1].split(r"\end{document}", 1)[0]
    body, items = figures(body)
    body = body.replace(r"\section*{Introduction}", "").replace(r"\section*{Methods}", r"\section*{Online Methods}")
    header = r"""\documentclass[lineno,pdflatex,sn-nature]{sn-jnl}
\usepackage{graphicx,amsmath,amssymb,booktabs,xcolor}
\setcitestyle{super,comma,open={},close={}}
\renewcommand{\bibnumfmt}[1]{#1.}
\urlstyle{same}
\setlength{\emergencystretch}{2em}
\raggedbottom
\hypersetup{hidelinks,pdftitle={TITLE},pdfauthor={Pooya Hejazi and Masoud Sabaei}}
\begin{document}
\title{TITLE}
\author[1]{\fnm{Pooya} \sur{Hejazi}}
\author*[1]{\fnm{Masoud} \sur{Sabaei}}\email{sabaei@aut.ac.ir}
\affil[1]{\orgdiv{Department of Computer Engineering}, \orgname{Amirkabir University of Technology}, \orgaddress{\city{Tehran}, \country{Iran}}}
\abstract{ABSTRACT}
\maketitle
""".replace("TITLE", title).replace("ABSTRACT", abstract)
    # Figures and their legends follow declarations, in order of first mention.
    end = []
    for filename, caption, legend, label in items:
        end.append(r"\clearpage\begin{figure}[p]\centering" + "\n"
                   + rf"\includegraphics[width=\linewidth]{{figures/{filename}.pdf}}" + "\n"
                   + rf"\caption{{\textbf{{{caption}}} {legend}}}\label{{{label}}}" + "\n"
                   + r"\end{figure}")
    final = inline_macros(header + body + "\n" + "\n".join(end) + "\n\\end{document}\n")
    assert r"\input{" not in final and r"\begin{thebibliography}" in final
    assert final.count(r"\begin{figure}") == 6
    paper.mkdir(parents=True, exist_ok=True)
    (paper / "main.tex").write_text(final, encoding="utf-8")
    (paper / "figures").mkdir(exist_ok=True)
    for filename, *_ in items:
        shutil.copy2(args.source / "figures" / (filename + ".pdf"), paper / "figures" / (filename + ".pdf"))
    if args.tectonic:
        subprocess.run([args.tectonic, *(["--only-cached"] if args.only_cached else []), "--keep-logs", "main.tex"], cwd=paper, check=True)
    members = [paper / name for name in ("main.tex", "sn-jnl.cls", "sn-nature.bst")]
    members.extend(paper / "figures" / (filename + ".pdf") for filename, *_ in items)
    with zipfile.ZipFile(paper / "Manuscript_Source.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member in members:
            archive.write(member, member.relative_to(paper))
    print(f"Assembled {paper / 'main.tex'} with {len(items)} figures.")


if __name__ == "__main__":
    main()
