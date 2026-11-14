# Marked changes

The preceding Article and supplement sources and previous main Figures 4–6 correspond to private repository commit `f7adc44d04b660d07ab3c7faadb4f432e26f5b66`. Their contents were checked against that commit (normalizing CRLF/LF only for TeX). `baseline_manifest.json` records local SHA-256 hashes.

The current `main_diff.pdf` and `Supplementary_Information_diff.pdf` compare that edition with the complete second-round revision and the Nature Computational Science framing. Blue text marks additions and red struck text deletions. Structurally changed supplementary tables show complete previous (red) and revised (blue) versions, preserving column alignment. Main Figures 4–6 show both image versions.

Rebuild from the single `code` directory with `python run.py build-diffs --tectonic PATH_TO_TECTONIC --perl PATH_TO_PERL --latexdiff PATH_TO_LATEXDIFF`. The journal-package equivalent is `supplementary_materials/tools/build_diffs.py`. latexdiff 1.4.0 was used. The baseline files are comparison material, not current manuscript text.
