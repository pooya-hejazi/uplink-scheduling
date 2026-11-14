"""Make the six vector figures from the supplied source data. --collect checks the original release hashes first."""
from pathlib import Path
import sys, hashlib, json, math
from fractions import Fraction as F
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import patches, lines
from matplotlib.ticker import PercentFormatter, MaxNLocator
from scipy.stats import spearmanr
dst=Path(__file__).resolve().parent
src=dst/'source_data';src.mkdir(exist_ok=True)
out=dst/'figures';out.mkdir(exist_ok=True)
def collect():
    manifests={}
    def read(g,name):
        root=dst.parent/f'Gate_{g}'
        if g not in manifests:
            manifests[g]={v.replace('\\','/').lstrip('*'):h for h,v in (s.strip().split(None,1) for s in (root/'SHA256SUMS').read_text().splitlines() if s.strip())}
        path=root/name;assert hashlib.sha256(path.read_bytes()).hexdigest()==manifests[g][root.name+'/'+name],name
        return pd.read_csv(path) if name.endswith('.csv') else path.read_text(encoding='utf-8')
    def put(name,d): d.to_csv(src/(name+'.csv'),index=False)
    ledger=read('3','results/conflict_attribution.csv').query("method=='det'")
    put('fig1_ledger',ledger[['family','block','k','G','term1','term2','term3','term4']])
    si=read('3','results/sensitivity_grid.csv');put('fig2_label_loss',si.query("campaign=='native' and k==16 and db==10")[['family','block','loss','posterior','prior','dp_H','matched_A','R']])
    u=read('3','results/uncertainty_summary.csv');put('fig3_uncertainty',u)
    # Analytic expectations and outward enclosures are transcribed at their published precision.
    log=read('1','verification.log');assert '3.153709' in log and '1.335321' in log
    put('fig3_gaussian',pd.DataFrame({'endpoint':['upper','vector lower','projected lower'],'mean':[15.128168313,11.974458499,13.792846701]}))
    put('fig4_decisions',read('3','results/block_decisions.csv'))
    for name,original in [('fig4_methods','method_summary'),('fig5_horizons','net_summary'),('fig6_capture_counts','rice_descriptive')]:put(name,read('3','results/'+original+'.csv'))
    for m in ['HUB','LO']:
        h=read('2','results/rice_replay_'+m+'.csv')
        put('fig6_'+m,h[['frame','G','L_proxy','later_LTS_fixed_action_rate','ms']])
    files=['Gate_1/verification.log','Gate_2/results/rice_replay_HUB.csv','Gate_2/results/rice_replay_LO.csv']+['Gate_3/results/'+x+'.csv' for x in ['conflict_attribution','sensitivity_grid','uncertainty_summary','block_decisions','method_summary','net_summary','rice_descriptive']]
    for filename,original in [('fig4_compute','compute_summary'),('fig4_exact_intervals','exact_binomial_intervals'),('fig5_absolute_rates','absolute_rate_summary'),('fig5_decomposition','gap_decomposition_summary'),('fig5_horizon_intervals','horizon_intervals'),('fig6_calibration_HUB','hardware_calibration_HUB'),('fig6_calibration_LO','hardware_calibration_LO')]:
        path=dst/'revision/reviewer_data'/(original+'.csv')
        put(filename,pd.read_csv(path));files.append(path.relative_to(dst.parent).as_posix())
    (src/'input_sha256.txt').write_text(''.join(hashlib.sha256((dst.parent/p).read_bytes()).hexdigest()+'  '+p+'\n' for p in files))
