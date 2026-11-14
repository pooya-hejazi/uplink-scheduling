"""Render the measured report as PDF via a temporary local HTML file; no outbound page requests."""
import subprocess,os,tempfile,shutil
from pathlib import Path
from lxml import html,etree
home=Path(__file__).resolve().parent;root=home.parent;out=root/'output/pdf/Gate_2_Report.pdf'
bundle=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies')
css="""@page{size:A4;margin:16mm 16mm 16mm}*{box-sizing:border-box}
body{font:10.2pt/1.39 'Segoe UI',Arial,sans-serif;color:#162d3b;margin:0}h1{font:700 30pt/1.07 'Segoe UI',sans-serif;letter-spacing:-.7pt;color:#133447;margin:.1cm 0 .45cm}h2{font:650 18pt/1.2 'Segoe UI',sans-serif;color:#125e64;margin:0 0 3.8mm;border-bottom:1.2pt solid #a1cad0;padding-bottom:2.5mm;break-after:avoid}h3{break-after:avoid}h2:not(:first-child){break-before:page}p{margin:2.4mm 0 3mm}p.meta{color:#287478;font-weight:650;text-transform:uppercase;letter-spacing:.6pt;font-size:9pt}p.lead{border-left:3pt solid #246e73;background:#edf6f5;padding:4mm;font-size:12pt;line-height:1.45}a{color:#175968}table{border-collapse:collapse;width:100%;margin:2.8mm 0 4mm;font-size:9.1pt}tr{break-inside:avoid}th,td{border-bottom:.45pt solid #cad9dd;padding:1.5mm 1.7mm;text-align:left}thead{display:table-header-group;background:#dceeee;color:#173c46}tbody tr:nth-child(even){background:#f4f8f9}figure{margin:2mm 0}figcaption{font-size:8.8pt;color:#506370}img{max-width:100%;max-height:65mm}code{font:8.5pt Consolas,monospace;overflow-wrap:anywhere}ul{padding-left:5mm}strong{font-weight:650}"""
js="""const {chromium}=require(process.argv[2]+'/node/node_modules/playwright');const {pathToFileURL}=require('url');(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-background-networking','--disable-component-update','--no-first-run']});try{const p=await b.newPage();await p.route(/^https?:/,r=>r.abort());await p.goto(pathToFileURL(process.argv[3]).href);await p.evaluate(()=>document.fonts.ready);await p.pdf({path:process.argv[4],format:'A4',preferCSSPageSize:true,printBackground:true,displayHeaderFooter:true,headerTemplate:'<div></div>',footerTemplate:'<div style="font:8px Arial;color:#53717e;width:100%;margin:0 60px;border-top:1px solid #bdd3d5;padding-top:5px">GATE 2  /  PILOT EVIDENCE <span style="float:right" class="pageNumber"></span></div>'});}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1})"""
with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp);part=t/'body.html';subprocess.run([shutil.which('pandoc') or 'C:/ProgramData/anaconda3/Scripts/pandoc.exe',str(home/'REPORT.md'),'-t','html5','--mathml','-o',str(part)],check=True)
    tree=html.fragment_fromstring(part.read_text(encoding='utf8'),create_parent='main')
    first=tree.find('p');first.set('class','meta');tree.remove(first);tree.insert(0,first)
    tree.find('h2').set('style','break-before:auto;margin-top:9mm')
    rice=next(h for h in tree.findall('h2') if h.text_content().startswith('5.'))
    node=rice.getnext()
    while node is not None and node.tag!='h2':
        node.set('style','font-size:9.25pt;line-height:1.27;margin-top:2mm;margin-bottom:2mm')
        node=node.getnext()
    for p in tree.xpath('//p'):
        if p.text_content().startswith('Disposition:'):p.set('class','lead')
    for img in tree.xpath('//img'):img.set('src',(home/img.get('src')).as_uri())
    for a in tree.xpath('//a[@href]'):
        u=a.get('href')
        if not u.startswith(('http:','https:','#')):a.set('href','../../Gate_2/'+u)
    htmlfile=t/'report.html';htmlfile.write_text('<!doctype html><html><head><meta charset="utf-8"><base href="'+out.as_uri()+'"><title>Gate 2 pilot evidence</title><style>'+css+'</style></head><body>'+etree.tostring(tree,encoding='unicode',method='html')+'</body></html>',encoding='utf8')
    script=t/'render.cjs';script.write_text(js)
    subprocess.run([str(bundle/'node/bin/node.exe'),str(script),str(bundle),str(htmlfile),str(out)],check=True)
print(out)

