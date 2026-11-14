"""Assemble the single-file submission from the editable article and its inputs."""
import re
from pathlib import Path


def expand(path, parents=()):
    if path in parents:
        raise ValueError(f"Cyclic TeX input: {path}")
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        match = re.fullmatch(r"\s*\\input\{([^}]+)\}\s*(?:%[^\n]*)?\n?", line)
        if match:
            child = path.parent / match[1]
            if not child.suffix:
                child = child.with_suffix(".tex")
            included = expand(child.resolve(), (*parents, path))
            lines.append(included if included.endswith("\n") else included + "\n")
        else:
            lines.append(line)
    return "".join(lines)


def build(directory=None):
    directory = Path(directory or Path(__file__).resolve().parent).resolve()
    source = expand(directory / "main_nature.tex")
    if re.search(r"^[^%\n]*\\input\s*\{", source, re.MULTILINE) or r"\begin{thebibliography}" not in source:
        raise ValueError("Incomplete article expansion or missing embedded bibliography")
    output = directory / "main_nature_submission.tex"
    output.write_text(source, encoding="utf-8")
    return output


def main():
    return build()


if __name__ == "__main__":
    main()
