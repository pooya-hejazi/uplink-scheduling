"""Descriptive three-tone RF-chain and placement sensitivity. Streaming only; no raw Rice data retained."""
from grid import *
from rice_io import Remote,inventory
from rice_decode import schema,extract,synchronize,strength
import h5py
from contextlib import closing
def run():
    guard();dest=root3/'results/rice_field';dest.mkdir(exist_ok=True);errors=[];myrows=inventory()
    for row in myrows:
        who='_'.join(row[k] for k in ['placement','mode','los','rf_chain']);path=dest/(who+'.csv')
        if path.exists():continue
        try:
            with closing(Remote(row)) as rr,h5py.File(rr,'r',rdcc_nbytes=16*2**20) as file:
                d,meta,pf=schema(file);nf=meta['frames'];j=np.array([32,56,80,104]);x=d['Pilot_Samples'][j,0];nc=d['Noise_Samples'][j,0,0];s=x.astype(float)
                good=(np.min(np.mean(s*s,axis=(2,3))/np.maximum(1.,np.mean(nc.astype(float)**2,axis=(1,2)))[:,None],axis=1)>2)
                assert good.any(),'no calibration pilots';cal_ids=j[good].tolist();x,nc=x[good],nc[good];lag,_,_=synchronize(x[:4],meta['prefix'],meta['cp'],64,1120,meta['postfix']);db,co=strength(x,nc,meta['prefix'],meta['cp'],64,lag,pf,meta['fftshift'])
                active=np.flatnonzero(np.any((db>=6)&(co>=.60),axis=0));assert len(active)>=4
                win=meta['windows'];tones=meta['tones'];sh=meta['fftshift'];sigma=np.sqrt(np.mean([abs(v)**2 for v in extract(nc,win,sh,tones)],axis=(0,1)))[active]
                assert np.isfinite(sigma).all() and np.all(sigma>0)
                dates=np.linspace(128,nf-2,32,dtype=int);assert len(set(dates))==32;out=[]
                for dt in dates:
                    X=d['Pilot_Samples'][dt,0];base=X[:,:,:128].astype(float);arr=[[],[]];valid=True
                    for u in range(6):
                        a,b=win[0];lo=a+lag[u];hi=b+lag[u];ss=X[u,:,2*lo:2*hi].astype(float);fac=np.median(np.mean(ss*ss,1)[active]/np.maximum(1.,np.mean(base[u]**2,1)[active]))
                        if fac<2:valid=False
                        h0,h1=extract(X[u],[(l+lag[u],r+lag[u]) for l,r in win],sh,tones,pf);arr[0].append(h0[active]/sigma);arr[1].append(h1[active]/sigma)
                    h0,h1=np.array(arr[0]),np.array(arr[1]);good=valid and np.isfinite(h0).all() and np.all(np.linalg.norm(h0,axis=1)>0)
                    for k in [2,4,6]:
                        inds={2:[1],4:[0,2],6:[0,1,2]}[k];h=np.ascontiguousarray(h0[:k][:,:,inds]);v=np.ascontiguousarray(h1[:k][:,:,inds]);z=dict(stratum=who,frame=int(dt),k=k,active=len(active),valid=int(good),G='',ms='',mean_pair_rho='',phase_increment='',ok=0)
                        if good:
                            rc,_,ti=solve(h);replay(h,rc);z.update(G=rc['G'],ms=ti['total_ns']/1e6,mean_pair_rho=float(np.mean(nominal(h,*np.triu_indices(k,1))[1])),phase_increment=float(np.median(np.angle(np.sum(h.conj()*v,1)))),ok=int(rc['G']<=.1 and ti['total_ns']<=250e6))
                        out.append(z)
                putcsv(path,out);(dest/(who+'.json')).write_text(json.dumps(dict(source=row,active=active.tolist(),lags=list(map(int,lag)),calibration=cal_ids,frames=dates.tolist(),range_hashes=rr.chunks,reference='second disjoint LTS; no latent CSI claim'),indent=2))
                print(who,len(active),'streams',len(out),'decisions/abstentions',flush=True)
        except Exception as exc:
            errors.append(dict(stratum=who,reason=type(exc).__name__+': '+str(exc)[:300]));print(who,errors[-1]['reason'],flush=True)
    (dest/'missing.json').write_text(json.dumps(errors,indent=2))
if __name__=='__main__':run()

