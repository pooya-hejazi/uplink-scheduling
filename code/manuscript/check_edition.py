"""Bind manuscript figures, compact source data and core claims to the independently issued record."""
from pathlib import Path
import argparse,csv,hashlib,math,re,json
from collections import Counter, defaultdict
from datetime import date
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from statistics import median
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image,ImageDraw,ImageChops
from revision.build_references import tex as escape_reference
root=Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--article-pdf", type=Path, default=root/"main_nature.pdf")
parser.add_argument("--supplement-pdf", type=Path, default=root/"Supplementary_Information.pdf")
parser.add_argument("--output-directory", type=Path, default=root.parent/"output"/"qa_gate4")
args = parser.parse_args()
out = args.output_directory
out.mkdir(parents=True, exist_ok=True)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def rd(name):return rows(root/'source_data'/(name+'.csv'))
def close(x,y,t=2e-12):assert math.isclose(float(x),float(y),abs_tol=t,rel_tol=t),(x,y)

def article_source(path, include_references=False):
    """Expand input files, preserving bibliography entries when requested."""
    source = re.sub(r'(?<!\\)%[^\n]*', '', path.read_text(encoding='utf-8'))
    def expand(match):
        child = path.parent / Path(match[1]).with_suffix('.tex')
        if not child.exists(): child = root/'supplementary'/Path(match[1]).with_suffix('.tex')
        return '' if child == root/'references.tex' and not include_references else article_source(child, include_references)
    return re.sub(r'\\input\s*\{([^}]+)\}', expand, source)

def paragraphs(tex, section):
    body = tex.split(r'\section*{' + section + '}', 1)[1].split(r'\section*{', 1)[0]
    return [p for p in re.split(r'\n\s*\n', body.strip()) if p.strip()]

def check_references(tex):
    assert not re.search(r'(?<!~)\\cite\b', tex), 'Use a non-breaking space before each citation'
    keys = list(dict.fromkeys(key.strip() for group in re.findall(r'\\cite\{([^}]+)\}', tex)
                              for key in group.split(',')))
    bibliography = (root/'references.tex').read_text(encoding='utf-8')
    assert re.findall(r'\\bibitem\{([^}]+)\}', bibliography) == keys
    assert 50 <= len(keys) <= 55
    table = rows(root/'revision'/'reference_comparison.csv')
    assert [r['key'] for r in table] == keys
    assert [int(r['number']) for r in table] == list(range(1, len(keys)+1))
    for column in ('title', 'url', 'doi'):
        values = [r[column].strip().casefold() for r in table if r[column].strip()]
        assert len(values) == len(set(values)), ('duplicate reference', column)
    venues = Counter()
    for row in table:
        assert all(row[field].strip() for field in ('contribution', 'strength', 'limitation', 'distance'))
        assert all(urlparse(row[field]).scheme == 'https' for field in ('url', 'evidence_url'))
        source = urlparse(row['evidence_url'])
        if row['publication_date'] or source.hostname in ('nature.com', 'www.nature.com'):
            assert date.fromisoformat(row['publication_date']).year == int(row['year']) == 2026
            assert source.hostname in ('nature.com', 'www.nature.com') and source.path == '/articles/'+row['doi'].split('/',1)[1]
            venues[row['venue']] += 1
    assert sum(venues.values()) == 7 and venues['Nature Communications'] >= 6, venues
    return table, dict(venues)

def check_ray_geometry(decisions):
    geometry = rows(root/'revision'/'ray_geometry.csv')
    native = {(r['family'],int(r['block']),int(r['k'])): r for r in decisions if r['method']=='det'}
    cells = defaultdict(list)
    seen = set()
    for r in geometry:
        family, block, k = r['family'], int(r['block']), int(r['k'])
        key = family, block, k
        assert key not in seen and k in (32,64)
        seen.add(key)
        assert 0 <= float(r['mean_pair_overlap']) <= 1 and 1 <= float(r['mean_effective_rank']) <= k
        assert 0 <= float(r['tone_conflict']) <= float(r['gap']) + 2e-12
        if family in ('O1_60','asu_campus1'):
            assert 0 <= int(float(r['n_los'])) <= k and float(r['median_path_count']) >= 1
            for field in ('median_strongest_power_fraction','median_direct_power_fraction','median_direction_resultant'):
                assert 0 <= float(r[field]) <= 1+1e-12
            cells[family,k].append(float(r['gap']))
        else:
            close(r['gap'], native[key]['G'])
    expected = set(native) | {(f,b,k) for f in ('O1_60','asu_campus1') for b in range(64) for k in (32,64)}
    assert seen == expected
    audited = rows(root/'audit/results/deepmimo_cells.csv')
    for r in audited:
        if float(r['db']) == 10 and int(r['k']) in (32,64):
            close(median(cells[r['family'],int(r['k'])]),r['median_gap'])
    return len(geometry)

