"""Action-specific uncertainty calibration and stationary net-benefit sensitivities."""
from uncertainty import *
from grid import source
def action(r):
    import base64
    a=r['receiver'];return np.array(r['pair']),np.array(r['power']),np.frombuffer(base64.b64decode(a[2]),np.dtype(a[0])).reshape(a[1])
def scores(est,h,act,sig):
    diff=(h-est)/sig;F=np.linalg.norm(diff,axis=1).max();pa,_,v=act;s=np.arange(len(pa));P=0.
    for t in (0,1):
        b=v[:,t]/np.linalg.norm(v[:,t],axis=1)[:,None]
        for j in (0,1):P=max(P,float(abs((b.conj()*diff[pa[:,j],:,s]).sum(1)).max()))
    return float(F),P
def run():
    guard();cfg,_,dest,_=which('test');out=[];bands=[];size=[];sample=rows(old/'results/calibration_scores.csv')
    # 4 projected/full calibration events at 1.25% each: both policies have the same pilot information.
    rank=math.ceil(.9875*257);assert rank==254
    with evaluate.worker(cfg['seed']) as pred:
        for fam in ('C','UMa'):
            for arm in ('fixed','scaled'):
                sig=1/np.sqrt(32*(10 if arm=='scaled' else 1));cal=[x for x in sample if x['family']==fam and x['arm']==arm and x['db']=='10'];assert len(cal)==256
                sc=[(float(x['T_F']),float(x['T_P'])) for x in cal];sw=[]
                for i in range(256):
                    h,z=imperfect.sampling(fam,'cal64',i,10);est=np.ascontiguousarray(h+sig*z);r,_,_=solve(est,'hybrid',pred);act=action(r);sw.append(scores(est,h,act,sig))
                cf,cp=np.sort(sc,axis=0)[rank-1];wf,wp=np.sort(sw,axis=0)[rank-1]
                for i in range(128):
                    raw=source(fam,i);h,_=normalized(raw,32,10);z=noise(fam,i,h,'test');est,cold,fc,pc=imperfect.stats(h,z,sig);r,_,_=solve(est,'hybrid',pred);warm=action(r);fw,pw=scores(est,h,warm,sig)
                    inside=(fc<=cf and pc<=cp and fw<=wf and pw<=wp);norm=16*np.log(2);cc=np.nextafter(cp*sig,np.inf);ww=np.nextafter(wp*sig,np.inf)
                    lo0=float(lower(est,cold[1],cold[0],cold[2],np.full((16,2,2),cc),T).sum()/Q/norm);hi0=high(est,cold,cc)/norm
                    lo1=float(lower(est,warm[1],warm[0],warm[2],np.full((16,2,2),ww),T).sum()/Q/norm);hi1=high(est,warm,ww)/norm
                    if inside:
                        assert lo0<=rates(h,cold)/norm+1e-10<=hi0+2e-10 and lo1<=rates(h,warm)/norm+1e-10<=hi1+2e-10
                    bands.append(dict(family=fam,arm=arm,block=i,rank=rank,cold_lo=lo0,cold_hi=hi0,warm_lo=lo1,warm_hi=hi1,cold_actual=rates(h,cold)/norm,warm_actual=rates(h,warm)/norm,joint=int(inside),eps0=cc,eps1=ww))
                    for H in [1,4,16,64,256,1024]:
                        for M in [0,16,64,256,1024]:
                            # Both policies use the same routine pilots. The M>0 arm explicitly charges warm-only deployment refresh.
                            eta0=1-32/256;eta1=max(0,eta0-M*32/(H*256));affordable=int(M*32+H*32<=H*256)
                            low=eta1*lo1-eta0*hi0;hi=eta1*hi1-eta0*lo0
                            out.append(dict(family=fam,arm=arm,block=i,H=H,M=M,affordable=affordable,gain_lower=low,gain_upper=hi,win=int(affordable and low>1e-5),loss=int(affordable and hi< -1e-5),indeterminate=int(affordable and low<=1e-5 and hi>=-1e-5)))
                print('net',fam,arm,flush=True)
    putcsv(dest/'policy_rate_bands.csv',bands);putcsv(dest/'net_benefit.csv',out)
if __name__=='__main__':run()

