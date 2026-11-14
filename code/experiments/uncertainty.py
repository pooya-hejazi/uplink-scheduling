"""Evaluate the held-out T4 lane with the same frozen LS action and calibration convention."""
from inputs import *
from campaign import *
from inputs import root as base3
import imperfect,math
from scipy.stats import binomtest
def noise(f,i,h,domain):
    u=int.from_bytes(hashlib.sha256(f'LS-G3|{domain}|{f}|{i}'.encode()).digest()[:8],'little');rng=np.random.default_rng(u);return (rng.normal(size=h.shape)+1j*rng.normal(size=h.shape))/np.sqrt(2)
def rates(h,a):
    pa,p,v=a;S=len(pa);s=np.arange(S);value=0.
    for t in [0,1]:
        d=v[:,t];own=h[pa[:,t],:,s];o=h[pa[:,1-t],:,s]
        value+=np.log1p(p[pa[:,t]]/PT*abs((d.conj()*own).sum(1))**2/((abs(d)**2).sum(1)+p[pa[:,1-t]]/PT*abs((d.conj()*o).sum(1))**2)).sum()
    return value
def high(h,act,eps):
    from enclosures import dotbox,up,dn
    pa,p,v=act;S=len(pa);total=0.
    for s in range(S):
        for j in [0,1]:
            vec=v[s,j];a,b=pa[s,j],pa[s,1-j]
            # Interval dot bounds also enclose the receiver norm squared when both inputs are the receiver.
            vl,vh=dotbox(vec,vec);nhi=up(np.sqrt(vh));d=up(dotbox(vec,h[a,:,s])[1]+up(nhi*eps));o=max(0.,dn(dotbox(vec,h[b,:,s])[0]-up(nhi*eps)))
            den=dn(vl+dn(dn(p[b]/PT)*max(0.,dn(o*o))));num=up(up(p[a]/PT)*up(d*d))
            if den<=0:return np.inf
            total=up(total+logi(up(1+up(num/den)),T,True))
    return total
def run():
    guard();dest=base3/'results';cal=rows(old/'results/calibration_scores.csv');old_rows=rows(old/'results/imperfect.csv');out=[]
    for fam in ['C','UMa']:
        for db in [10,0,20]:
            for arm in ['fixed','scaled']:
                path=dest/f'imperfect_{fam}_{db}_{arm}.csv'
                if path.exists():out.extend(rows(path));continue
                cr=[x for x in cal if x['family']==fam and int(x['db'])==db and x['arm']==arm];assert len(cr)==256
                cf,cp=np.sort([[float(x['T_F']),float(x['T_P'])] for x in cr],axis=0)[250]
                sig=1/np.sqrt(32*(10**(db/10) if arm=='scaled' else 1));ef=np.nextafter(cf*sig,np.inf);ep=np.nextafter(cp*sig,np.inf)
                p0=next(q for q in old_rows if q['family']==fam and int(q['db'])==db and q['arm']==arm);assert abs(ef-float(p0['epsF']))<1e-12 and abs(ep-float(p0['epsP']))<1e-12
                rr=[]
                for i in range(128):
                    raw=np.load(base3/'data'/f'pilot_{fam}_{i:04d}.npz')['h'];h,scale=normalized(raw,32,db);z=noise(fam,i,h,'test');start=now()
                    est,act,f,q=imperfect.stats(h,z,sig);r,_,_=solver.solve(est,'subgrad',eps=ef,proj=ep,action=act);elapsed=(now()-start)/1e6;audit.replay(est,r,ef,ep)
                    u=int(r['U'])/int(r['den']);lf=sum(r['LF_pair'])/Q;lp=sum(r['LP_pair'])/Q;true=rates(h,act)
                    assert (f>cf or lf<=true+1e-10<=u+2e-10) and (q>cp or lp<=true+1e-10)
                    sigma=16*np.log(2);g=(u-lp)/sigma;ret=lp/u;hu=high(est,act,ep)
                    assert q>cp or true<=hu+1e-10
                    a=dict(family=fam,db=db,arm=arm,block=i,raw_sha=digest(h),epsF=ef,epsP=ep,T_F=f,T_P=q,hitF=int(f<=cf),hitP=int(q<=cp),joint=int(f<=cf and q<=cp),G_P=g,retention=ret,ms=elapsed,ok=int(lp>0 and g<=.50 and ret>=.95 and elapsed<=1000),LF=lf/sigma,LP=lp/sigma,U_F=u/sigma,fixed_action_upper=hu/sigma,true_rate=true/sigma,plugin_nominal=rates(est,act)/sigma)
                    rr.append(a)
                putcsv(path,rr);out.extend(rr);print('T4',fam,db,arm,sum(int(x['joint']) for x in rr),sum(int(x['ok']) for x in rr),flush=True)
    putcsv(dest/'uncertainty.csv',out);ss=[]
    for fam in ['C','UMa']:
        for db in [0,10,20]:
            for arm in ['fixed','scaled']:
                d=[v for v in out if v['family']==fam and int(v['db'])==db and v['arm']==arm];j=sum(int(v['joint']) for v in d);p=binomtest(j,128,.95,alternative='less').pvalue
                ss.append(dict(family=fam,db=db,arm=arm,n=len(d),joint=j,F=sum(int(v['hitF']) for v in d),P=sum(int(v['hitP']) for v in d),useful=sum(int(v['ok']) for v in d),pvalue=p,coverage_flag=int(p<.025),median_G=np.median([float(v['G_P']) for v in d]),median_retention=np.median([float(v['retention']) for v in d])))
    putcsv(dest/'uncertainty_summary.csv',ss)
if __name__=='__main__':run()