if '--collect' in sys.argv:collect()
def data(n):return pd.read_csv(src/(n+'.csv'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.4,'axes.titlesize':9.5,'axes.titleweight':'semibold','axes.labelsize':8.4,'xtick.labelsize':7.4,'ytick.labelsize':7.4,'legend.fontsize':7.2,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#607080','axes.labelcolor':'#1b3242','axes.titlecolor':'#102838','text.color':'#183444','xtick.color':'#3e5565','ytick.color':'#3e5565','pdf.fonttype':42,'svg.fonttype':'none','axes.linewidth':.65,'lines.linewidth':1.65,'savefig.facecolor':'white','figure.facecolor':'white'})
navy='#244a70'; cyan='#007e83'; amber='#c6682e'; purple='#7967a6'; grey='#89969d';ink='#173546'
cs=[navy,cyan,amber,purple]; fams=['A','B','C','UMa'];methods=['det','hybrid','standalone','legacy']
def title(a,label,t):a.set_title(label,loc='left',pad=8,fontweight='bold')
def tidy(a,axis='y'):a.grid(axis=axis,color='#dfe6e7',linewidth=.6);a.set_axisbelow(True);a.tick_params(length=3)
def save(f,n):
    f.savefig(out/(n+'.pdf'),bbox_inches='tight',pad_inches=.055,metadata={'Title':n.replace('_',' '),'Creator':'Matplotlib; numerical source data supplied'})
    f.savefig(out/(n+'.svg'),bbox_inches='tight',pad_inches=.055)
    plt.close(f)
def two():return plt.subplots(2,2,figsize=(7.03,5.05),layout='constrained',gridspec_kw={'wspace':.075,'hspace':.12})
def ec(a,values,color,label=None,total=None,**kw):
    v=np.sort(np.asarray(values));a.step(np.r_[min(0.,v[0]),v],np.r_[0,np.arange(1,len(v)+1)]/(len(v) if total is None else total),where='post',color=color,label=label,**kw)
def pct(a):a.yaxis.set_major_formatter(PercentFormatter(1,decimals=0));a.set_ylim(-.015,1.03)
def bars_legend(a,colors,labels,**kw):return a.legend(handles=[patches.Patch(color=c,label=s) for c,s in zip(colors,labels)],frameon=False,**kw)
def pipes():
    f=plt.figure(figsize=(7.05,4.28),layout='constrained')
    gs=f.add_gridspec(2,2,height_ratios=[1.05,1])
    a=f.add_subplot(gs[0,:]);a.set_xlim(0,1);a.set_ylim(0,1);a.axis('off')
    title(a,'a','From paired uplink signals to a certified rate interval')
    a.text(.013,.90,'Users',weight='bold')
    a.text(.128,.90,'Labelled tones',weight='bold')
    a.text(.357,.90,'Array',weight='bold')
    for pair,y,tone,col in [(('1','2'),.69,1,purple),(('3','4'),.29,2,amber)]:
        for user,dy in zip(pair,[.085,-.085]):
            a.plot([.055,.130],[y+dy,y],color=col,lw=1.2)
            a.plot(.046,y+dy,'o',ms=12,mfc='white',mec=col)
            a.text(.046,y+dy,user,ha='center',va='center',fontsize=7.4)
        a.text(.143,y,f'Tone {tone}',va='center',color=col,weight='bold')
        x=np.linspace(.234,.351,90)
        a.plot(x,y+.039*np.sin((x-x[0])/(x[-1]-x[0])*2*np.pi*(tone+1)),color=col,lw=1.25)
    a.plot([.379,.379],[.22,.76],color=ink,lw=1)
    for y in np.linspace(.22,.76,5):
        a.plot(.379,y,'s',color=ink,ms=4.5)
    a.plot([.379,.432],[.49,.49],color=ink,lw=1)
    a.plot(.434,.49,'o',ms=14,mfc='white',mec=ink,ls='none')
    a.plot(.434,.49,'.',color=ink,ms=4)
    a.text(.439,.90,'Channel estimate and uncertainty ball',weight='bold')
    a.plot([.434,.434],[.82,.56],ls=':',color=grey,lw=.8)
    for y,col,heading,detail in [(.69,navy,r'Oracle ceiling  $U$','Continuous power boxes for every pair and tone\nChecked odd-set (blossom) dual'),
                                 (.31,cyan,r'Achievable floor  $L$','Hungarian tone assignment for pairs from the pool\nChosen powers and fixed MMSE filters')]:
        a.annotate('',(.488,y),(.449,.49),arrowprops=dict(arrowstyle='-|>',lw=1.25,color=col))
        a.text(.498,y+.05,heading,color=col,weight='bold',va='center')
        a.text(.498,y-.037,detail,va='top',fontsize=7.9)
    a.text(.013,.045,'Example feasible assignment',fontsize=7.9)
    a.text(.498,.045,r'Four-term gap  $G=(U-L)/(S\,\ln 2)$',weight='bold',fontsize=8.1)
    b=f.add_subplot(gs[1,0]);c=f.add_subplot(gs[1,1]);d=data('fig1_ledger');r=d.query("family=='A' and block==0 and k==32").iloc[0];v=r[['term1','term2','term3','term4']].astype(float).to_numpy()
    assert abs(v.sum()-r.G)<1e-10
    title(b,'b','One 32-user interval');parts=['Matching','Tone conflict','Unused power','Rate enclosure']
    for i,(z,col) in enumerate(zip(v,cs)):
        label=f'{z:.3g}'
        if 'e' in label:
            coefficient,exponent=label.split('e')
            label='$'+coefficient+rf'\times10^{{{int(exponent)}}}$'
        b.barh(3-i,z,color=col,height=.47)
        b.text(max(.001,z)+.00055,3-i,label,va='center',fontsize=7.1)
    b.set_yticks(range(4),parts[::-1]);b.set_xlim(0,.042);b.set_xlabel('Contribution (bit/s/Hz)');tidy(b,'x');b.text(.99,.68,f'Sum = {r.G:.4f}',transform=b.transAxes,ha='right',fontsize=7.7)
    title(c,'c','What remains on average');strong=d.groupby('k')[[f'term{j}' for j in range(1,5)]].mean()
    for i,(k,row) in enumerate(strong.iterrows()):
        s=0
        for z,col in zip(row,cs):c.barh(i,z,left=s,color=col,height=.44);s+=z
        c.text(s+.001,i,f'{s:.3f}',va='center',fontsize=7.25)
    c.set_yticks([0,1],['32 users','64 users']);c.set_ylim(1.67,-.64);c.set_xlim(0,strong.sum(axis=1).max()*1.23);c.set_xlabel('Mean gap (bit/s/Hz)');tidy(c,'x');save(f,'fig1_architecture')
def conflict_source_tables():
    import itertools
    uv=[(F(1),F(0)),(F(0),F(1)),(F(3,5),F(4,5)),(F(-4,5),F(3,5))]
    pairs=list(itertools.combinations(range(4),2))
    exact=[[sum(x*y for x,y in zip(o[i],o[j]))**2 for o in (uv,[uv[t] for t in (0,2,1,3)])] for i,j in pairs]
    r=np.array([[float(value) for value in row] for row in exact])
    rows=[dict(user_i=i+1,user_j=j+1,tone=s+1,squared_correlation=float(exact[e][s]),exact_fraction=str(exact[e][s])) for e,(i,j) in enumerate(pairs) for s in range(2)]
    pd.DataFrame(rows).to_csv(src/'fig2_correlations.csv',index=False)
    t=np.linspace(-.36,.36,81);base=4*np.log(2);ref=2*np.log(91/25)
    pd.DataFrame(dict(tone_price_difference_nats=t,relaxed_upper_nats=base+abs(t),best_labelled_rate_nats=np.full_like(t,ref))).to_csv(src/'fig2_price_grid.csv',index=False)
    assert r.shape==(6,2) and len(t)==81 and np.isclose(min(base+abs(t))-ref,2*np.log(100/91))
    return r,t,base,ref

def conflict():
    f,ax=two();a,b,c,d=ax.flat;title(a,'a','Disjoint pairs can prefer the same tone')
    # Entries visualized as orthogonal/nonorthogonal; labels are exact squared correlations derived from the channels.
    r,t,base,ref=conflict_source_tables()
    a.imshow(r.T,aspect='auto',vmin=0,vmax=1,cmap='Blues');a.set_xticks(range(6),['12','13','14','23','24','34']);a.set_yticks([0,1],['Tone 1','Tone 2']);a.set_xlabel('User pair')
    for i,j in np.ndindex(r.T.shape):a.text(j,i,f'{r[j,i]:.2f}',ha='center',va='center',color='white' if r[j,i]>.55 else ink,fontsize=8.5)
    title(b,'b','Irreducible four-user loss');b.plot(t,base+abs(t),color=navy,label='Price relaxation');b.axhline(ref,color=cyan,label='Best labelled schedule');b.vlines(0,ref,base,color=amber,lw=2.5);b.set_xlabel(r'Tone-price difference $\beta_2-\beta_1$ (nats)');b.set_ylabel('Aggregate nats');b.legend(frameon=False,fontsize=6.9);tidy(b)
    tab=data('fig2_label_loss');assert len(tab)==512
    for q,key,l,t in [(c,'posterior','c','Conflict on selected pairs'),(d,'prior','d','Range over all candidates')]:
        title(q,l,t);q.scatter(tab[key],tab.loss,c=cyan if key=='posterior' else purple,alpha=.42,edgecolors='none',s=11,rasterized=False);q.text(.94,.91,r'$\rho$ = '+f'{spearmanr(tab[key],tab.loss).statistic:.3f}',ha='right',transform=q.transAxes);q.set_xlabel(('Posterior conflict' if key=='posterior' else 'Range bound')+' (bit/s/Hz)');q.set_ylabel('Exact table loss (bit/s/Hz)');tidy(q)
    save(f,'fig2_conflict')
def uncertainty():
    f,ax=two();a,b,c,d=ax.flat;t=data('fig3_gaussian');v=t['mean'].values;title(a,'a','One oracle ceiling, two receiver floors')
    for i,z in enumerate(v[1:]):
        a.plot([z,v[0]],[1-i]*2,color=cs[i],lw=3.5,solid_capstyle='round');a.scatter([z,v[0]],[1-i]*2,c=[cs[i],ink],s=28,zorder=3);a.text((z+v[0])/2,1-i+.2,f'Gap {v[0]-z:.3f}',ha='center',fontsize=8)
    a.set_yticks([0,1],['Projected','Full vector']);a.set_ylim(-.55,1.55);a.set_xlim(11.5,15.55);a.set_xlabel('Mean endpoint (bit/s/Hz)');tidy(a,'x')
    z=data('fig3_uncertainty')
    for q,(field,l,tit,yl) in zip((b,c),[('median_G','b','Gap at the implemented receiver','Median gap (bit/s/Hz)'),('median_retention','c','How much of the ceiling is retained?','Median lower / upper')]):
        title(q,l,tit)
        for family,col in [('C',navy),('UMa',cyan)]:
            for arm,sty,mark in [('fixed','--','o'),('scaled','-','s')]:
                w=z[(z.family==family)&(z.arm==arm)];q.plot(w.db,w[field],sty,marker=mark,ms=3.7,color=col,label=('CDL-C' if family=='C' else family)+' '+arm)
        q.set_xticks([0,10,20]);q.set_xlabel('SNR (dB)');q.set_ylabel(yl);q.axhline(.5 if field=='median_G' else .95,color=grey,lw=.85,ls=':');tidy(q)
    b.legend(frameon=False,ncol=2,fontsize=6.6)
    w=z[z.db==10];title(d,'d','Utility and coverage are distinct');idx=np.arange(4);w=w.set_index(['family','arm']).loc[[('C','fixed'),('C','scaled'),('UMa','fixed'),('UMa','scaled')]].reset_index();d.bar(idx-.18,w.useful,.34,color=navy,label='Useful interval');d.bar(idx+.18,w.joint,.34,color=amber,label='Joint coverage')
    d.set_xticks(idx,['CDL-C\nfixed','CDL-C\nscaled','UMa\nfixed','UMa\nscaled']);d.set_ylim(0,161);d.set_yticks([0,32,64,96,128]);d.set_ylabel('Topologies out of 128');tidy(d);d.legend(frameon=False,loc='upper center',ncol=2,fontsize=6.8);save(f,'fig3_uncertainty')
def scaling():
    f,ax=two();a,b,c,d=ax.flat;v=data('fig4_decisions');assert len(v)==4096
    for z,k,letter in [(a,32,'a'),(b,64,'b')]:
        title(z,letter,str(k)+' users')
        for key,label,col,sty in zip(methods,['Deterministic search','Learned warm start','Network only','Subgradient baseline'],cs,['-','--','-.',':']):
            g=v.query('k==@k and method==@key');ec(z,g.loc[g.ms<=(250 if k==32 else 1000),'G'],col,label,total=len(g),ls=sty)
        z.axvline(.15,color=grey,lw=1,ls=':');z.set_xlim(0,.26);z.set_xlabel('Certified gap (bit/s/Hz)');z.set_ylabel('Fraction useful by deadline');pct(z);tidy(z)
    a.legend(frameon=False,loc='lower right',fontsize=6.8)
    title(c,'c','Receipt time, by method');ts=data('fig4_methods')
    for i,key in enumerate(methods):
        z=ts.query('method==@key').sort_values('k')
        for j,(r,col) in enumerate(zip(z.itertuples(),[navy,amber])):
            y=3-i+.12*(-1 if j else 1);c.plot([r.median_ms,r.p95_ms],[y,y],color=col,lw=1.5);c.plot(r.median_ms,y,'o',color=col,ms=4);c.plot(r.p95_ms,y,'|',color=col,ms=7)
    c.set_yticks(range(4),['Subgradient baseline','Network only','Learned warm start','Deterministic search']);c.set_xscale('log');c.set_xlabel('Median to 95th percentile (ms)');bars_legend(c,[navy,amber],['32','64 users'],loc='upper right',ncol=2,fontsize=6.4);c.set_ylim(-.45,3.6);tidy(c,'x')
    title(d,'d','');comparison=data('fig4_compute')
    for method,col,label in [('det',navy,'Deterministic search'),('extra',purple,'Three extra iterations'),('hybrid',cyan,'Learned warm start')]:
        z=comparison[comparison.method==method]
        for k,marker in [(32,'o'),(64,'s')]:
            r=z[z.k==k].iloc[0];d.scatter(r.median_ms,r.median_G,color=col,marker=marker,s=30,label=label if k==32 else None)
    d.set_xlabel('Median complete time (ms)');d.set_ylabel('Median gap (bit/s/Hz)');d.legend(frameon=False,fontsize=6.0,loc='lower right');tidy(d)
    save(f,'fig4_scaling')
def phase():
    f,ax=two();a,b,c,d=ax.flat
    rates=data('fig5_absolute_rates')
    order=['det','hybrid','standalone','legacy','cold','equal_match','sequential']
    labels=['Deterministic search','Learned warm start','Network only','Subgradient baseline','Zero-price baseline','Matching + power refinement','Sequential equal-power']
    title(a,'a','')
    for offset,k,col in [(-.14,32,navy),(.14,64,amber)]:
        z=rates[rates.k==k].set_index('method').loc[order]
        for j,r in enumerate(z.itertuples()):
            a.plot([r.L_median,r.U_median],[j+offset]*2,color=col,lw=1.3)
            a.scatter(r.L_median,j+offset,color=col,s=14,zorder=3)
            a.plot(r.U_median,j+offset,'|',color=col,ms=5)
        a.axvline(z.U_best_median.iloc[0],color=col,ls=':',lw=.8)
    a.set_yticks(range(7),labels,fontsize=6.2);a.invert_yaxis();a.set_xlabel('Rate (bit/s/Hz)')
    bars_legend(a,[navy,amber],['32 users','64 users'],loc='lower right',fontsize=6.1);tidy(a,'x')
    title(b,'b','');z=data('fig5_decomposition')
    for off,col,lo,hi,lab in [(-.12,navy,'slack_lo','slack_hi','Upper-bound slack'),(.12,cyan,'suboptimality_lo','suboptimality_hi','Action suboptimality')]:
        for j,r in enumerate(z.to_dict('records')):
            b.plot([r[lo],r[hi]],[j+off]*2,color=col,lw=2,label=lab if j==0 else None)
            b.plot([r[lo],r[hi]],[j+off]*2,'|',color=col,ms=6)
    b.set_yticks(range(5),['2','4','6','8','16']);b.invert_yaxis();b.set_ylabel('Users');b.set_xlabel('Mean contribution (bit/s/Hz)');b.legend(frameon=False,fontsize=6.1);tidy(b,'x')
    h=data('fig5_horizon_intervals');Hs=[1,4,16,64,256,1024];title(c,'c','')
    for (fam,arm),col,lab,sty in zip([('C','fixed'),('C','scaled'),('UMa','fixed'),('UMa','scaled')],cs,['CDL-C fixed','CDL-C scaled','UMa fixed','UMa scaled'],['-','--','-.',':']):
        z=h.query('family==@fam and arm==@arm and M==0').sort_values('H')
        c.plot(z.H,z.wins/z.n,sty,marker='o',ms=2.8,color=col,label=lab)
        c.fill_between(z.H,z.lower,z.upper,color=col,alpha=.12,lw=0)
    c.set_xscale('log',base=4);c.set_xticks(Hs,list(map(str,Hs)));c.set_xlabel('Stationary horizon (blocks)');c.set_ylabel('Fraction with certified gain');pct(c);tidy(c);c.legend(frameon=False,fontsize=5.8,ncol=2,loc='center right')
    title(d,'d','');q=h.query("family=='UMa' and arm=='scaled'").copy();q['fraction']=q.wins/q.n
    m=q.pivot(index='M',columns='H',values='fraction');ok=q.pivot(index='M',columns='H',values='affordable')
    arr=np.ma.array(m.values,mask=ok.values<1);cm=plt.colormaps['Blues'].copy();cm.set_bad('#e4e5e3');d.imshow(arr,aspect='auto',vmin=0,vmax=1,cmap=cm)
    d.set_xticks(range(6),[str(x) for x in m.columns]);d.set_yticks(range(5),[str(x) for x in m.index]);d.set_xlabel('Stationary horizon (blocks)');d.set_ylabel('Extra pilot blocks')
    for i,j in np.ndindex(arr.shape):d.text(j,i,'-' if arr.mask[i,j] else f'{100*m.iloc[i,j]:.0f}%',ha='center',va='center',fontsize=6.5,color='white' if m.iloc[i,j]>.55 and not arr.mask[i,j] else ink)
    save(f,'fig5_phase')

def hardware():
    f,ax=two();a,b,c,d=ax.flat
    for panel,letter in zip(ax.flat,'abcd'):title(panel,letter,'')
    summaries=[]
    for j,(name,col) in enumerate([('HUB',navy),('LO',amber)]):
        old=data('fig6_'+name);valid=old[np.isfinite(old.G)];timely=valid[valid.ms<=250]
        z=data('fig6_calibration_'+name);test=z[z['split']=='test'];summaries.append(test)
        ec(a,timely.G,col,name+' certificate',total=1873)
        ec(a,z.equal_power_reference_gap,col,name+' fixed-power reference',total=1873,ls='--')
        dif=(valid.later_LTS_fixed_action_rate-valid.L_proxy).dropna().sort_values().to_numpy()
        b.step(dif,np.arange(1,len(dif)+1)/len(dif),where='post',color=col,label=name)
        for offset,field in zip([-.22,0,.22],['covered_floor','covered_interval','joint']):
            c.bar(j+offset,test[field].mean(),.20,color=col,alpha={-.22:1,0:.65,.22:.30}[offset])
        lo=test.LP.median();hi=test.U_F.median();later=test.later_rate.median()
        d.plot([lo,hi],[j,j],color=col,lw=3)
        d.plot([lo,hi],[j,j],'|',color=col,ms=12)
        d.scatter(later,j,marker='D',color=ink,s=28,zorder=3)
        d.text((lo+hi)/2,j+.17,f'{lo:.2f} to {hi:.2f}',ha='center',fontsize=7)
    a.axvline(.1,color=grey,ls=':',lw=1);a.set_xlim(0,.30);a.set_xlabel('Early-input gap (bit/s/Hz)');a.set_ylabel('Fraction of 1,873 frames');pct(a);tidy(a);a.legend(frameon=False,loc='lower right',fontsize=5.9)
    b.axvline(0,color=grey,ls=':',lw=1);b.set_xlabel('Later rate − early floor (bit/s/Hz)');b.set_ylabel('Fraction of eligible frames');pct(b);tidy(b);b.legend(frameon=False)
    c.set_xticks([0,1],['HUB (1,614)','LO (1,513)']);c.set_ylabel('Observed test-frame fraction');pct(c);tidy(c)
    c.legend(handles=[patches.Patch(color=grey,alpha=v,label=l) for v,l in [(1,'Projected floor'),(.65,'Combined interval'),(.3,'Both residual events')]],frameon=False,fontsize=6,loc='lower center')
    d.set_yticks([0,1],['HUB','LO']);d.set_ylim(-.4,1.5);d.set_xlim(left=0);d.set_xlabel('Median rate endpoint (bit/s/Hz)');tidy(d,'x')
    d.scatter([],[],marker='D',color=ink,label='Median later-LTS rate');d.legend(frameon=False,fontsize=6.5,loc='upper right')
    save(f,'fig6_hardware')
if __name__=='__main__':
    for fn in (pipes,conflict,uncertainty,scaling,phase,hardware):fn()
    print('Six figures drawn from checked, disclosable sources.')

