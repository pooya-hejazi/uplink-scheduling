"""Independent Argos IQ decoder and RENEW recorded-frame distribution reconstruction."""
import hashlib,itertools,json,os,statistics
from collections import Counter
from pathlib import Path
import numpy as np
from prepare import AUD,OUT,RELEASE,archive,dump,write_rows,read_rows,zipfile
def sha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def fft(A):
    iq=A.reshape(-1,8,7,224,2);x=(iq[...,0]+1j*iq[...,1])/32768.
    t=x[...,47:175].reshape(-1,8,7,2,64)
    return np.roll(np.fft.fft(t,axis=-1),32,axis=-1).transpose(0,2,1,3,4)
def signals(X):
    B=np.array([i for i in range(6,59) if i!=32]); N=np.setdiff1d(np.arange(64),B)
    u=X[:,:6];occupied=np.take(u,B,axis=-1);null=np.take(u,N,axis=-1)
    pwr=abs(occupied)**2;noise=abs(null)**2;eps=np.finfo(float).tiny
    conc=10*np.log10(np.maximum(eps,pwr.mean((3,4)))/np.maximum(eps,noise.mean((3,4))))
    num=abs((occupied[:,:,:,0,:].conj()*occupied[:,:,:,1,:]).sum(-1))
    den=np.sqrt(np.maximum(eps,pwr[:,:,:,0,:].sum(-1)*pwr[:,:,:,1,:].sum(-1)))
    return conc,num/den,occupied
def against(v,q):
    assert np.isclose(v,float(q),rtol=1e-12,atol=2e-13),(v,q)