def check_reviewer_data(decisions):
    data=root/'revision/reviewer_data'
    absolute=rows(data/'absolute_rates.csv')
    assert len(absolute)==10752
    by_topology=defaultdict(list)
    for r in absolute: by_topology[r['family'],r['block'],r['k']].append(r)
    assert len(by_topology)==1536
    for group in by_topology.values():
        assert len(group)==len({r['method'] for r in group})==7
        best=min(float(r['U']) for r in group)
        for r in group:
            close(r['U_best'],best)
            assert float(r['L'])<=best+1e-10
            close(r['retention_pct'],100*float(r['L'])/best)
    decomposition=rows(data/'gap_decomposition.csv')
    assert Counter(int(r['k']) for r in decomposition)=={k:512 for k in (2,4,6,8,16)}
    for r in decomposition:
        lo,hi,L,U=map(float,(r['V_lo'],r['V_hi'],r['L'],r['U']))
        assert L<=lo+1e-10 and lo<=hi+1e-10 and hi<=U+1e-10
        close(r['slack_lo'],U-hi);close(r['slack_hi'],U-lo)
        close(r['suboptimality_lo'],lo-L);close(r['suboptimality_hi'],hi-L)
    calls=rows(data/'compute_calls.csv');assert len(calls)==9216
    assert len({tuple(r[k] for k in ('family','block','k','rep','method')) for r in calls})==9216
    baseline={(r['family'],r['block'],r['k']):r for r in decisions if r['method']=='det'}
    computed=rows(data/'compute_blocks.csv');assert len(computed)==3072
    for r in computed:
        if r['method']=='det':close(r['G'],baseline[r['family'],r['block'],r['k']]['G'])
        assert int(r['iterations'])==({32:7,64:6}[int(r['k'])]+(0 if r['method']=='det' else 3))
    sweep=rows(data/'refinement_sweep.csv')
    assert Counter(int(r['budget']) for r in sweep)=={b:64 for b in (32,128,512,7936)}
    assert all(r['budget']==r['refined'] for r in sweep)
    hardware={}
    for mode,n in [('HUB',1870),('LO',1769)]:
        records=rows(data/f'hardware_calibration_{mode}.csv')
        assert len(records)==n and len({r['frame'] for r in records})==n
        assert [int(r['frame']) for r in records]==sorted(int(r['frame']) for r in records)
        assert all(r['split']==('calibration' if i<256 else 'test') for i,r in enumerate(records))
        qf=math.nextafter(sorted(float(r['F_score']) for r in records[:256])[250],math.inf)
        qp=math.nextafter(sorted(float(r['P_score']) for r in records[:256])[250],math.inf)
        for r in records:
            close(r['qF'],qf);close(r['qP'],qp)
            close(r['equal_power_reference_gap'],float(r['early_U'])-float(r['equal_power_optimum']))
            if r['split']=='test':
                later,lp,lf,uf=map(float,(r['later_rate'],r['LP'],r['LF'],r['U_F']))
                assert int(float(r['covered_floor']))==int(later>=lp-1e-10)
                assert int(float(r['covered_interval']))==int(max(lp,lf)-1e-10<=later<=uf+1e-10)
                close(r['projected_width'],uf-lp)
                assert int(float(r['joint']))==int(float(r['F_score'])<=qf and float(r['P_score'])<=qp)
                if float(r['P_score'])<=qp: assert later>=lp-1e-10
                if float(r['F_score'])<=qf: assert lf-1e-10<=later<=uf+1e-10
        report=json.loads((data/f'hardware_calibration_{mode}.json').read_text())
        assert report['n_calibration']==256 and report['n_test']==n-256
        close(report['floor_coverage'],sum(float(r['covered_floor']) for r in records[256:])/(n-256))
        close(report['joint_score_coverage'],sum(float(r['joint']) for r in records[256:])/(n-256))
        hardware[mode]=report
    return hardware

