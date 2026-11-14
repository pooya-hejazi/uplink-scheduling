"""Fresh bounded HTTPS check of sealed RENEW source ranges (no raw bytes written to disk)."""
import hashlib,io,json,time,urllib.parse,urllib.request
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import h5py
import numpy as np
from prepare import archive,zipfile,read_rows,dump,write_rows
class Window(io.RawIOBase):
    def __init__(self,which,record):
        self.src=record['source'];self.man=record['range_hashes'];self.pos=0;self.buf=OrderedDict();self.log={};self.which=which
        assert urllib.parse.urlsplit(self.src['url']).hostname=='renew.rice.edu'
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset+(0 if whence==0 else self.pos if whence==1 else self.src['bytes']);return self.pos
    def page(self,i):
        if i in self.buf:return self.buf[i]
        assert str(i) in self.man,('page absent from preexisting whole-range hash manifest',self.which,i)
        lo=i*2**20;hi=min(lo+2**20,self.src['bytes'])-1
        req=urllib.request.Request(self.src['url'],headers={'Range':f'bytes={lo}-{hi}','If-Match':self.src['etag'],'Accept-Encoding':'identity'})
        for n in range(2):
            try:
                with urllib.request.urlopen(req,timeout=13) as f:
                    assert urllib.parse.urlsplit(f.url).hostname=='renew.rice.edu'
                    assert f.status==206 and f.headers.get('Content-Range')==f'bytes {lo}-{hi}/{self.src["bytes"]}' and f.headers.get('ETag')==self.src['etag']
                    data=f.read(hi-lo+2)
                break
            except (OSError,TimeoutError):
                if n:raise
        hv=hashlib.sha256(data).hexdigest()
        assert len(data)==hi-lo+1 and hv==self.man[str(i)]
        self.log[i]=dict(mode=self.which,page=i,offset=lo,length=len(data),sha256=hv);self.buf[i]=data
        if len(self.buf)>32:self.buf.popitem(last=False)
        return data
    def readinto(self,b):
        n=min(len(b),max(0,self.src['bytes']-self.pos));p=0
        while p<n:
            i,off=divmod(self.pos+p,2**20);data=self.page(i);t=min(n-p,len(data)-off);b[p:p+t]=data[off:off+t];p+=t
        self.pos+=p;return p
def one(mode):
    with zipfile.ZipFile(archive('Gate_3')) as z:
        name='distributed_'+mode+'_LoS_A';root='Gate_3/results/rice_field/'+name
        record=json.loads(z.read(root+'.json'));assert record['frames'][0]==128
        ref=next(r for r in read_rows(z.read(root+'.csv')) if r['frame']=='128' and r['k']=='6')
        md=json.loads(z.read('Gate_2/results/rice_replay_'+mode+'.json'));remote=Window(mode,record)
    # A held-out six-user pilot frame and the eligible noise calibration frames in this 32-window release.
    with h5py.File(remote,'r',rdcc_nbytes=4*2**20) as file:
        data=file['Data'];pilot=data['Pilot_Samples'][128,0];noise=np.stack([data['Noise_Samples'][i,0,0] for i in record['calibration']])
        pf=np.asarray(data.attrs['OFDM_PILOT_F']);pil=pf[::2]+1j*pf[1::2]
    tones=md['tones'];anten=record['active']
    def lts(x,a):
        z=x[...,2*a:2*(a+64):2].astype(float)+1j*x[...,2*a+1:2*(a+64):2].astype(float)
        ft=np.fft.fft(z/32768,axis=-1)
        if md['fftshift']:ft=np.fft.fftshift(ft,axes=-1)
        return ft[...,tones]
    sig=np.sqrt(np.mean([abs(lts(noise,a))**2 for a,b in md['windows']],axis=(0,1)))[anten]
    hh=np.stack([lts(pilot[u],md['windows'][0][0]+record['lags'][u])[anten]/pil[tones]/sig for u in range(6)])
    ii,jj=np.triu_indices(6,1);g=(abs(hh)**2).sum(1);cross=(hh[ii].conj()*hh[jj]).sum(1)
    rho=float(np.mean(abs(cross)**2/(g[ii]*g[jj])))
    assert int(ref['valid']) and np.isclose(rho,float(ref['mean_pair_rho']),rtol=1e-12,atol=2e-13)
    return dict(mode=mode,source_file=record['source']['url'].split('/')[-1],etag=record['source']['etag'],frame=128,noise_calibration_frames=record['calibration'],raw_input_bytes_in_memory=int(pilot.nbytes+noise.nbytes),verified_http_pages=len(remote.log),verified_http_bytes=sum(r['length'] for r in remote.log.values()),recomputed_three_tone_mean_pair_rho=rho,released_mean_pair_rho=float(ref['mean_pair_rho']),raw_saved=False),list(remote.log.values())
def main():
    # HDF5 is a file-like Python reader, so run the two small specimens sequentially in-process.
    outcomes=[one(mode) for mode in ('HUB','LO')]
    write_rows('renew_spot_range_hashes.csv',sorted(sum((r[1] for r in outcomes),[]),key=lambda v:(v['mode'],v['page'])))
    dump('renew_spot_replay.json',dict(results=[r[0] for r in outcomes],scope='Independently re-fetched/authenticated source pages for the frame-128 sensitivity pilot and eligible calibration noise windows (three HUB, two LO); reproduced one numeric field result per capture. Not a full raw capture or a replay of all distributed primary decisions.'))
if __name__=='__main__':main()