def main():
    loc=Path(os.environ.get('GATE4_ARGOS_PRIVATE',str(RELEASE.parent/'Gate_3/rice_private/argos')))
    out=[];phase=[];modes={};frames_out=[]
    with zipfile.ZipFile(archive('Gate_3')) as z:
        R='Gate_3/results/argos/'
        official={(r['regime'],int(r['frame'])):r for r in read_rows(z.read(R+'frame_summaries.csv'))}
        pairs={(r['regime'],int(r['frame']),int(r['user_i']),int(r['user_j'])):r for r in read_rows(z.read(R+'pair_frames.csv'))}
        calib={(r['regime'],int(r['user']),int(r['rf_zero_based'])):r for r in read_rows(z.read(R+'rf_diagnostics.csv'))}
        for mode in ('static','env','mob'):
            ranges=json.loads(z.read(R+mode+'_ranges.json'));src=ranges['source'];rows=ranges['raw_ranges']
            assert ranges['policy_sha256']==hashlib.sha256(z.read('Gate_3/ARGOS_PROTOCOL.md')).hexdigest()
            assert len(rows)==33
            with np.load(loc/(mode+'.npz'),allow_pickle=False) as ar:
                cal,evaluation,ids=ar['cal'],ar['evaluation'],ar['frame']
            full=len(rows)==33 and len(ids)==len(evaluation)==32 and len(cal)==64
            assert full and sha(cal)==rows[0]['sha256'] and sha(cal[0])==ranges['initial_h5py_frame0_sha256']
            for x,v,r in zip(evaluation,ids,rows[1:]):assert v==r['start'] and sha(x)==r['sha256'] and x.nbytes==r['length']
            assert np.array_equal(ids,64+((2*np.arange(32)+1)*(ranges['total_frames']-64))//64)
            cc,co,_=signals(fft(cal));cm,om=np.median(cc,axis=0),np.median(co,axis=0)
            active=np.flatnonzero(np.logical_and(cm>=6,om>=.60).any(axis=0)); assert len(active)>=2
            for u,r in itertools.product(range(6),range(8)):
                ref=calib[mode,u+1,r];against(cm[u,r],ref['cal_median_occupied_to_null_dB']);against(om[u,r],ref['cal_median_lts_coherence']);assert (r in active)==int(ref['rf_retained'])
            ec,eo,X=signals(fft(evaluation)); YY=np.take(X,active,axis=2)
            accepted=[];kept2=[];delta=[];num_pairs=0
            for ix,f in enumerate(ids):
                c=ec[ix][:,active];o=eo[ix][:,active];qc=float(np.min(np.median(c,axis=1)));qo=float(np.min(np.median(o,axis=1)))
                v=YY[ix];pwr=(v.real**2+v.imag**2).sum(axis=1)
                ok=qc>=3 and qo>=.50 and pwr.min()>0 and np.isfinite(v).all()
                ref=official[mode,int(f)];against(qc,ref['minimum_user_occupied_to_null_dB']);against(qo,ref['minimum_user_lts_coherence']);assert ok==bool(int(ref['quality_pass']))
                vals=[]
                if pwr.min()>0:
                    for a,b in itertools.combinations(range(6),2):
                        cross=(v[a].conj()*v[b]).sum(axis=0);rho=(cross.real**2+cross.imag**2)/(pwr[a]*pwr[b]);summary=rho.mean(axis=1);vals.append(summary)
                        off=pairs[mode,int(f),a+1,b+1];against(summary[0],off['rho_first']);against(summary[1],off['rho_second']);num_pairs+=1
                    mu=np.mean(vals,axis=0);against(mu[0],ref['first_mean_rho']);against(mu[1],ref['second_mean_rho'])
                    if ok:accepted.append(float(mu[0]));kept2.append(float(mu[1]));delta.append(float(mu[1]-mu[0]))
                out.append(dict(mode=mode,frame=int(f),accepted=int(ok),source_range_sha256=rows[ix+1]['sha256'],mean_rho_first=float(mu[0]) if vals else '',mean_rho_second=float(mu[1]) if vals else ''))
            phase.append(dict(regime=mode,planned=32,accepted=len(accepted),median_first=statistics.median(accepted),median_second=statistics.median(kept2),paired_change=statistics.median(delta),active_rf=active.tolist(),validated_source_ranges=33,pair_frames_checked=num_pairs,source_file=Path(src['url']).name,ETag=src['etag']))
        for mode in ('HUB','LO'):
            path='Gate_2/results/rice_';meta=json.loads(z.read(path+f'replay_{mode}.json'));raw=read_rows(z.read(path+f'replay_{mode}.csv'));source=json.loads(z.read(path+f'sha_{mode}.json'))
            assert source['sha256']==meta['source_sha256'];raw={int(r['frame']):r for r in raw}
            frames=list(range(meta['calibration_frames'][1]+1,meta['frames']));abstained=set(meta['abstention_frames'])
            assert set(raw).isdisjoint(abstained) and set(raw)|abstained==set(frames)
            for f in frames:
                r=raw.get(f);gap=float(r['G']) if r else '';ms=float(r['ms']) if r else ''
                frames_out.append(dict(mode=mode,frame=f,retained=int(bool(r)),useful=int(bool(r) and gap<=.1 and ms<=250),gap=gap,ms=ms,later_minus_early=float(r['later_LTS_fixed_action_rate'])-float(r['L_proxy']) if r else '',reason='' if r else 'signal absent or incomplete',early_input_sha256=r['input_sha256'] if r else ''))
            modes[mode]=dict(full_capture_sha256=source['sha256'],source_file=source['file'],bytes=source['bytes'],etag=source['etag'],n_postprefix=len(frames),eligible=len(raw),abstentions=len(abstained),raw_reaccessed=False)
    dist=[]
    for mode in ('HUB','LO'):
        grp=[r for r in frames_out if r['mode']==mode];n=len(grp)
        for metric in ('gap','later_minus_early','ms'):
            vals=sorted(r[metric] for r in grp if r['retained']);count=Counter(vals);rank=0
            for value in sorted(count):
                rank+=count[value]
                dist.append(dict(mode=mode,metric=metric,threshold=value,count_at_or_below=rank,denominator_all_postprefix=n,cumulative_fraction=rank/n))
    write_rows('argos_frame_replay.csv',out);write_rows('renew_all_postprefix_frames.csv',frames_out);write_rows('renew_ecdfs.csv',dist)
    dump('hardware_scope.json',dict(argos_input='Local private IQ windows re-read; all 99 byte-range digests and three frame-zero digests checked against Gate 3. No IQ or channel coefficients are redistributed.',argos=phase,renew=modes,renew_input='Only archived frame and abstention records and raw capture digest metadata were available in the designated session directories. No complete distributed HUB/LO IQ or frame-slice archive was present; the two source files together exceed 9.3 GB. The ECDF denominator is all 1,873 post-prefix frames per mode. No new capture or population inference.',renew_replayed_frame_rows=len(frames_out),renew_ecdf_rows=len(dist)))
if __name__=='__main__':main()
