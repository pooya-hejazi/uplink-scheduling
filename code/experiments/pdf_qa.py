from pathlib import Path
import sys
import pypdfium2 as pdf
from pypdf import PdfReader
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1];path=root/'output/pdf'/f'{sys.argv[1]}_Report.pdf'
p=pdf.PdfDocument(path);text=[x.extract_text() for x in PdfReader(path).pages];assert len(p)==len(text) and min(map(len,text))>90
for v in ('deterministic','512' if sys.argv[1]=='Gate_3' else '95/96','time'):assert v in ' '.join(text)
cols=min(3,len(p));sheet=Image.new('RGB',(cols*254,(len(p)+cols-1)//cols*368),'#dfebec');draw=ImageDraw.Draw(sheet)
for j,page in enumerate(p):
    g=page.render(scale=.7).to_pil().convert('RGB');g.thumbnail((248,345));x=(j%cols)*254;y=(j//cols)*368;sheet.paste(g,(x+3,y+3));draw.text((x+4,y+347),f'Page {j+1}',fill='#245263')
out=path.with_name(sys.argv[1]+'_layout.png');sheet.save(out);print(path,len(p),[len(s) for s in text])

