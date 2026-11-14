"""Six figures and machine-readable evidence; profile/block bootstrap units are not individual tones."""
import sys,json,hashlib,csv
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import rankdata,spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent;R=root/'results';F=R/'figures';F.mkdir(exist_ok=True)
rng=np.random.default_rng(19073)
def table(where,pat):
    ps=sorted(where.glob(pat));return pd.concat([pd.read_csv(p) for p in ps],ignore_index=True)
def save(fig,name):
    fig.tight_layout();fig.savefig(F/(name+'.png'),dpi=180);fig.savefig(F/(name+'.svg'));plt.close(fig)
def stat(X,Y):
    a=rankdata(X,axis=1);b=rankdata(Y,axis=1);a-=a.mean(1)[:,None];b-=b.mean(1)[:,None];den=np.sqrt((a*a).sum(1)*(b*b).sum(1));return np.divide((a*b).sum(1),den,out=np.full(len(a),np.nan),where=den>0)
def main():
    g={k:table(R/('grid_'+k),'*.csv') for k in ('native','ray','analytic')}
    g['analytic']=g['analytic'][g['analytic'].k.notna()]
    for t in g.values():assert (t.G>=0).all()
    ng=g['native'];assert len(ng)==6144 and len(g['ray'])==1536 and len(g['analytic'])==6144
    allg=pd.concat([v.assign(campaign=k) for k,v in g.items()]);allg.to_csv(R/'sensitivity_grid.csv',index=False)
    out=[]
    for reg,d in allg.groupby('family'):
        for k in [16,32,64]:
            for db in [-5,0,10,20]:
                v=d[(d.k==k)&(d.db==db)];assert len(v) in (64,128)
                out.append(dict(family=reg,k=k,db=db,n=len(v),median_G=v.G.median(),p95_G=v.G.quantile(.95),median_ms=v.total_ns.median()/1e6))
    pd.DataFrame(out).to_csv(R/'sensitivity_summary.csv',index=False)
    sizes=(16,32,64);fig,ax=plt.subplots(1,2,figsize=(9,3.3))
    for f,d in ng[ng.db==10].groupby('family'):
        ax[0].plot(sizes,[d[d.k==k].G.median() for k in sizes],'-o',label=f)
        ax[1].plot(sizes,[d[d.k==k].total_ns.median()/1e6 for k in sizes],'-o',label=f)
    for a,yl in zip(ax,['Median certified gap (bit/s/Hz)','Median complete time (ms)']):a.set(xlabel='Users',ylabel=yl,xticks=sizes);a.grid(alpha=.22);a.legend(frameon=False)
    save(fig,'F1_native_scale')
    select=table(R/'grid_analytic','transition_*.csv');assert len(select)==1152
    D=select.pivot(index='block',columns='t',values='dominant').values;ts=np.arange(9)/8;B=D[rng.integers(0,128,(10000,128))].mean(1);point=D.mean(0)
    def crossing(A):
        mask=(A[:,:-1]>=.5)&(A[:,1:]>=.5);return np.where(mask.any(1),np.argmax(mask,1)/8,np.inf)
    bb=crossing(B);cc=crossing(point[None,:])[0];active=bb[np.isfinite(bb)];ct=dict(t=np.round(ts,3).tolist(),fraction=point.tolist(),point_crossing=None if not np.isfinite(cc) else float(cc),bootstrap_no_cross_fraction=float((~np.isfinite(bb)).mean()),finite_only_ci=np.quantile(active,[.025,.975]).tolist() if len(active) else [])
    select.to_csv(R/'transition.csv',index=False);(R/'transition_summary.json').write_text(json.dumps(ct,indent=2))
    x=ng[(ng.k==16)&(ng.db==10)].sort_values(['family','block']);assert len(x)==512
    corr={}
    for var in ['posterior','prior']:
        a=x[var].values.reshape(4,128);b=x.loss.values.reshape(4,128);v=[]
        if np.isnan(a).any():
            raise ArithmeticError('undefined diagnostic requires explicit missing-pair handling')
        for z in range(50):
            ix=rng.integers(0,128,(200,4,128));ii=np.arange(4)[None,:,None];v.extend(stat(a[ii,ix].reshape(200,-1),b[ii,ix].reshape(200,-1)))
        corr[var]=dict(rho=float(spearmanr(a.ravel(),b.ravel()).statistic),ci=np.nanquantile(v,[.025,.975]).tolist(),valid=int(np.isfinite(v).sum()))
    (R/'structure_summary.json').write_text(json.dumps(corr,indent=2))
    fig,ax=plt.subplots(1,2,figsize=(9,3.4));ax[0].scatter(x.posterior,x.loss,s=7,alpha=.35,color='#1e686b');ax[0].set(xlabel='Posterior conflict (bit/s/Hz)',ylabel='Exact same-table loss (bit/s/Hz)',title='Native · 16 users, 10 dB');ax[1].plot(ts,point,'-o');ax[1].fill_between(ts,*np.quantile(B,[.025,.975],axis=0),alpha=.2);ax[1].axhline(.5,ls=':',c='k');ax[1].set(xlabel='Frequency-selectivity interpolation',ylabel='Conflict-dominant fraction',ylim=(-.02,1.02),title='128 paired analytic blocks');save(fig,'F2_conflict')
    unc=pd.read_csv(R/'uncertainty.csv');q=unc[unc.db==10];fig,ax=plt.subplots(1,2,figsize=(9,3.5))
    for key,v in q.groupby(['family','arm']):
        for a,col in zip(ax,['G_P','retention']):
            vv=np.sort(v[col]);a.step(vv,np.arange(1,len(vv)+1)/len(vv),where='post',label='/'.join(key))
    for a,cut,label in zip(ax,[.5,.95],['Projected gap (bit/s/Hz)','Certified retention']):a.axvline(cut,ls='--',c='k',lw=1);a.set(xlabel=label,ylabel='Topology ECDF');a.legend(frameon=False,fontsize=8)
    save(fig,'F3_uncertain_CSI')
    ph=pd.read_csv(R/'phase_mse.csv');ag=ph.groupby(['m1','law','M','policy'],as_index=False).agg(MSE=('MSE','mean'),gain=('retained_gain','mean'));ag.to_csv(R/'phase_summary.csv',index=False)
    fig,ax=plt.subplots(1,2,figsize=(9,3.4))
    for a,m in zip(ax,[.7,.9]):
        for p,d in ag[(ag.m1==m)&(ag.law=='von_mises')].groupby('policy'):a.plot(d.M,d.MSE,'-o',label=p)
        a.set(xscale='log',xlabel='Direct phase references',ylabel='Raw scalar MSE',title=f'von Mises truth · m1={m}');a.legend(fontsize=7,frameon=False)
    save(fig,'F4_phase_mismatch')
    nr=pd.read_csv(R/'net_benefit.csv');net=nr.groupby(['family','arm','H','M'],as_index=False).agg(win=('win','mean'),loss=('loss','mean'),indeterminate=('indeterminate','mean'),affordable=('affordable','mean'),mean_lower=('gain_lower','mean'),mean_upper=('gain_upper','mean'));net.to_csv(R/'net_summary.csv',index=False)
    fig,ax=plt.subplots(1,2,figsize=(9,3.4))
    for a,f in zip(ax,['C','UMa']):
        for m,d in net[(net.family==f)&(net.arm=='fixed')&net.M.isin([0,16,256])].groupby('M'):
            d=d[d.affordable==1];a.plot(d.H,d.mean_lower,'-o',label='M='+str(m));a.plot(d.H,d.mean_upper,'--',color=a.lines[-1].get_color())
        a.axhline(0,ls=':',c='k');a.set(xscale='log',xlabel='Stationary horizon (blocks)',ylabel='Mean net-gain bounds (bit/s/Hz)',title=f+' · fixed pilot energy');a.legend(frameon=False,fontsize=8)
    save(fig,'F5_net_benefit')
    fig,ax=plt.subplots(1,2,figsize=(9,3.4));old=root.parent/'Gate_2/results';ota=[]
    for m in ['HUB','LO']:
        t=pd.read_csv(old/f'rice_replay_{m}.csv');rr=json.loads((old/f'rice_replay_{m}.json').read_text());alln=rr['frames']-128
        for a,y in zip(ax,[t.G,t.later_LTS_fixed_action_rate-t.L_proxy]):
            y=np.sort(y);a.step(y,np.arange(1,len(y)+1)/alln,where='post',label=m)
        ota.append(dict(mode=m,independent_captures=1,postprefix_frames=alln,eligible=len(t),active=rr['active_count'],success=int(((t.G<=.1)&(t.ms<=250)).sum()),median_later_change=float((t.later_LTS_fixed_action_rate-t.L_proxy).median())))
    for a,xl in zip(ax,['Proxy certified gap (bit/s/Hz)','Later LTS rate minus early lower (bit/s/Hz)']):a.set(xlabel=xl,ylabel='Fraction of all post-prefix frames');a.legend(frameon=False)
    ax[0].set_xlim(0,.3);save(fig,'F6_Rice_descriptive');pd.DataFrame(ota).to_csv(R/'rice_descriptive.csv',index=False)
    oracle=table(R/'oracle','*.csv');oracle.to_csv(R/'oracle_intervals.csv',index=False);om=oracle.groupby('k').agg(resolved=('resolved','sum'),n=('resolved','size'),median_width=('G_oracle','median'));om.to_csv(R/'oracle_summary.csv')
    print('analyzed',len(allg),'grid cells, exact DP',len(x),'transition',ct['point_crossing'],'Spearman',corr,'oracle',om.to_dict(),flush=True)
if __name__=='__main__':main()

