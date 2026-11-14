"""Decode all pilot frames of a selected local Rice capture; output only aggregate/receipt diagnostics."""
import h5py,json,csv,sys,hashlib
from pathlib import Path
from solver import *
from rice_io import R,inventory,Remote
from rice_signal import strength,synchronize
home=Path(__file__).resolve().parent
def schema(f):
    d=f['Data'];a=d.attrs;ps=d['Pilot_Samples']; ns=d['Noise_Samples']
    scalar=lambda k:int(np.asarray(a[k]).item())
    Tn,cell,K,N,L=ps.shape;assert (cell,K,N)==(1,6,64) and ns.shape==(Tn,1,1,N,L)
    fft=scalar('FFT_SIZE');cp=scalar('CP_LEN');pre=scalar('PREFIX_LEN');post=scalar('POSTFIX_LEN');slot=scalar('SLOT_SAMP_LEN')
    def tocomplex(q):q=np.asarray(q);return q[::2]+1j*q[1::2]
    pf=tocomplex(a['OFDM_PILOT_F']);pt=tocomplex(a['OFDM_PILOT'])
    fft0=np.fft.fft(pt);shifted=np.max(abs(np.fft.fftshift(fft0)-pf))<1e-5
    assert shifted or np.max(abs(fft0-pf))<1e-5
    sc=np.sort(a['OFDM_DATA_SC']);control=np.sort(a['OFDM_PILOT_SC']);assert len(np.unique(sc))==48 and len(control)==4 and not set(sc)&set(control)
    physical=(sc.astype('int64')-fft//2 if shifted else (sc.astype('int64')+fft//2)%fft-fft//2)
    indices=np.argsort(physical)[[12,24,36]];tones=sc[indices];signed=physical[indices]
    assert len(pf)==fft==64 and len(set(signed))==3 and np.all(abs(pf[tones])>.99)
    bounds=[(pre+cp+j*(fft+cp),pre+cp+j*(fft+cp)+fft) for j in range(2)]
    assert bounds[0][1]<=bounds[1][0] and bounds[-1][1]<=slot-post and slot*2==L
    sched=[s.decode() if isinstance(s,bytes) else str(s) for s in a['CL_FRAME_SCHED']]
    pilot_slots=[s.index('P') for s in sched];assert len(sched)==6 and len(set(pilot_slots))==6
    return d,dict(frames=Tn,k=K,antenna_slots=N,tones=tones.tolist(),signed_tones=signed.tolist(),native_index_quartiles=sc[[12,24,36]].tolist(),data_tones=sc.tolist(),fftshift=bool(shifted),windows=bounds,pilot_slots=pilot_slots,cp=cp,prefix=pre,postfix=post,sample_rate=scalar('RATE'),carrier=scalar('FREQ')),pf
def extract(X,bounds,shift,tones,pf=None):
    t=[]
    for a,b in bounds:
        iq=X[...,2*a:2*b:2].astype('float64')+1j*X[...,2*a+1:2*b:2].astype('float64')
        ft=np.fft.fft(iq/32768,axis=-1)
        if shift:ft=np.fft.fftshift(ft,axes=-1)
        t.append(ft[...,tones] if pf is None else ft[...,tones]/pf[tones])
    return t
def decode(mode,path):
    row=next(r for r in inventory() if r['placement']=='distributed' and r['mode']==mode and r['rf_chain']=='A')
    t0=now()
    with h5py.File(path,'r',rdcc_nbytes=16*2**20) as f:
        d,meta,pf=schema(f);nf=meta['frames'];tones=meta['tones'];bounds=meta['windows'];shift=meta['fftshift']
        assert nf>128
        # Reserve the first 128 frames as calibration. Screen receiver power AND coherent LTS response:
        # a live ADC can contain only noise. Do not tune the cutoff to obtain the catalog count of 61.
        calibration=np.arange(32,128,8);xc=d['Pilot_Samples'][calibration,0];nc=d['Noise_Samples'][calibration,0,0]
        preliminary=np.mean(xc.astype(float)**2,axis=(2,3))/np.maximum(1.,np.mean(nc.astype(float)**2,axis=(1,2)))[:,None]
        ok=np.min(preliminary,axis=1)>2
        if not ok.any():raise ArithmeticError('no six-user pilot signals in reserved calibration frames')
        xc,nc=xc[ok],nc[ok];lag,_,_=synchronize(xc[:4],meta['prefix'],meta['cp'],64,1120,meta['postfix'])
        strength_db,coh=strength(xc,nc,meta['prefix'],meta['cp'],64,lag,pf,shift)
        active=np.flatnonzero(np.any((strength_db>=6)&(coh>=.60),axis=0))
        if len(active)<4:raise ArithmeticError('no reproducible active RF stack')
        meta.update(calibration_frames=[0,127],quality_frames=calibration[ok].tolist(),alignment_shifts=lag,active_rule='at least one UE with pilot/noise >=6 dB AND normalized adjacent-LTS coherence >=0.60 on preceding calibration frames',calibration_signal_db=strength_db.tolist(),calibration_lts_coherence=coh.tolist())
        a0=np.empty((nf,6,64,3),complex);a1=np.empty_like(a0);noise=np.empty((nf,64,3));nonzero=np.zeros((nf,64),bool);pcount=np.zeros(nf,int);present=np.zeros(nf,bool)
        for i in range(0,nf,20):
            sl=slice(i,min(i+20,nf)); x=d['Pilot_Samples'][sl,0];n=d['Noise_Samples'][sl,0,0]
            nonzero[sl]=np.any(x!=0,axis=(1,3))
            pcount[sl]=np.sum(np.any(x!=0,axis=(2,3)),axis=1)
            check=np.empty((len(x),6)); guard=x[:,:,:,0:128].astype(float)
            for u,l in enumerate(lag):
                win=[(a+l,b+l) for a,b in bounds];a0[sl,u],a1[sl,u]=extract(x[:,u],win,shift,tones,pf)
                a,b=win[0];signal=np.mean(x[:,u,:,2*a:2*b].astype(float)**2,axis=-1);bg=np.mean(guard[:,u]**2,axis=-1)
                check[:,u]=np.median(signal[:,active]/np.maximum(bg[:,active],1.),axis=1)
            present[sl]=np.min(check,axis=1)>=2
            noise[sl]=np.mean([abs(y)**2 for y in extract(n,bounds,shift,tones)],axis=0)
            if i%400==0:print(mode,'decoded',i,flush=True)
    good=(pcount==6)&present&np.all(nonzero[:,active],axis=1)&np.all(noise[:,active,:]>0,axis=(1,2))
    if not good.any() or len(active)<4:raise ArithmeticError('no complete six-user decisions')
    # Independent physical RF streams; no arbitrary SNR rescaling. The noise slot is later in-frame:
    # estimate and freeze per-antenna/tone noise from the first complete frame, and replay only later frames.
    train=127; sigma=np.sqrt(noise[:128,active,:].mean(0));assert np.isfinite(sigma).all() and np.all(sigma>0)
    dates=np.flatnonzero(good&(np.arange(nf)>train));records=[]
    rate_norm=3*np.log(2)
    for fr in dates:
        h=np.ascontiguousarray(a0[fr][:,active,:]/sigma[None,:,:]);ref=a1[fr][:,active,:]/sigma[None,:,:]
        rec,_,tim=solve(h,'subgrad')
        pa=np.asarray(rec['pair']);pw=np.asarray(rec['power'])/PT;s=np.arange(3)
        v=np.frombuffer(base64.b64decode(rec['receiver'][2]),dtype='<c16').reshape(3,2,len(active));v0=np.sum(abs(v)**2,axis=-1)
        def realized(H):
            total=0.
            for j in [0,1]:
                own,other=pa[:,j],pa[:,1-j];u=v[:,j]
                total+=np.log1p(pw[own]*abs((u.conj()*H[own,:,s]).sum(1))**2/(v0[:,j]+pw[other]*abs((u.conj()*H[other,:,s]).sum(1))**2)).sum()
            return total/rate_norm
        observed=realized(h);reference=realized(ref);lower=int(rec['L'])/int(rec['den'])/rate_norm;upper=int(rec['U'])/int(rec['den'])/rate_norm
        if not lower<=observed+1e-10 or observed>upper+1e-10:raise ArithmeticError('recorded-input soundness violation')
        records.append([fr,rec['G'],lower,upper,reference,tim['total_ns']/1e6,rec['raw_sha'],rec['witness']])
    assert len(records)>0 and len(records)+128+sum(~good[128:])==nf
    with (R/f'rice_replay_{mode}.csv').open('w',newline='') as fp:
        w=csv.writer(fp);w.writerow(['frame','G','L_proxy','U_proxy','later_LTS_fixed_action_rate','ms','input_sha256','witness']);w.writerows(records)
    meta.update(source_sha256=json.loads((R/f'rice_sha_{mode}.json').read_text())['sha256'],active_indices=active.tolist(),active_count=len(active),nonzero_frame_counts=nonzero.sum(0).tolist(),noise_source='per-stream/tone mean on two nonoverlapping segments of the first 128 noise slots; frozen',abstention_frames=(128+np.flatnonzero(~good[128:])).tolist(),signal_absent_or_incomplete_all_frames=np.flatnonzero(~good).tolist(),decisions=len(records),elapsed_s=(now()-t0)/1e9,median_G=float(np.median([r[1] for r in records])),median_ms=float(np.median([r[5] for r in records])),fraction_0p1_250ms=float(np.mean([r[1]<=.1 and r[5]<=250 for r in records])),observed_violations=0,reference='later disjoint LTS proxy, never labelled truth',mode=mode)
    (R/f'rice_replay_{mode}.json').write_text(json.dumps(meta,indent=2));print(mode,{k:meta[k] for k in ['decisions','active_count','tones','median_G','median_ms','elapsed_s']},flush=True)
if __name__=='__main__':
    mode=sys.argv[1];row=next(r for r in inventory() if r['placement']=='distributed' and r['mode']==mode and r['rf_chain']=='A')
    if not (R/f'rice_replay_{mode}.json').exists():decode(mode,home/'rice_private'/Path(row['url']).name)

