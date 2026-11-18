"""Locate response anchors against the line rulers printed in the delivered PDF."""
from pathlib import Path
import argparse,hashlib,json,logging,re,unicodedata
import pdfplumber

logging.getLogger('fontTools').setLevel(logging.ERROR)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--submission',type=Path,default=Path(__file__).resolve().parents[2])
args=parser.parse_args()
PAPER=args.submission/'paper'
PDF=PAPER/'main.pdf'
data=json.loads((PAPER/'response_content.json').read_text(encoding='utf-8'))

def norm(value):
    return ''.join(c.lower() for c in unicodedata.normalize('NFKD',value) if c.isalnum())

# shortcut: ruler positions follow the supplied sn-jnl class; update them if the class layout changes.
words=[];text='';offsets=[];rulers={}
with pdfplumber.open(PDF) as doc:
    for page_no,page in enumerate(doc.pages,1):
        extracted=page.extract_words(x_tolerance=1.5,y_tolerance=3)
        # Extract the narrow ruler independently so figure labels cannot split its digits.
        ruler_x = 487.57 if page_no % 2 else 100.68
        strip = page.crop((ruler_x-.3, 67, ruler_x+22, 627))
        rulers[page_no] = [w for w in strip.extract_words(x_tolerance=1.5, y_tolerance=1)
                           if w['text'].isdigit() and abs(w['x0']-ruler_x)<.2]
        first = 46*(page_no-1)+1
        assert [int(w['text']) for w in rulers[page_no]] == list(range(first,first+46)), page_no
        def margin(w):
            return w['text'].isdigit() and ruler_x-.3 <= w['x0'] < ruler_x+22
        for w in extracted:
            if margin(w) or not 60<w['top']<650:continue
            content=norm(w['text'])
            offsets.extend([len(words)]*len(content));text+=content
            words.append(dict(w,page=page_no))

def locate(begin,end=None):
    start=text.find(norm(begin));assert start>=0,begin
    end_start = start if end is None else text.find(norm(end), start)
    assert end_start >= start, (begin, end)
    finish = end_start + len(norm(end or begin))
    assert finish>start,(begin,end)
    a,b=words[offsets[start]],words[offsets[finish-1]]
    low=[w for w in rulers[a['page']] if w['top']<=a['top']+1.6]
    high=[w for w in rulers[b['page']] if w['top']>=b['top']-1.6]
    return dict(page_start=a['page'],page_end=b['page'],line_start=int((low[-1] if low else rulers[a['page']][0])['text']),
                line_end=int((high[0] if high else rulers[b['page']][-1])['text']),anchor_start=begin,anchor_end=end or begin)

anchors={key:(r['anchor_start'],r['anchor_end']) for key,r in data['locations']['locations'].items()}
locations={key:locate(*value) for key,value in anchors.items()}
out=dict(pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),locations=locations,
         convention='Inclusive printed margin-ruler lines bracketing the identified text; not LaTeX source lines.')
(PAPER/'response_locations.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
data['locations']=out
(PAPER/'response_content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
for key,row in locations.items():print(key,row['page_start'],row['page_end'],row['line_start'],row['line_end'])
