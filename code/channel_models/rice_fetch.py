"""Download only the selected two author-hosted files, one at a time; retain only local working data."""
from rice_io import inventory,R
from concurrent.futures import ThreadPoolExecutor,as_completed
import io,os,shutil,hashlib,time,threading,json,sys
from pathlib import Path
import requests
home=Path(__file__).resolve().parent;scratch=home/'rice_private';scratch.mkdir(exist_ok=True)
class BufferFile(io.RawIOBase):
    def __init__(self,data):self.data=memoryview(data);self.pos=0
    def tell(self):return self.pos
    def seek(self,n,whence=0):self.pos=n if whence==0 else self.pos+n if whence==1 else len(self.data)+n;return self.pos
    def readinto(self,b):
        n=min(len(b),len(self.data)-self.pos);b[:n]=self.data[self.pos:self.pos+n];self.pos+=n;return n
    def readable(self):return True
    def seekable(self):return True
def fetch(row,mem=False):
    name=Path(row['url']).name;dest=scratch/name;N=row['bytes'];size=16*2**20
    if dest.exists() and (scratch/(name+'.sha256')).exists():return dest
    part=scratch/(name+'.part');journal=scratch/(name+'.ranges')
    if mem:
        import numpy as np,psutil
        if psutil.virtual_memory().available<2*N:raise MemoryError('memory reserve unavailable')
        buf=np.empty(N,dtype='uint8');journal=scratch/(name+'.memranges')
    elif not part.exists():
        if shutil.disk_usage(scratch).free<N+800*2**20:raise OSError('not enough space for one selected capture plus 800 MiB reserve')
        with part.open('wb') as f:f.truncate(N)
    if not mem and part.stat().st_size!=N:raise IOError('wrong staging size')
    done={} if mem or not journal.exists() else dict((int(i),sha) for i,sha in (x.split() for x in journal.read_text().splitlines()))
    n=(N+size-1)//size;tls=threading.local()
    def get(i):
        a=i*size;b=min(N,a+size)-1
        if not hasattr(tls,'session'):tls.session=requests.Session()
        for retry in range(6):
            try:
                with tls.session.get(row['url'],headers={'Range':f'bytes={a}-{b}','If-Match':row['etag'],'Accept-Encoding':'identity'},timeout=(18,90),stream=True) as rr:
                    rr.raise_for_status()
                    if rr.status_code!=206 or rr.headers.get('Content-Range','').lower()!=f'bytes {a}-{b}/{N}':raise IOError(f'invalid HTTP range {rr.status_code} {rr.headers.get("Content-Range")}')
                    data=rr.content
                if len(data)!=b-a+1:raise IOError('short response')
                if mem:buf[a:b+1]=np.frombuffer(data,dtype='uint8')
                else:
                    with part.open('r+b',buffering=0) as fp:fp.seek(a);fp.write(data)
                return i,hashlib.sha256(data).hexdigest()
            except (OSError,requests.RequestException) as e:
                if retry>=5:raise
                print('retry',i,retry,type(e).__name__,str(e)[:85],flush=True)
    start=time.monotonic()
    with ThreadPoolExecutor(10) as pool,journal.open('w' if mem else 'a') as jf:
        pending={pool.submit(get,i):i for i in range(n) if i not in done}
        for fut in as_completed(pending):
            i,sha=fut.result();done[i]=sha;jf.write(f'{i} {sha}\n');jf.flush()
            if len(done)%8==0 or len(done)==1:print(row['mode'],len(done),n,round(time.monotonic()-start),flush=True)
    whole=hashlib.sha256()
    with (BufferFile(buf) if mem else part.open('rb')) as fp:
        for i in range(n):
            data=fp.read(size);assert hashlib.sha256(data).hexdigest()==done[i];whole.update(data)
    if not mem:part.replace(dest);(scratch/(name+'.sha256')).write_text(whole.hexdigest())
    (R/f'rice_sha_{row["mode"]}.json').write_text(json.dumps({'file':name,'bytes':N,'sha256':whole.hexdigest(),'etag':row['etag']},indent=2))
    return BufferFile(buf) if mem else dest
if __name__=='__main__':
    mode=sys.argv[1];row=next(r for r in inventory() if r['mode']==mode and r['placement']=='distributed' and r['rf_chain']=='A')
    flag=scratch/(mode+'_memory.active')
    if '--ram-replay' in sys.argv:
        from rice_decode import decode
        flag.write_text(str(os.getpid()))
        try:
            with fetch(row,mem=True) as cap:decode(mode,cap)
        finally:flag.unlink(missing_ok=True)
    else:
        while flag.exists() and not (R/f'rice_replay_{mode}.json').exists():time.sleep(3)
        if not (R/f'rice_replay_{mode}.json').exists():print(fetch(row),flush=True)

