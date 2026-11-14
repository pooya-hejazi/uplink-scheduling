"""Compile latexdiff changes against the archived preceding submission sources."""
import argparse
from pathlib import Path
import re
import subprocess


def table_versions(old, current):
    """Show structurally changed tables in full instead of merging their column layouts."""
    pattern = r'\\begin\{table\}(?:\[[^]]*\])?.*?\\end\{table\}|\\begingroup\\small\\setlength\{\\tabcolsep\}\{4pt\}.*?\\endgroup'
    def tables(text):
        return {re.search(r'\\label\{([^}]+)\}', block)[1]: block
                for block in re.findall(pattern, text, re.S)
                if re.search(r'\\label\{([^}]+)\}', block)}
    previous, revised = tables(old), tables(current)
    replacements = {}
    for label in previous.keys() & revised.keys():
        a, b = previous[label], revised[label]
        if a == b:
            continue
        token = r'\DIFtableplaceholder{'+label+'}'
        old, current = old.replace(a, token), current.replace(b, token)
        a = re.sub(r'\\label\{[^}]+\}', '', a).replace(r'\caption{', r'\caption*{Previous version. ')
        b = b.replace(r'\caption{', r'\caption{Revised version. ')
        if r'\begin{longtable}' in a:
            # A reordered multipage table needs whole versions and a restored caption counter.
            a = a.replace(r'\arabic{table}B', r'previous.\arabic{table}B')
            a = (r'\begingroup\edef\DIFsavedtable{\number\value{table}}\color{red}'
                 r'\renewcommand{\theHtable}{previous.\arabic{table}}'+a+
                 r'\setcounter{table}{\DIFsavedtable}\endgroup')
            b = r'\begingroup\color{blue}'+b+r'\endgroup'
        a = re.sub(r'(\\begin\{table\})(?:\[[^]]*\])?', lambda m: m[1]+'[p]'+r'\color{red}', a)
        b = re.sub(r'(\\begin\{table\})(?:\[[^]]*\])?', lambda m: m[1]+'[p]'+r'\color{blue}', b)
        replacements[token] = a+'\n'+b
    return old, current, replacements


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submission', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--perl', default='perl')
    parser.add_argument('--latexdiff', required=True)
    parser.add_argument('--tectonic', required=True)
    parser.add_argument('--only-cached', action='store_true')
    args = parser.parse_args()
    submission = args.submission.resolve()
    baseline = submission/'paper/marked_changes'
    for directory, current, previous, name in [
        ('paper', 'main.tex', 'previous_main.tex', 'main_diff'),
        ('supplementary_materials', 'Supplementary_Information.tex', 'previous_Supplementary_Information.tex', 'Supplementary_Information_diff')]:
        target = submission/directory
        old = (baseline/previous).read_text(encoding='utf-8')
        current_text = (target/current).read_text(encoding='utf-8')
        replacements = {}
        if directory == 'paper':
            for stem in ('fig4_scaling', 'fig5_phase', 'fig6_hardware'):
                previous_figure = baseline/'previous_figures'/(stem+'.pdf')
                if previous_figure.read_bytes() != (target/'figures'/(stem+'.pdf')).read_bytes():
                    old = old.replace('figures/'+stem+'.pdf', 'marked_changes/previous_figures/'+stem+'.pdf')
        else:
            old, current_text, replacements = table_versions(old, current_text)
        old_path = baseline/('diff_input_'+previous)
        old_path.write_text(old, encoding='utf-8')
        current_path = baseline/('diff_input_current_'+current)
        current_path.write_text(current_text, encoding='utf-8')
        # Graphic-state assignments before a multicolumn break TeX alignment in the supplement.
        graphics = 'both' if directory == 'paper' else 'none'
        command = [args.perl, args.latexdiff, '--encoding=utf8', '--math-markup=whole', '--append-textcmd=abstract',
                   '--graphics-markup='+graphics, str(old_path), str(current_path)]
        result = subprocess.run(command, capture_output=True, check=True)
        assert b'DIFadd' in result.stdout and b'DIFdel' in result.stdout
        marked = result.stdout.decode('utf-8').replace('\r\n', '\n')
        if directory == 'paper':
            a = old.split(r'\abstract{', 1)[1].split(r'\maketitle', 1)[0]
            b = current_text.split(r'\abstract{', 1)[1].split(r'\maketitle', 1)[0]
            if a != b:
                assert 'DIFadd' in marked.split(r'\abstract{', 1)[1].split(r'\maketitle', 1)[0]
        for token, versions in replacements.items():
            marked = re.sub(r'%DIFDELCMD[^\n]*'+re.escape(token)+r'[^\n]*', '', marked)
            assert marked.count(token) == 1, token
            marked = marked.replace(token, versions)
        assert r'\DIFtableplaceholder' not in marked
        (target/(name+'.tex')).write_text(marked, encoding='utf-8')
        (target/(name+'_latexdiff.log')).write_bytes(result.stderr)
        subprocess.run([args.tectonic, *(['--only-cached'] if args.only_cached else []),
                        '--keep-logs', name+'.tex'], cwd=target, check=True)
        print('Compiled', name+'.pdf')


if __name__ == '__main__':
    main()
