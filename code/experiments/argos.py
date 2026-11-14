"""Secondary, descriptive user-channel spatial correlations at Rice Argos's recorded six-user load."""
from argos_source import root,dest
import csv,json,hashlib,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from itertools import combinations
MODE={'static':'Static','env':'Environmental mobility','mob':'Mobile'}
BINS=np.r_[np.arange(6,32),np.arange(33,59)]
NULL=np.setdiff1d(np.arange(64),BINS)
IJ=np.array(list(combinations(range(6),2)))
EPS=np.finfo(float).tiny
def transform(x):
    """Return [frame,LTS,user-or-noise,antenna,centered FFT bin]."""
    m=len(x);assert x.shape==(m,8,1568,2)
    raw=x.reshape(m,8,7,224,2).astype(float);z=(raw[...,0]+1j*raw[...,1])/32768
    blocks=np.stack((z[...,47:111],z[...,111:175]),axis=1).swapaxes(2,3)
    return np.fft.fftshift(np.fft.fft(blocks,axis=-1),axes=-1)
def quality(z):
    """User/RF tests use only pilot occupied/guard bins and the adjacent LTS, never spatial correlations."""
    a=z[:,:,0:6];h=a[...,BINS];v=a[...,NULL]
    e=np.mean(np.abs(h)**2,axis=-1);n=np.mean(np.abs(v)**2,axis=-1)
    c=abs((h[:,0].conj()*h[:,1]).sum(-1))/np.sqrt(np.maximum(EPS,(abs(h[:,0])**2).sum(-1)*(abs(h[:,1])**2).sum(-1)))
    return 10*np.log10(np.maximum(EPS,e.mean(1))/np.maximum(EPS,n.mean(1))),c
def pairs(h):
    """[user,antenna,tone] -> 15 absolute squared unit-vector inner products per tone."""
    assert h.shape[0]==6 and h.shape[2]==52
    norms=np.linalg.norm(h,axis=1)
    if not np.all(np.isfinite(norms)&(norms>0)):return None
    q=(h/norms[:,None,:]).transpose(2,0,1);gram=q.conj()@q.swapaxes(1,2);a,b=IJ.T
    assert np.max(np.abs(gram-gram.conj().swapaxes(1,2)))<2e-13 and np.max(abs(np.diagonal(gram,axis1=1,axis2=2)-1))<2e-13
    mat=np.abs(gram[:,a,b].T)**2
    ref=np.array([[abs(np.vdot(h[i,:,s],h[j,:,s]))**2/((np.vdot(h[i,:,s],h[i,:,s]).real)*(np.vdot(h[j,:,s],h[j,:,s]).real)) for s in range(52)] for i,j in IJ])
    assert np.max(np.abs(ref-mat))<2e-13 and mat.min()>=0 and mat.max()<=1+2e-13
    return np.clip(mat,0,1)
def control():
    h=np.repeat(np.eye(6,dtype=complex)[:,:,None],52,axis=2);assert np.all(pairs(h)==0)
    h[1]=h[0]*(2+3j);x=pairs(h);assert np.allclose(x[0],1) and np.allclose(x[1:],0)
    h[2]=0;assert pairs(h) is None
    rng=np.random.default_rng(714);z=rng.standard_normal((6,8,52))+1j*rng.standard_normal((6,8,52))
    assert np.allclose(pairs(z),pairs(z*np.exp(1j*rng.uniform(-3,3,(6,1,52)))),atol=2e-13)
