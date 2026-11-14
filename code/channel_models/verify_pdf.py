"""Render a contact sheet and check text anchors on actual final pages."""
from pathlib import Path
import tempfile
import pypdfium2 as pdf
from PIL import Image,ImageOps,ImageDraw
from pypdf import PdfReader
out=Path(__file__).resolve().parents[1]/'output/pdf';d=Path(tempfile.gettempdir())/'gate2-pdf-qa';d.mkdir(exist_ok=True)
for name,filename in [('report','Gate_2_Report.pdf'),('road','Research_Execution_Roadmap.pdf')]:
    doc=pdf.PdfDocument(out/filename);w,h=218,306
    sheet=Image.new('RGB',((w+8)*min(len(doc),4),(h+20)*((len(doc)+3)//4)),'white');pen=ImageDraw.Draw(sheet)
    text=' '.join(p.extract_text() or '' for p in PdfReader(out/filename).pages)
    if name=='report':assert '46/96' in text and '0.50' in text and '1,000 ms' in text
    for j,page in enumerate(doc):
        im=page.render(scale=.6).to_pil().convert('RGB');im.thumbnail((w,h));x=(j%4)*(w+8);y=(j//4)*(h+20)
        sheet.paste(ImageOps.expand(im,border=1,fill='#bed0cf'),(x,y));pen.text((x+4,y+h+2),str(j+1),fill='black')
    sheet.save(d/(name+'.png'));print(name,len(doc),sum(c.isalnum() for c in text),d/(name+'.png'))