def render(name):
    p = {"main_nature": args.article_pdf, "Supplementary_Information": args.supplement_pdf}.get(name, root/(name+".pdf"))
    doc=pdfium.PdfDocument(str(p));n=len(doc);assert n>=1
    im=Image.new('RGB',(256*min(n,4),340*((n+3)//4)),'#e1e8e9');dr=ImageDraw.Draw(im);text=[]
    for i in range(n):
        pg=doc[i];tx=pg.get_textpage().get_text_range();assert tx.strip(),(p,i);text.append(tx);img=pg.render(scale=.395).to_pil().convert('RGB')
        assert ImageChops.difference(img,Image.new('RGB',img.size,'white')).getbbox() is not None,(p,i)
        im.paste(img,((i%4)*256+7,(i//4)*340+4));dr.text(((i%4)*256+10,(i//4)*340+319),str(i+1),fill='black')
    im.save(out/(name+'_pages.png'));return n,'\n'.join(text)
def main():
    tex=article_source(root/'main_nature.tex')
    calls=re.findall(r'\\fig\{(fig\d_[^}]+)\}',tex);assert len(calls)==len(set(calls))==6
    result=tex.split(r'\section*{Results}')[1].split(r'\section*{Discussion}')[0];assert result.count(r'\subsection*')==6
    intro=tex.split(r'\section*{Introduction}')[1].split(r'\section*{Results}')[0].strip()
    assert paragraphs(tex,'Introduction') and paragraphs(tex,'Discussion')
    assert r'\[' not in intro and 'equation}' not in intro
    declarations = ('Acknowledgements','Author contributions','Competing interests')
    headings = re.findall(r'\\section\*\{([^}]+)\}',tex)
    assert [v for v in headings if v in declarations] == list(declarations)
    abstract=tex.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0].strip()
    assert 'Here we ' in abstract and 120<=len(abstract.split())<=150
    references, nature_venues = check_references(tex)
    assert not any(t in tex for t in ['TODO','TBD','PLACEHOLDER'])
    audit=root/'audit';j=json.loads((audit/'Gate_4_Audit_Certificate.json').read_text());assert j['disposition']=='PASS_WITH_SCOPE_LIMITS'
    for line in (audit/'CERTIFICATE_SHA256SUMS').read_text().splitlines():
        digest, filename = line.split(None,1)
        assert h(audit/filename) == digest, filename
    receipts=json.loads((audit/'results/receipt_summary.json').read_text());sample=json.loads((audit/'results/sample_dp_summary.json').read_text());assert (receipts['distinct'],receipts['timing_links'],receipts['violations'],sample['exact_tick_mismatches'])==(8192,12288,0,0)
    decisions=rd('fig4_decisions');methods=rd('fig4_methods');primary=rows(audit/'results/primary_table.csv');assert len(decisions)==4096
    geometry_rows = check_ray_geometry(decisions)
    reviewer_hardware = check_reviewer_data(decisions)
    paired = rows(audit/'results/paired_transitions.csv')
    assert [(int(r['k']),float(r['exact_mcnemar_two_sided'])) for r in paired] == [(32,.03125),(64,.0625)]
    for row,ar in [(r,next(x for x in primary if (x['k'],x['method'])==(r['k'],r['method']))) for r in methods]:
        d=[x for x in decisions if (x['k'],x['method'])==(row['k'],row['method'])];assert len(d)==512 and sum(int(x['ok']) for x in d)==int(ar['passed'])==int(row['hits']);close(median(float(x['G']) for x in d),ar['median_G']);close(row['median_ms'],ar['median_ms'])
    for r in rd('fig1_ledger'):close(sum(float(r['term'+str(i)]) for i in range(1,5)),r['G'])
    q=rd('fig3_uncertainty');assert [int(r['useful']) for r in q if int(r['db'])==10]==[128,128,83,127]
    hwr=rd('fig6_capture_counts')
    for r in hwr:
        d=rd('fig6_'+r['mode']);assert len(d)==int(r['eligible']);assert sum(float(x['G'])<=.1 and float(x['ms'])<=250 for x in d)==int(r['success']);close(median(float(x['later_LTS_fixed_action_rate'])-float(x['L_proxy']) for x in d),r['median_later_change'])
    ledger=rd('fig2_label_loss');assert len(ledger)==512 and all(float(x['loss'])<=float(x['posterior'])+1e-12<=float(x['prior'])+2e-12 for x in ledger)
    for f in calls:
        p=root/'figures'/(f+'.pdf');assert len(PdfReader(p).pages)==1
        assert ET.parse(root/'figures'/(f+'.svg')).getroot().tag.endswith('svg')
    def labels(figure):
        svg = ET.parse(root/'figures'/(figure+'.svg'))
        return [' '.join(''.join(e.itertext()).split()) for e in svg.findall('.//{*}text')]
    assert all(letter in labels(calls[3]) for letter in 'abcd')
    assert all(letter in labels(calls[5]) for letter in 'abcd')
    assert any(''.join(s.split())=='6.02×10−7' for s in labels(calls[0]))
    n,t=render('main_nature');ncert,tcert=render('Gate_4_Audit_Certificate');nsupp,tsupp=render('Supplementary_Information')
    for name, pdftext in [('main_nature',t), ('Supplementary_Information',tsupp)]:
        assert '??' not in pdftext and not re.search(r'\[\s*\?\s*]',pdftext), name
        log_path = root/(name+'.log')
        if log_path.exists():
            log = log_path.read_text(encoding='utf-8',errors='replace')
            assert not re.search(r'undefined (?:references|citations)|(?:Citation|Reference) .+ undefined',log,re.I), name
    assert 20 <= nsupp <= 45, nsupp
    supplement = article_source(root/'Supplementary_Information.tex', include_references=True)
    assert len(re.findall(r'\\section\{', supplement)) == 7
    assert re.findall(r'\\bibitem\{([^}]+)\}', supplement) == [r['key'] for r in references]
    assert len(re.findall(r'\\label\{supp:(?:table\d+|comparison|rates|compute|decomposition|refinement|hardware_calibration)\}', supplement)) == 16
    assert len(re.findall(r'\\label\{supp:fig\d+\}', supplement)) == 8
    for index in range(1, 17):
        assert re.search(r'Supplementary\s+Table\s+'+str(index)+r'\b', tsupp), index
    for index in range(1, 9):
        assert re.search(r'Supplementary\s+Figure\s+'+str(index)+r'\b', tsupp), index
        assert len(PdfReader(root/'supplementary'/'figures'/f'sfig{index}.pdf').pages) == 1
    assert '37/84' in tsupp.replace(' ', '') or r'\frac{37}{84}' in supplement
    extended_geometry = rows(root/'supplementary/data/physics_geometry.csv')
    assert len(extended_geometry) == 384
    for row in extended_geometry:
        close(sum(float(row[f'T{i}']) for i in range(1, 5)), row['gap'])
    selectivity = rows(root/'supplementary/data/sim_fixed_policy_selectivity.csv')
    assert len(selectivity) == 1152
    assert round(min(float(r['total']) for r in selectivity), 4) == 0.0359
    assert round(max(float(r['total']) for r in selectivity), 4) == 2.3430
    assert round(max(float(r['dc'])/float(r['total']) for r in selectivity), 3) == 0.377
    assert sum(float(r['term2']) > float(r['total'])/2 for r in selectivity) == 980
    expected_ranks = {('O1_60',32):1.0218, ('O1_60',64):1.0230,
                      ('asu_campus1',32):2.6004, ('asu_campus1',64):2.6444}
    for (scene, users), expected_rank in expected_ranks.items():
        ranks = [float(r['rank']) for r in extended_geometry if r['scene']==scene and int(r['k'])==users]
        assert len(ranks)==64 and round(median(ranks),4)==expected_rank


    for r in references:
        assert r['url'] in supplement and escape_reference(r['title']) in supplement, r['key']
    assert len(rows(root/'supplementary/data/closest_studies.csv')) == 10
    assert all(v in t for v in ('0.03125','0.0625'))
    assert all(re.search(r'(?:Figure|Fig\.)\s*'+str(i)+r'\s*[.:]?\s+[A-Z]',t) for i in range(1,7));assert 'Data availability' in t and 'Code availability' in t and '8,192' in t and '0.0625' in t
    assert '8,192' in tcert and '12,288' in tcert and '0.0625' in tcert and '0.03125' in tcert
    intrograph=Image.new('RGB',(2*550,3*413),'#e1e8e9')
    for i,f in enumerate(calls):
        doc=pdfium.PdfDocument(str(root/'figures'/(f+'.pdf')));img=doc[0].render(scale=1.32).to_pil().convert('RGB');img.thumbnail((540,403));intrograph.paste(img,(5+550*(i%2),5+413*(i//2)))
    intrograph.save(out/'six_final_figures.png')
    info={'article_pages':n,'certificate_pages':ncert,'abstract_whitespace_words':len(abstract.split()),'introduction_paragraphs':len(paragraphs(tex,'Introduction')),'results_subsections':6,'figures':{f:h(root/'figures'/(f+'.pdf')) for f in calls},'article_sha256':h(args.article_pdf),'audit_certificate_json_sha256':h(audit/'Gate_4_Audit_Certificate.json'),'primary_counts':{str(k):{r['method']:int(r['hits']) for r in methods if int(r['k'])==k} for k in (32,64)},'figure_source_rows':{'primary':len(decisions),'structural':len(ledger),'uncertainty_cells':len(q)},'compared_to_independent_audit':True,'package_includes_raw_rice':False}
    info.update(supplement_pages=nsupp,supplement_sha256=h(args.supplement_pdf),supplementary_notes=7,supplementary_figures=8,supplementary_tables=16,
                references=len(references),nature_2026_by_venue=nature_venues,discussion_paragraphs=len(paragraphs(tex,'Discussion')),
                ray_geometry_rows=geometry_rows,exact_paired_two_sided_p={r['k']:r['exact_mcnemar_two_sided'] for r in paired})
    info['reviewer_hardware']=reviewer_hardware
    (root/'article_claims.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2))
if __name__=='__main__':main()