def csvout(path,rows,fields=None):
    with path.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def digest(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def quart(v):
    if not v:return None
    return [float(x) for x in np.quantile(v,[.25,.5,.75])]
def analyze(name):
    src=json.loads((dest/f'{name}_ranges.json').read_text());assert src['policy_sha256']==hashlib.sha256((root/'ARGOS_PROTOCOL.md').read_bytes()).hexdigest()
    md=json.loads((dest/f'{name}_metadata.json').read_text())
    assert md['source']==src['source'];parts=src['raw_ranges']
    with np.load(root/'rice_private/argos'/f'{name}.npz',allow_pickle=False) as ar:
        cal,vals,frames=(ar[k] for k in ['cal','evaluation','frame'])
    assert len(cal)==64 and len(vals)==len(frames)==32 and len(parts)==33
    assert digest(cal)==parts[0]['sha256'] and digest(cal[0])==src['initial_h5py_frame0_sha256']
    assert all(digest(x)==entry['sha256'] and int(fr)==entry['start'] for x,fr,entry in zip(vals,frames,parts[1:]))
    z=transform(cal);cc,co=quality(z);cm,mm=np.median(cc,0),np.median(co,0)
    active=np.where(np.any((cm>=6)&(mm>=.60),axis=0))[0];d=[]
    for user in range(6):
        for a in range(8):d.append(dict(regime=name,user=user+1,rf_zero_based=a,cal_median_occupied_to_null_dB=float(cm[user,a]),cal_median_lts_coherence=float(mm[user,a]),rf_retained=int(a in active)))
    zz=transform(vals);fc,ff=quality(zz);decisions=[];pr=[];perTone=[];kept=[];reps=[];finite=[];delta=[];means=[]
    for k,frame in enumerate(frames):
        x=zz[k];groups=x[:,:6][:,:,active,:][...,BINS]
        concentration=float(np.min(np.median(fc[k][:,active],axis=1))) if len(active) else None
        repeat=float(np.min(np.median(ff[k][:,active],axis=1))) if len(active) else None
        sets=[pairs(t) for t in groups] if len(active)>=2 else [None,None]
        full=all(a is not None for a in sets);reasons=[]
        if len(active)<2:reasons.append('fewer than two qualified RFs')
        if not full:reasons.append('incomplete six-user vectors')
        if concentration is None or concentration<3:reasons.append('occupied/null <3 dB')
        if repeat is None or repeat<.50:reasons.append('pilot coherence <0.50')
        valid=not reasons
        # The seventh slot is the acquisition's noise slot, never a user or a user pair.
        noise=float(np.mean(np.abs(x[:,6][:,active,:][...,BINS])**2)) if len(active) else None
        if full:
            per=np.stack(sets);pairmean=per.mean(-1);m1,m2=pairmean.mean(1);finite.append(float(m1))
            if valid:kept.append(float(m1));reps.append(float(m2));delta.append(float(m2-m1));means.append(pairmean[0])
            for j,(u,v) in enumerate(IJ):
                pr.append(dict(regime=name,frame=int(frame),user_i=int(u+1),user_j=int(v+1),quality_pass=int(valid),rho_first=float(pairmean[0,j]),rho_second=float(pairmean[1,j])))
            if valid:perTone.append(per)
        else:m1=m2=None
        decisions.append(dict(regime=name,frame=int(frame),quality_pass=int(valid),reason='; '.join(reasons),retained_rf=len(active),minimum_user_occupied_to_null_dB=concentration,minimum_user_lts_coherence=repeat,noise_slot_mean_power=noise,first_mean_rho=float(m1) if full else None,second_mean_rho=float(m2) if full else None,first_max_pair_mean_rho=float(pairmean[0].max()) if full else None))
    tonal=[];perpair=[]
    if perTone:
        v=np.stack(perTone);p=v.mean(-1)
        for pos,tone in enumerate(BINS-32):tonal.append(dict(regime=name,signed_tone=int(tone),frames=len(v),median_frame_mean_rho_first=float(np.median(v[:,0,: ,pos].mean(1))),median_frame_mean_rho_second=float(np.median(v[:,1,:,pos].mean(1)))))
        for j,(u,w) in enumerate(IJ):perpair.append(dict(regime=name,user_i=int(u+1),user_j=int(w+1),frames=len(v),median_frame_rho_first=float(np.median(p[:,0,j])),median_frame_rho_second=float(np.median(p[:,1,j]))))
    return dict(regime=name,source_file=Path(src['source']['url']).name,description=md['schema']['/']['attrs']['Description']['head'][0].strip(),rf_indices=active.tolist(),users=6,pairs=15,tones=52,recorded_frames=src['total_frames'],frames_planned=32,frames_finite=len(finite),frames_accepted=len(kept),first_lts_quartiles=quart(kept),second_lts_quartiles=quart(reps),unfiltered_finite_first_lts_quartiles=quart(finite),paired_delta_quartiles=quart(delta),worst_absolute_frame_mean_lts_difference=max(map(abs,delta),default=None)),decisions,pr,d,tonal,perpair
def main():
    control();summ=[];frames=[];pair=[];cal=[];tt=[];pp=[]
    for name in MODE:
        s,f,p,c,t,i=analyze(name);summ.append(s);frames.extend(f);pair.extend(p);cal.extend(c);tt.extend(t);pp.extend(i)
    csvout(dest/'frame_summaries.csv',frames);csvout(dest/'rf_diagnostics.csv',cal)
    csvout(dest/'pair_frames.csv',pair,['regime','frame','user_i','user_j','quality_pass','rho_first','rho_second'])
    csvout(dest/'tone_summaries.csv',tt,['regime','signed_tone','frames','median_frame_mean_rho_first','median_frame_mean_rho_second'])
    csvout(dest/'pair_summaries.csv',pp,['regime','user_i','user_j','frames','median_frame_rho_first','median_frame_rho_second'])
    def result(s):
        v=s['first_lts_quartiles']
        return f"{MODE[s['regime']].lower()} {v[1]:.3f} ({s['frames_accepted']}/32)" if v else f"{MODE[s['regime']].lower()}: no valid frames (0/32)"
    sentence="Three six-user Argos UHF recordings were assessed. Median frame-mean squared user-channel correlation (valid/planned frames) was "+', '.join(map(result,summ))+". Each frame averages 15 user pairs and 52 occupied tones. This is descriptive evidence from one array; it supplies no additional independent distributed HUB/LO comparison. Source: C. Shepard, J. Ding, R. E. Guerra and L. Zhong, Understanding Real Many-Antenna MU-MIMO Channels, Asilomar 2016."
    report=dict(statement=sentence,unit='dimensionless normalized squared inter-user inner product across active RF antennas',recordings=3,unit_limit='one setup, one recording per condition; independence across sessions not assumed',secondary_only=True,first_lts_start=47,second_lts_start=111,centered_bins=BINS.tolist(),signed_tones=(BINS-32).tolist(),calibration_frame_id_range_inclusive=[0,63],regimes=summ)
    (root/'results/argos_summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(sentence)
    for s in summ:print(s['regime'],s['rf_indices'],s['first_lts_quartiles'],s['second_lts_quartiles'],s['unfiltered_finite_first_lts_quartiles'],flush=True)
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='check':control();print('PASS: orthogonal, duplicate, zero and phase-rescaled controls; vectorized/scalar agreement')
    else:main()

