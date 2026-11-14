"""Build the response from exact referee comments and verified PDF-ruler locations."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path


def tex(value):
    replacements={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_',
                  '{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}',
                  'ᴴ':r'\textsuperscript{H}','₂':r'\textsubscript{2}','₁':r'\textsubscript{1}',
                  '²':r'\textsuperscript{2}','µ':r'\(\mu\)','×':r'\(\times\)','−':r'\(-\)',
                  '…':r'\ldots{}','ρ':r'\(\rho\)','√':r'\(\surd\)','≤':r'\(\leq\)',
                  '⁽':r'\textsuperscript{(}','⁾':r'\textsuperscript{)}','⁰':r'\textsuperscript{0}','¹':r'\textsuperscript{1}'}
    text=''.join(replacements.get(c,c) for c in value)
    text=re.sub(r'\*\*(.+?)\*\*',lambda m:r'\textbf{'+m[1]+'}',text)
    return re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)',lambda m:r'\emph{'+m[1]+'}',text)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--submission',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--tectonic');p.add_argument('--only-cached',action='store_true')
    a=p.parse_args();paper=a.submission/'paper'
    data=json.loads((paper/'response_content.json').read_text(encoding='utf-8'))
    if hashlib.sha256((paper/'main.pdf').read_bytes()).hexdigest()!=data['locations']['pdf_sha256']:
        subprocess.run([sys.executable,str(Path(__file__).with_name('index_pdf_locations.py')),'--submission',str(a.submission)],check=True)
        data=json.loads((paper/'response_content.json').read_text(encoding='utf-8'))
    assert [r['id'] for r in data['records']]==[f'T{i}' for i in range(1,6)]
    md=['# '+data['title'],'**'+data['manuscript']+'**',data['introduction'],
        'Locations below use the printed Article PDF margin ruler, not LaTeX source lines. Supplementary locations refer to its printed page numbers.']
    body=[r'\documentclass[10pt,letterpaper]{article}',r'\usepackage[margin=0.85in]{geometry}',
          r'\usepackage{amsmath,amssymb,longtable,booktabs,array}',r'\usepackage[hidelinks]{hyperref}',
          r'\setlength{\emergencystretch}{3em}',r'\setlength{\parindent}{0pt}',r'\setlength{\parskip}{0.5em}',
          r'\begin{document}',r'\begin{center}\Large\bfseries '+tex(data['title'])+r'\end{center}',
          r'\textbf{'+tex(data['manuscript'])+'}',tex(data['introduction']),tex(md[-1])]
    for row in data['records']:
        where=[]
        for key in row['location_keys']:
            loc=data['locations']['locations'][key]
            pages=str(loc['page_start']) if loc['page_start']==loc['page_end'] else f"{loc['page_start']}–{loc['page_end']}"
            where.append(f"Article pp. {pages}, lines {loc['line_start']:03}–{loc['line_end']:03}")
        if row['supplement']:where.append(row['supplement'])
        location='; '.join(where)
        md.extend(['## '+row['id'],'\n'.join('> '+line if line else '>' for line in row['comment'].splitlines()),'**Response.** '+row['response'],'**Locations.** '+location])
        quoted=re.sub(r'(?m)^(?=\d+\. |\- )',lambda m:r'\par\noindent ',tex(row['comment']))
        body.extend([r'\section*{'+row['id']+'}',r'\begin{quote}\small '+quoted+r'\end{quote}',
                     r'\textbf{Response.} '+tex(row['response']),r'\textbf{Locations.} '+tex(location)])
    verification=paper/'reference_verification.json'
    records=json.loads(verification.read_text(encoding='utf-8'))
    md.extend(['## Additional verification (report Part C)',
               'All nine listed 2026 journal references were checked against publisher-deposited DOI records; reference 28 was checked against the official ETSI report. Titles, volumes, pages/article numbers and years agree. The machine-readable records from 14 November 2026 accompany this response. The noise-scale diagnostic in T1 does not identify a causal mechanism.',
               '| Article reference | DOI or primary source |','|---|---|'])
    body.extend([r'\section*{Additional verification (report Part C)}',tex(md[-3]),r'\begin{longtable}{p{0.20\linewidth}p{0.72\linewidth}}\toprule Article reference & DOI or primary source\\\midrule\endhead'])
    for item in records:
        number,doi=item['number'],item['record']['DOI']
        md.append(f'| {number} | https://doi.org/{doi} |')
        body.append(tex(number)+r' & \url{https://doi.org/'+doi+r'}\\')
    url='https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/19.02.00_60/tr_138901v190200p.pdf'
    md.append('| 28 | [ETSI TR 138 901 V19.2.0, February 2026]('+url+') |')
    body.extend([r'28 & \href{'+url+r'}{ETSI TR 138 901 V19.2.0, February 2026}\\\bottomrule\end{longtable}',
                 tex('The code and Source Data hashes and archive members were checked locally; compiled table layouts were visually inspected. At the authors’ request, archival registration is deferred until acceptance (T3).'),r'\end{document}'])
    (paper/'Response_to_Referees.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
    (paper/'Response_to_Referees.tex').write_text('\n\n'.join(body)+'\n',encoding='utf-8')
    if a.tectonic:
        subprocess.run([a.tectonic,*(['--only-cached'] if a.only_cached else []),'--keep-logs','Response_to_Referees.tex'],cwd=paper,check=True)
    print('Built response to T1–T5 using printed PDF locations.')


if __name__=='__main__':main()
