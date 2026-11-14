"""Verified HTTP range reader for registered, file-level capture access, without storing the 257 GB collection."""
import io,json,hashlib,time,threading
from pathlib import Path
from functools import lru_cache
import requests,h5py,numpy as np
R=Path(__file__).resolve().parent/'results'
class Remote(io.RawIOBase):
    def __init__(self,row):
        self.row=row;self.size=row['bytes'];self.pos=0;self.session=requests.Session();self.chunks={};self.block=2**20
    def seek(self,n,whence=0):self.pos=n if whence==0 else self.pos+n if whence==1 else self.size+n;return self.pos
    def tell(self):return self.pos
    def seekable(self):return True
    def readable(self):return True
    @lru_cache(maxsize=32)
    def page(self,i):
        start=i*self.block;end=min(self.size,start+self.block)-1
        for retry in range(4):
            try:
                with self.session.get(self.row['url'],headers={'Range':f'bytes={start}-{end}','If-Match':self.row['etag'],'Accept-Encoding':'identity'},timeout=(15,50),stream=True) as rr:
                    rr.raise_for_status()
                    if rr.status_code!=206 or rr.headers.get('Content-Range','').lower()!=f'bytes {start}-{end}/{self.size}':raise IOError('server did not honor exact byte range')
                    raw=rr.content
                if len(raw)!=end-start+1:raise IOError('short HTTP range')
                sha=hashlib.sha256(raw).hexdigest()
                if self.chunks.setdefault(i,sha)!=sha:raise IOError('source changed')
                return raw
            except (requests.RequestException,IOError):
                if retry==3:raise
    def readinto(self,b):
        pos=self.pos;n=min(len(b),max(0,self.size-pos));p=0
        while p<n:
            i,off=divmod(pos+p,self.block);v=self.page(i);take=min(n-p,len(v)-off);b[p:p+take]=v[off:off+take];p+=take
        self.pos+=p;return p
def inventory():
    return json.loads((R/'rice_inventory.json').read_text())
def attrs_plain(attrs):
    def convert(v):
        v=np.asarray(v)
        if v.dtype.kind=='S':return v.astype(str).tolist()
        if v.dtype.kind=='c':return str(v)
        return v.tolist()
    return {k:convert(v) for k,v in attrs.items()}
def inspect():
    for row in inventory():
        remote=Remote(row)
        with h5py.File(remote,'r') as f:
            d=f['Data'];a=attrs_plain(d.attrs)
            r=dict(source=row,fields={k:{'shape':v.shape,'chunks':v.chunks,'dtype':str(v.dtype)} for k,v in d.items()},attrs=a)
            key='_'.join(row[k] for k in ('placement','mode','los','rf_chain'));(R/f'rice_meta_{key}.json').write_text(json.dumps(r,indent=2,default=str))
            print(key,r['fields'],[k for k in a if 'SC' in k or 'FFT' in k or 'ANT' in k],flush=True)
        remote.session.close();remote.page.cache_clear()
if __name__=='__main__':inspect()

