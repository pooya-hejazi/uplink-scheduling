"""Produce stratified tables, pilot-only locks and Figure 3 source data from the observed logs."""
import json,sys
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
home=Path(__file__).resolve().parent;res=home/'results'
grid=(.02,.05,.10,.15)
def tab(df,p):df.to_csv(res/p,index=False)
def job():
    a=pd.read_csv(res/'deterministic.csv');assert len(a)==12960 and len(a.drop_duplicates(['family','block','k','db','method','rep']))==len(a) and a.zero_ok.eq(1).all()
    n=pd.read_csv(res/'neural_pilot.csv');assert len(n)==576 and n.zero_ok.eq(1).all()
    v=pd.read_csv(res/'validation.csv');assert len(v)==7*256
    lock=json.loads((res/'selection.json').read_text());cand=lock['candidate'];control=lock['comparator']
    base=pd.concat([a,n]); grouped=base.groupby(['family','block','k','db','method'],as_index=False).median(numeric_only=True)
    idx=['family','k','db','method']; metrics=['G','dc','Sd','endpoint_ns','enclosure_ns','matching_ns','primal_ns','receipt_ns','proposer_ns','total_ns']
    stat=grouped.groupby(idx)[metrics].quantile([.05,.50,.95]).rename_axis(index=idx+['quantile']).reset_index()
    tab(stat,'stratified_distributions.csv');tab(grouped,'block_medians.csv')
    primary=grouped[(grouped.method==cand)&(grouped.db==10)&(grouped.family.isin(['A','B','C','UMa']))]
    op=[];locked=None
    for t in grid:
        frac={}
        for k,cap,need in [(32,250,.80),(64,1000,.60)]:
            sel=primary[primary.k==k];assert len(sel)==96
            rows=[]
            for fam,chunk in sel.groupby('family'):
                passed=(chunk.G.le(t)&chunk.total_ns.le(cap*1e6));cnt=int(passed.sum());rows.append(cnt/len(chunk))
                op.append(dict(tau=t,k=k,family=fam,pass_count=cnt,n=len(chunk),fraction=cnt/len(chunk),cap_ms=cap))
            frac[k]=float(np.mean(rows));op.append(dict(tau=t,k=k,family='equal_profile',pass_count=round(96*frac[k]),n=96,fraction=frac[k],cap_ms=cap))
        if locked is None and frac[32]>=.8 and frac[64]>=.6:locked=t
    tab(pd.DataFrame(op),'known_threshold_grid.csv')
    imp=pd.read_csv(res/'imperfect.csv');assert len(imp)==288 and imp.verified.eq(1).all()
    sec=None;igrid=[]
    for gap in [.20,.50,1,2,4,8]:
        for ratio in [.95,.90,.80,.65,.50]:
            good=True
            for (fam,arm),c in imp[imp.db==10].groupby(['family','arm']):
                b=(c.G_P.le(gap)&c.retention.ge(ratio)&c.ms.le(1000)&c.LP.gt(0));count=int(b.sum());good=good and count>=12
                igrid.append(dict(gap=gap,ratio=ratio,family=fam,arm=arm,count=count,n=len(c)))
            if good and sec is None:sec={'gap':gap,'retention':ratio}
    tab(pd.DataFrame(igrid),'imperfect_threshold_grid.csv')
    irows=imp.groupby(['family','db','arm']).agg(n=('block','size'),G_P_median=('G_P','median'),retention_median=('retention','median'),L_F=('LF','median'),L_P=('LP','median'),U_F=('U','median'),F_hits=('hitF','sum'),P_hits=('hitP','sum'),joint_hits=('joint','sum'),latency_ms=('ms','median')).reset_index()
    tab(irows,'imperfect_by_stratum.csv')
    vals=[]
    for label,d in v.groupby('label'):
        vals.append(dict(label=label,n=len(d),score=np.mean(d.G.to_numpy()[:,None]<=grid),median_G=d.G.median(),median_ms=d.total_ns.median()/1e6,p95_gpu_ms=d.gpu_ms.quantile(.95)))
    tab(pd.DataFrame(vals),'validation_selection.csv')
    nb=grouped[(grouped.method=='neural')&(grouped.db==10)]
    stage=grouped[(grouped.db==10)&(grouped.family.isin(['A','B','C','UMa']))].groupby(['method','k'])[metrics].median().reset_index();tab(stage,'native10_stage_medians.csv')
    # Workload projection is specified in units of the measured matrix; fixed Gate 3 extras are itemized in the report.
    mainhours=a.total_ns.sum()/1e9/3600
    dur=mainhours # actual service time, no I/O or compilation
    sim=a[a.family.isin(['A','B','C','UMa'])].total_ns.sum()/1e9/3600*(128/24)
    ray=a[~a.family.isin(['A','B','C','UMa'])].total_ns.sum()/1e9/3600*(64/12)
    net=n.total_ns.sum()/1e9/3600*128/24*3 # 3 SNRs, only K32/64 extrapolated
    data=dict(known_tau=locked,primary_deadline_ms={'32':250,'64':1000},secondary=sec,native_deterministic_hours=sim,ray_deterministic_hours=ray,neural_K32_64_native_hours=net,det_pilot_hours=dur,forward={str(k):{'p50':float(d.gpu_ms.median()),'p95':float(d.gpu_ms.quantile(.95)),'encoder_p95':float(d.base_gpu_ms.quantile(.95))} for k,d in n.groupby('k')},end_to_end={str(k):{'p50_ms':float(d.total_ns.median()/1e6),'p95_ms':float(d.total_ns.quantile(.95)/1e6)} for k,d in nb.groupby('k')},**lock)
    (res/'thresholds.json').write_text(json.dumps(data,indent=2,allow_nan=False))
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,ax=plt.subplots(1,3,figsize=(10,3.2),layout='constrained')
    ax[0].bar(['Full ball','Projected'],[3.153709814,1.335321612],color=['#96adbd','#15646c'])
    ax[0].set(ylabel='Mean gap (bit/s/Hz)',title='a   Exact Gaussian model',ylim=(0,3.6))
    for j,val in enumerate([3.153709814,1.335321612]):ax[0].text(j,val+.07,f'{val:.3f}',ha='center')
    for fam,col in [('C','#15646c'),('UMa','#9e542e')]:
        for arm,ls in [('fixed','-'),('scaled','--')]:
            d=irows[(irows.family==fam)&(irows.arm==arm)].sort_values('db')
            for aa,key in [(ax[1],'G_P_median'),(ax[2],'retention_median')]:aa.plot(d.db,d[key],linestyle=ls,marker='o',color=col,label=f'{fam}, {arm}')
    ax[1].set(title='b   Median projected gap',ylabel='bit/s/Hz',xlabel='Data SNR (dB)',xticks=[0,10,20]);ax[2].set(title='c   Median retained rate',ylabel='Lₚ / Uꜰ',xlabel='Data SNR (dB)',xticks=[0,10,20],ylim=(0,1.02));ax[2].legend(fontsize=7,loc='lower right')
    fig.savefig(res/'figure3_pilot.svg');fig.savefig(res/'figure3_pilot.png',dpi=160);plt.close(fig)
    print(json.dumps(data,indent=2))
if __name__=='__main__':job()

