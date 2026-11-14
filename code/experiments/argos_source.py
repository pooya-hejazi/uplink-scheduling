"""Read Rice Argos HDF5 metadata through validated ranges; never copy IQ into the release."""
from pathlib import Path
import json,hashlib,sys,urllib.parse,requests,h5py,numpy as np
from concurrent.futures import ThreadPoolExecutor
root=Path(__file__).resolve().parent;dest=root/'results/argos'
sys.path.insert(0,str(root.parent/'Gate_2'))
from rice_io import Remote
def sources():
    access=json.loads((dest/'access.json').read_text());d=json.loads((dest/'directory_entries.json').read_text());base='https://'+access['host']+access['returned_collection']
    assert access['status']==200 and access['host'] in ('renew.rice.edu','renew-wireless.org')
    ids=[s for s in sorted(d) if s.startswith('ArgosCSI-8x6-')];assert len(ids)==3
    for s in ids:
        files=[f for f in d[s] if f.endswith('.hdf5')];assert len(files)==1
        yield s.rstrip('/').split('_')[-1],urllib.parse.urljoin(base,s+files[0])
def inspect(pair):
    name,u=pair
    with requests.get(u,headers={'Range':'bytes=0-511','Accept-Encoding':'identity'},timeout=(35,65),stream=True) as rsp:
        rsp.raise_for_status();assert rsp.status_code==206 and rsp.headers['Content-Range'].startswith('bytes 0-511/');nn=int(rsp.headers['Content-Range'].split('/')[-1]);etag=rsp.headers['ETag'];start=rsp.content;assert start[:8]==b'\x89HDF\r\n\x1a\n'
    record=dict(url=u,bytes=nn,etag=etag);rr=Remote(record);meta={}
    def attr(a):
        v=np.asarray(a);vals=v.ravel()[:100].tolist()
        return dict(shape=list(v.shape),dtype=str(v.dtype),head=[(x.decode('utf8','replace') if isinstance(x,bytes) else str(x) if isinstance(x,complex) else x) for x in vals])
    try:
        with h5py.File(rr,'r') as hf:
            def visit(k,o):
                meta[k]=dict(attrs={s:attr(a) for s,a in o.attrs.items() if s!='nodes_description'})
                if isinstance(o,h5py.Dataset):meta[k].update(shape=list(o.shape),dtype=str(o.dtype),chunks=o.chunks,compression=o.compression,offset=o.id.get_offset())
            visit('/',hf);hf.visititems(visit)
    finally:rr.session.close();rr.page.cache_clear()
    data=dict(regime=name,source=record,schema=meta,metadata_range_sha256=rr.chunks)
    (dest/f'{name}_metadata.json').write_text(json.dumps(data,indent=2))
    print(name,nn,etag,[(k,v.get('shape'),v.get('chunks'),list(v['attrs'])[:10]) for k,v in meta.items()],flush=True)
if __name__=='__main__':
    with ThreadPoolExecutor(3) as p:list(p.map(inspect,sources()))

