"""Chronological LTS calibration and exhaustive equal-power scheduling on RENEW.

Reconstructed complex channels stay in a separate private directory. Only scalar
results and source hashes belong in the review package.
"""
import argparse
import base64
import hashlib
import itertools
import json
import math
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'reviewer_data'
PRIVATE=ROOT/'output/reviewer_revision_20261114/private'
for name in ('Gate_2','Gate_2B','Gate_3'):sys.path.insert(0,str(ROOT/name))
from rice_io import Remote,inventory
from rice_decode import extract
import solver
from solver import nominal,PT,Q,T,lower


class PrefetchedRemote(Remote):
    """Bounded, read-only range prefetch; raw pages remain in memory."""
    def __init__(self,row):
        super().__init__(row)
        self.block=2*2**20
        self.pool=ThreadPoolExecutor(max_workers=4)
        self.pending=OrderedDict()
        self.local=threading.local()

    def fetch(self,i):
        if not hasattr(self.local,'session'):self.local.session=requests.Session()
        start=i*self.block;end=min(self.size,start+self.block)-1
        for attempt in range(3):
            try:
                with self.local.session.get(self.row['url'],headers={'Range':f'bytes={start}-{end}','If-Match':self.row['etag'],'Accept-Encoding':'identity'},timeout=(15,60)) as r:
                    r.raise_for_status()
                    assert r.status_code==206 and r.headers.get('Content-Range')==f'bytes {start}-{end}/{self.size}' and r.headers.get('ETag')==self.row['etag']
                    data=r.content
                assert len(data)==end-start+1
                return data
            except requests.RequestException:
                if attempt==2:raise

    def page(self,i):
        for j in range(i,min(i+8,(self.size+self.block-1)//self.block)):
            if j not in self.pending:self.pending[j]=self.pool.submit(self.fetch,j)
        data=self.pending[i].result()
        self.pending.move_to_end(i)
        digest=hashlib.sha256(data).hexdigest()
        assert self.chunks.setdefault(i,digest)==digest
        while len(self.pending)>64:
            _,future=self.pending.popitem(last=False)
            future.cancel()
        return data


def decode(mode):
    PRIVATE.mkdir(parents=True,exist_ok=True)
    dest=PRIVATE/(mode+'.npz')
    if dest.exists():
        print('Using private decoded windows',mode,flush=True);return
    md=json.loads((ROOT/f'Gate_2/results/rice_replay_{mode}.json').read_text())
    row=next(r for r in inventory() if r['placement']=='distributed' and r['mode']==mode and r['rf_chain']=='A')
    rr=PrefetchedRemote(row)
    with h5py.File(rr,'r',rdcc_nbytes=8*2**20) as file:
        data=file['Data'];pf=np.asarray(data.attrs['OFDM_PILOT_F']);pf=pf[::2]+1j*pf[1::2]
        tones=md['tones'];windows=md['windows'];active=md['active_indices'];lag=md['alignment_shifts']
        sigfile=PRIVATE/(mode+'_sigma.npy')
        if sigfile.exists():sigma=np.load(sigfile)
        else:
            noise=[]
            for start in range(0,128,16):
                n=data['Noise_Samples'][start:min(128,start+16),0,0]
                noise.append(np.mean([abs(v)**2 for v in extract(n,windows,md['fftshift'],tones)],axis=0))
                print(mode,'noise prefix',start+len(n),flush=True)
            sigma=np.sqrt(np.concatenate(noise)[:,active,:].mean(0));assert np.all(sigma>0)
            np.save(sigfile,sigma)
        ids=pd.read_csv(ROOT/f'Gate_2/results/rice_replay_{mode}.csv').frame.to_numpy()
        early=[];later=[]
        expected=pd.read_csv(ROOT/f'Gate_2/results/rice_replay_{mode}.csv')
        for idx,fr in enumerate(ids):
            framefile=PRIVATE/f'{mode}_{int(fr):04d}.npz'
            if framefile.exists():
                with np.load(framefile) as old:early.append(old['early']);later.append(old['later'])
                continue
            x=data['Pilot_Samples'][int(fr),0];v=[[],[]]
            for user in range(6):
                a,b=extract(x[user],[(l+lag[user],r+lag[user]) for l,r in windows],md['fftshift'],tones,pf)
                v[0].append(a[active]/sigma);v[1].append(b[active]/sigma)
            h0,h1=np.asarray(v[0]),np.asarray(v[1])
            assert solver.digest(h0)==expected.iloc[idx].input_sha256,('early input hash',mode,int(fr))
            np.savez_compressed(framefile,early=h0,later=h1)
            early.append(h0);later.append(h1)
            if idx%32==31:print(mode,'authenticated frames',idx+1,'/',len(ids),'HTTP pages',len(rr.chunks),flush=True)
        np.savez_compressed(dest,frames=ids,early=np.asarray(early),later=np.asarray(later))
    (PRIVATE/(mode+'_source.json')).write_text(json.dumps(dict(source=row,range_sha256=rr.chunks,frames=ids.tolist(),early_hashes_match=True),indent=2))
    rr.pool.shutdown(wait=True);rr.session.close()
    print(mode,'private decoding complete',flush=True)


def rate(h,act):
    pairs,p,v=act;s=np.arange(3);value=0.
    for t in (0,1):
        a,b=pairs[:,t],pairs[:,1-t];d=v[:,t]
        value+=np.log1p((p[a]/PT)*abs((d.conj()*h[a,:,s]).sum(1))**2/((abs(d)**2).sum(1)+(p[b]/PT)*abs((d.conj()*h[b,:,s]).sum(1))**2)).sum()
    return float(value/(3*np.log(2)))


def scores(h,ref,act):
    pairs,p,v=act;delta=ref-h;s=np.arange(3);full=np.linalg.norm(delta,axis=1).max();projected=0.
    for t in (0,1):
        d=v[:,t]/np.linalg.norm(v[:,t],axis=1)[:,None]
        for j in (0,1):projected=max(projected,abs((d.conj()*delta[pairs[:,j],:,s]).sum(1)).max())
    return float(full),float(projected)


def evaluate(mode):
    from audit import replay
    z=np.load(PRIVATE/(mode+'.npz'))
    I,J=np.triu_indices(6,1)
    schedules=np.array([p for p in itertools.permutations(range(6)) if all(p[j]<p[j+1] for j in (0,2,4))]).reshape(-1,3,2)
    assert len(schedules)==90 and len({tuple(p.ravel()) for p in schedules})==90
    edge=solver.edgeid(6,schedules[:,:,0],schedules[:,:,1]);ss=np.arange(3)
    ncal=256;rank=math.ceil(.975*(ncal+1));assert rank==251
    actions=[];sc=[]
    for h,ref in zip(z['early'],z['later']):
        act=solver.make_action(h,I,J,'subgrad');actions.append(act);sc.append(scores(h,ref,act))
    sc=np.asarray(sc);qf,qp=np.nextafter(np.sort(sc[:ncal],axis=0)[rank-1],np.inf)
    assert np.isfinite([qf,qp]).all()
    original=pd.read_csv(ROOT/f'Gate_2/results/rice_replay_{mode}.csv').set_index('frame')
    rows=[]
    for i,(fr,h,ref,act) in enumerate(zip(z['frames'],z['early'],z['later'],actions)):
        nom=nominal(h,I,J);values=nom[2][edge,ss].sum(1)/(3*np.log(2));equal=float(values.max())
        early=rate(h,act);later=rate(ref,act);saved=original.loc[fr]
        assert solver.digest(h)==saved.input_sha256
        assert abs(later-saved.later_LTS_fixed_action_rate)<1e-10
        row=dict(mode=mode,frame=int(fr),split='calibration' if i<ncal else 'test',equal_power_optimum=equal,early_rate=early,early_L=saved.L_proxy,early_U=saved.U_proxy,early_G=saved.G,equal_power_reference_gap=saved.U_proxy-equal,later_rate=later,F_score=sc[i,0],P_score=sc[i,1],qF=qf,qP=qp)
        row.update(early_input_sha256=solver.digest(h),later_input_sha256=solver.digest(ref))
        assert row['equal_power_reference_gap']>=-1e-9
        if i>=ncal:
            r,_,_=solver.solve(h,'subgrad',eps=qf,proj=qp,action=act);replay(h,r,qf,qp)
            norm=3*np.log(2);lp=sum(r['LP_pair'])/Q/norm;lf=sum(r['LF_pair'])/Q/norm;upper=int(r['U'])/int(r['den'])/norm
            hitf=sc[i,0]<=qf;hitp=sc[i,1]<=qp
            assert not hitp or later>=lp-1e-10
            assert not hitf or (later>=lf-1e-10 and later<=upper+1e-10)
            row.update(LP=lp,LF=lf,U_F=upper,projected_width=upper-lp,covered_floor=int(later>=lp-1e-10),covered_interval=int(max(lp,lf)-1e-10<=later<=upper+1e-10),hitF=int(hitf),hitP=int(hitp),joint=int(hitf and hitp))
        rows.append(row)
        if i%64==63:print(mode,'calibrated/exhaustive evaluation',i+1,flush=True)
    d=pd.DataFrame(rows);d.to_csv(OUT/f'hardware_calibration_{mode}.csv',index=False)
    t=d.query("split=='test'")
    report=dict(mode=mode,n_calibration=ncal,n_test=len(t),rank=rank,alpha_per_event=.025,qF=qf,qP=qp,floor_coverage=float(t.covered_floor.mean()),interval_coverage=float(t.covered_interval.mean()),joint_score_coverage=float(t.joint.mean()),median_LP=float(t.LP.median()),median_UF=float(t.U_F.median()),median_width=float(t.projected_width.median()),positive_floors=int((t.LP>0).sum()),median_equal_power_gap=float(d.equal_power_reference_gap.median()),scope='Chronological within-capture observable-LTS2 evaluation. No exchangeability/population or latent-channel coverage claim.')
    (OUT/f'hardware_calibration_{mode}.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('task',choices=['decode','evaluate']);p.add_argument('mode',choices=['HUB','LO']);a=p.parse_args();globals()[a.task](a.mode)
