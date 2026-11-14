"""Walk the post-registration, author-hosted catalog; no raw data redistribution."""
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse,unquote
import json,concurrent.futures
from pathlib import Path
import requests
root='https://renew.rice.edu/datasets/ashu/traces/dist_mu_mimo/'
home=Path(__file__).resolve().parent; out=home/'results';out.mkdir(exist_ok=True)
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        href=dict(attrs).get('href','')
        if tag=='a' and href and not href.startswith(('/','?','..','#','http')):self.links.append(href)
def scan(url):
    r=requests.get(url,timeout=35);r.raise_for_status();h=Links();h.feed(r.text)
    dirs=[]; files=[]
    for link in h.links:
        if link.startswith('ul_') and link.endswith('/') and link!='ul_64x6/':continue
        a=urljoin(url,link)
        if link.endswith('/'):dirs.append(a)
        elif link.lower().endswith('.hdf5'):
            z=requests.head(a,timeout=35);z.raise_for_status();files.append({'url':a,'bytes':int(z.headers.get('content-length',0)),'etag':z.headers.get('etag'),'mode':'HUB' if 'HUB' in a or 'Scenario_1' in a else 'LO','placement':'distributed' if 'Scenario_2' in a else 'colocated','los':'NLoS' if 'NLOS' in a.upper() else 'LoS','rf_chain':Path(unquote(link)).stem[-1]})
    return dirs,files
if __name__=='__main__':
    pending=[root]; rows=[]
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        while pending:
            chunks=list(pool.map(scan,pending));pending=[d for dd,_ in chunks for d in dd];rows+=[f for _,ff in chunks for f in ff]
    assert len(set(r['url'] for r in rows))==len(rows) and {'HUB','LO'}=={r['mode'] for r in rows if r['placement']=='distributed'}
    (out/'rice_inventory.json').write_text(json.dumps(rows,indent=2));print([(r['placement'],r['mode'],r['los'],r['rf_chain'],r['bytes']) for r in rows])

