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
    for filename,original in [('fig4_time_control','time_control_summary'),('fig4_paired_tests','time_control_paired_tests'),('fig5_decomposition_distribution','decomposition_distribution'),('fig5_integer_table_reference','integer_table_reference'),('fig6_phase_HUB','hardware_phase_HUB'),('fig6_phase_LO','hardware_phase_LO'),('fig6_comparison_HUB','hardware_comparison_HUB'),('fig6_comparison_LO','hardware_comparison_LO')]:
        path=dst/'revision/round2_data'/(original+'.csv')
        put(filename,pd.read_csv(path));files.append(path.relative_to(dst.parent).as_posix())
    for mode in ('HUB', 'LO'):
        files.extend([f'Gate_4/source_data/fig6_payload_{mode}.csv',
                      f'Gate_4/supplementary/data/payload_frames_{mode}.csv',
                      f'Gate_4/revision/payload_data/payload_controls_{mode}.json'])
    files.extend(['Gate_4/supplementary/data/seven_method_call_times.csv',
                  'Gate_4/supplementary/data/lo_alignment_sensitivity.csv'])
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
def panel_heading(ax, letter, text):
    ax.set_title(rf'$\mathbf{{{letter}}}$   {text}', loc='left', pad=8,
                 fontsize=9, fontweight='semibold', color=ink)


def uplink_model(ax):
    ax.set(xlim=(0, 170), ylim=(0, 49), aspect='equal')
    ax.axis('off')
    panel_heading(ax, 'a', 'Two users share each tone at the receive array')
    ax.text(1, 45, 'Transmitting users', color=ink, fontsize=8, weight='bold')
    ax.text(65, 45, 'Receive array', color=ink, fontsize=8, weight='bold')
    ax.text(115, 45, 'Per-tone linear reception', color=ink, fontsize=8, weight='bold')
    ax.text(65, 5, '16 elements shown', fontsize=7, color=ink)
    for tone, ys, color, shade, style in [(1, (36, 29), navy, '#eef3f7', '-'),
                                          (2, (18, 11), cyan, '#e8f4f1', '--')]:
        cy = sum(ys) / 2
        ax.add_patch(patches.FancyBboxPatch((.5, cy-6.8), 29, 13.6, boxstyle='round,pad=.2,rounding_size=1.5',
                                            facecolor=shade, edgecolor='none'))
        ax.text(1.7, cy, f'Tone {tone}', va='center', fontsize=7.3, weight='bold', color=color)
        for row, y in enumerate(ys):
            user = (tone-1)*2+row+1
            ax.text(15.5, y, rf'$u_{user}$', fontsize=8.4, ha='center', va='center', color=color)
            ax.add_patch(patches.FancyBboxPatch((22, y-1.6), 4, 3.2, boxstyle='round,pad=.13,rounding_size=.45',
                                                facecolor='white', edgecolor=color, linewidth=1))
            ax.plot([24.6,24.6],[y+1.65,y+3.25],color=color,lw=1,solid_capstyle='round')
            ax.annotate('', xy=(63.3,25.6), xytext=(27.2,y),
                        arrowprops=dict(arrowstyle='-|>', lw=1.05, linestyle=style,
                                        color=color, mutation_scale=6, shrinkA=0, shrinkB=0))
        ax.plot([87,94,94,104], [25.5,25.5,cy,cy], linestyle=style, color=color, lw=1.2)
        ax.text(106, cy, rf'$\mathbf{{y}}_{tone}$', fontsize=9.4, color=color, ha='left', va='center')
        for row, y in enumerate(ys):
            user = (tone-1)*2+row+1
            ax.plot([113,116,119], [cy,cy,y], color=color, lw=.9)
            ax.add_patch(patches.FancyBboxPatch((119, y-2.5), 16.5, 5, boxstyle='round,pad=.1,rounding_size=.8',
                                                facecolor=shade, edgecolor=color, linewidth=.8))
            ax.text(127.1, y, rf'$\mathbf{{v}}_{user}^{{\mathrm{{H}}}}$', ha='center', va='center', fontsize=8.2, color=color)
            ax.annotate('', xy=(141,y), xytext=(135.6,y), arrowprops=dict(arrowstyle='-|>', lw=.8, color=color, mutation_scale=6))
            ax.text(142, y, rf'$z_{user}=\mathbf{{v}}_{user}^{{\mathrm{{H}}}}\mathbf{{y}}_{tone}$',
                    va='center', fontsize=8.5, color=ink)
    # A drawn array illustrates simultaneous reception across all elements.
    origin = np.array([65., 14.])
    across, upward = np.array([4.9,1.05]), np.array([0.,4.65])
    corners = [origin, origin+4*across, origin+4*across+4*upward, origin+4*upward]
    ax.add_patch(patches.Polygon(corners, closed=True, facecolor='#e4eced', edgecolor=ink, lw=1.2))
    for i in range(4):
        for j in range(4):
            xy = origin+(i+.5)*across+(j+.5)*upward
            ax.add_patch(patches.Ellipse(xy, 3.0, 2.7, angle=11, facecolor='white', edgecolor=ink, lw=.9))
    ax.plot([74,74,77,77],[16,11,11,16.8],color=ink,lw=1,zorder=0)
    ax.plot([71.5,79.4],[11,11],color=ink,lw=1.2)
    ax.text(1, .3, r'$\mathbf{y}_s=\sqrt{p_i}\,\mathbf{h}_{is}x_i+\sqrt{p_j}\,\mathbf{h}_{js}x_j+\mathbf{n}_s$',
            fontsize=9, color=ink)


def pipes():
    f=plt.figure(figsize=(7.12,4.62),layout='constrained')
    gs=f.add_gridspec(2,2,height_ratios=[1.25,1])
    uplink_model(f.add_subplot(gs[0,:]))
    b=f.add_subplot(gs[1,0]);c=f.add_subplot(gs[1,1]);d=data('fig1_ledger');r=d.query("family=='A' and block==0 and k==32").iloc[0];v=r[['term1','term2','term3','term4']].astype(float).to_numpy()
    assert abs(v.sum()-r.G)<1e-10
    panel_heading(b,'b','One 32-user decision');parts=['Matching','Tone conflict','Unused power','Rate enclosure']
    for i,(z,col) in enumerate(zip(v,cs)):
        label=f'{z:.3g}'
        if 'e' in label:
            coefficient,exponent=label.split('e')
            label='$'+coefficient+rf'\times10^{{{int(exponent)}}}$'
        b.barh(3-i,z,color=col,height=.47)
        b.text(max(.001,z)+.00055,3-i,label,va='center',fontsize=7.1)
    b.set_yticks(range(4),parts[::-1]);b.set_xlim(0,.042);b.set_xlabel('Contribution (bit/s/Hz)');tidy(b,'x');b.text(.99,.68,f'Sum = {r.G:.4f}',transform=b.transAxes,ha='right',fontsize=7.7)
    panel_heading(c,'c','Mean gap over 512 topologies');strong=d.groupby('k')[[f'term{j}' for j in range(1,5)]].mean()
    for i,(k,row) in enumerate(strong.iterrows()):
        s=0
        for z,col in zip(row,cs):c.barh(i,z,left=s,color=col,height=.44);s+=z
        c.text(s+.001,i,f'{s:.3f}',va='center',fontsize=7.25)
    c.set_yticks([0,1],['32 users','64 users']);c.set_ylim(1.67,-.64);c.set_xlim(0,strong.sum(axis=1).max()*1.23);c.set_xlabel('Mean gap (bit/s/Hz)');tidy(c,'x');save(f,'fig1_architecture')
def conflict_source_tables():
    import itertools
    uv=[(F(1),F(0)),(F(0),F(1)),(F(3,5),F(4,5)),(F(-4,5),F(3,5))]
    pairs=list(itertools.combinations(range(4),2))
    channels = (uv, [uv[t] for t in (0,2,1,3)])
    exact=[[sum(x*y for x,y in zip(o[i],o[j]))**2 for o in channels] for i,j in pairs]
    pd.DataFrame([(s, u, str(x), str(y)) for s, vectors in enumerate(channels, 1)
                  for u, (x,y) in enumerate(vectors, 1)],
                 columns=['tone','user','first_coordinate','second_coordinate']).to_csv(src/'fig2_channels.csv', index=False)
    r=np.array([[float(value) for value in row] for row in exact])
    rows=[dict(user_i=i+1,user_j=j+1,tone=s+1,squared_correlation=float(exact[e][s]),exact_fraction=str(exact[e][s])) for e,(i,j) in enumerate(pairs) for s in range(2)]
    pd.DataFrame(rows).to_csv(src/'fig2_correlations.csv',index=False)
    t=np.linspace(-.36,.36,81);base=4*np.log(2);ref=2*np.log(91/25)
    pd.DataFrame(dict(tone_price_difference_nats=t,relaxed_upper_nats=base+abs(t),best_labelled_rate_nats=np.full_like(t,ref))).to_csv(src/'fig2_price_grid.csv',index=False)
    assert r.shape==(6,2) and len(t)==81 and np.isclose(min(base+abs(t))-ref,2*np.log(100/91))
    return r,t,base,ref,channels

def conflict():
    f,ax=plt.subplots(3,2,figsize=(7.12,7.07),layout='constrained',
                      gridspec_kw={'height_ratios':[.74,.91,1],'wspace':.08,'hspace':.11})
    r,t,base,ref,channels=conflict_source_tables()
    for tone,(plot,vectors) in enumerate(zip(ax[0],channels),1):
        panel_heading(plot,'ab'[tone-1],f'Channel directions on tone {tone}')
        plot.set(xlim=(-1.32,1.35),ylim=(-.27,1.28),aspect='equal')
        plot.axis('off')
        angle=np.linspace(0,np.pi,160)
        plot.plot(np.cos(angle),np.sin(angle),lw=.8,color='#bac7cc')
        plot.plot([-1.18,1.18],[0,0],color='#bdc9cd',lw=.8)
        plot.plot([0,0],[-.07,1.14],color='#bdc9cd',lw=.8)
        for user,((x,y),col) in enumerate(zip(vectors,[navy,cyan,amber,purple]),1):
            x,y=float(x),float(y)
            plot.annotate('',xy=(x,y),xytext=(0,0),arrowprops=dict(
                arrowstyle='-|>',color=col,lw=1.8,mutation_scale=8,shrinkA=0,shrinkB=0))
            plot.text(1.14*x,1.13*y,rf'$u_{user}$',fontsize=8.5,color=col,ha='center',va='center')
        match=[(i+1,j+1) for i in range(4) for j in range(i+1,4)
               if sum(x*y for x,y in zip(vectors[i],vectors[j])) == 0]
        assert len(match)==2 and len({u for edge in match for u in edge})==4
        plot.text(0,-.20,'Orthogonal pairs   '+' and '.join(f'{i}–{j}' for i,j in match),
                  ha='center',va='center',fontsize=7.7,color=ink)
    a,b,c,d=ax[1:].flat
    panel_heading(a,'c','Squared channel overlap')
    a.imshow(r.T,aspect='auto',vmin=0,vmax=1,cmap='Blues');a.set_xticks(range(6),['12','13','14','23','24','34']);a.set_yticks([0,1],['Tone 1','Tone 2']);a.set_xlabel('User pair')
    for i,j in np.ndindex(r.T.shape):a.text(j,i,f'{r[j,i]:.2f}',ha='center',va='center',color='white' if r[j,i]>.55 else ink,fontsize=8.5)
    panel_heading(b,'d','Best schedule and priced ceiling');b.plot(t,base+abs(t),color=navy,label='Price relaxation');b.axhline(ref,color=cyan,label='Best labelled schedule');b.vlines(0,ref,base,color=amber,lw=2.5);b.set_xlabel(r'Tone-price difference $\beta_2-\beta_1$ (nats)');b.set_ylabel('Aggregate nats');b.legend(frameon=False,fontsize=6.9);tidy(b)
    tab=data('fig2_label_loss');assert len(tab)==512
    for q,key,l,t in [(c,'posterior','e','Conflict on selected pairs'),(d,'prior','f','Range over all candidate pairs')]:
        panel_heading(q,l,t);q.scatter(tab[key],tab.loss,c=cyan if key=='posterior' else purple,alpha=.42,edgecolors='none',s=11,rasterized=False);q.text(.94,.91,r'$\rho$ = '+f'{spearmanr(tab[key],tab.loss).statistic:.3f}',ha='right',transform=q.transAxes);q.set_xlabel(('Posterior conflict' if key=='posterior' else 'Range bound')+' (bit/s/Hz)');q.set_ylabel('Exact table loss (bit/s/Hz)');tidy(q)
    save(f,'fig2_conflict')
def projection_geometry(left, right):
    panel_heading(left, 'a', 'One projection, two channels')
    left.set(xlim=(-.23,2.45), ylim=(-.35,1.98), aspect='equal')
    left.axis('off')
    def arrow(ax, start, end, color, lw=1.25, style='-|>'):
        ax.annotate('', xy=end, xytext=start, arrowprops=dict(arrowstyle=style, color=color,
                    lw=lw, mutation_scale=8, shrinkA=0, shrinkB=0))
    arrow(left, (0,0), (2.36,0), grey, .8)
    arrow(left, (0,0), (0,1.86), grey, .8)
    left.text(2.33,.075,r'$d$',fontsize=9,ha='right',va='bottom')
    left.text(-.07,1.80,r'$d_\perp$',fontsize=9,ha='right',va='center')
    x, y0, y1 = 1.65, .60, 1.55
    left.plot([x,x],[0,y1],ls=':',color=grey,lw=1)
    arrow(left,(0,0),(x,y0),navy,1.9)
    arrow(left,(0,0),(x,y1),cyan,1.9)
    left.plot(x,0,'o',ms=4.5,mfc='white',mec=ink,zorder=3)
    left.text(x+.09,y0,r'$\hat h$',fontsize=10,va='center',color=navy)
    left.text(x+.08,y1,r'$h$',fontsize=10,va='center',color=cyan)
    left.text(x,-.12,'common projection',ha='center',va='top',fontsize=7.3)
    panel_heading(right, 'b', 'Two bounds on channel error')
    right.set(xlim=(-1.55,1.55),ylim=(-1.4,1.4),aspect='equal')
    right.axis('off')
    right.axvspan(-.35,.35,color='#d9efeb',zorder=0)
    right.add_patch(patches.Circle((0,0),1,facecolor='#e7edf7',alpha=.67,edgecolor='none',zorder=1))
    right.add_patch(patches.Circle((0,0),1,fill=False,edgecolor=navy,linewidth=1.35,zorder=2))
    for x0 in (-.35,.35):right.axvline(x0,ls='--',lw=1,color=cyan,zorder=3)
    arrow(right,(-1.28,0),(1.37,0),grey,.75)
    arrow(right,(0,-1.23),(0,1.25),grey,.75)
    right.plot(0,0,'o',ms=3,mfc=ink,mec=ink,zorder=4)
    right.text(1.32,-.075,r'$d$',va='top',ha='right',fontsize=9)
    right.text(.075,1.34,r'$d_\perp$',va='top',ha='left',fontsize=9)
    arrow(right,(0,0),(-.83,.558),navy,1)
    right.text(-.62,.17,r'$\epsilon$',fontsize=10,color=navy)
    arrow(right,(-.35,-1.17),(.35,-1.17),cyan,.95,'<->')
    right.text(.44,-1.17,r'$2b$',fontsize=8.6,va='center',color=cyan)


def uncertainty():
    f,ax=plt.subplots(3,2,figsize=(7.12,7.24),layout='constrained',
                      gridspec_kw={'height_ratios':[.94,1,1],'wspace':.08,'hspace':.11})
    projection_geometry(*ax[0])
    a,b,c,d=ax[1:].flat
    t=data('fig3_gaussian');v=t['mean'].values;panel_heading(a,'c','Expected rate bounds')
    for i,z in enumerate(v[1:]):
        a.plot([z,v[0]],[1-i]*2,color=cs[i],lw=3.5,solid_capstyle='round');a.scatter([z,v[0]],[1-i]*2,c=[cs[i],ink],s=28,zorder=3);a.text((z+v[0])/2,1-i+.2,f'Gap {v[0]-z:.3f}',ha='center',fontsize=8)
    a.set_yticks([0,1],['Projected','Full vector']);a.set_ylim(-.55,1.55);a.set_xlim(11.5,15.55);a.set_xlabel('Mean endpoint (bit/s/Hz)');tidy(a,'x')
    z=data('fig3_uncertainty')
    for q,(field,l,tit,yl) in zip((b,c),[('median_G','d','Gap at the implemented receiver','Median gap (bit/s/Hz)'),('median_retention','e','Certified rate retention','Median lower / upper')]):
        panel_heading(q,l,tit)
        for family,col in [('C',navy),('UMa',cyan)]:
            for arm,sty,mark in [('fixed','--','o'),('scaled','-','s')]:
                w=z[(z.family==family)&(z.arm==arm)];q.plot(w.db,w[field],sty,marker=mark,ms=3.7,color=col,label=('CDL-C' if family=='C' else family)+' '+arm)
        q.set_xticks([0,10,20]);q.set_xlabel('SNR (dB)');q.set_ylabel(yl);q.axhline(.5 if field=='median_G' else .95,color=grey,lw=.85,ls=':');tidy(q)
    b.legend(frameon=False,ncol=2,fontsize=6.6)
    w=z[z.db==10];panel_heading(d,'f','Usable intervals and joint coverage');idx=np.arange(4);w=w.set_index(['family','arm']).loc[[('C','fixed'),('C','scaled'),('UMa','fixed'),('UMa','scaled')]].reset_index();d.bar(idx-.18,w.useful,.34,color=navy,label='Useful interval');d.bar(idx+.18,w.joint,.34,color=amber,label='Joint coverage')
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
    for method,col,label in [('det',navy,'Deterministic'),('extra',purple,'Three extra iterations'),('hybrid',cyan,'Learned: iteration run')]:
        z=comparison[comparison.method==method]
        for k,marker in [(32,'o'),(64,'s')]:
            r=z[z.k==k].iloc[0];d.scatter(r.median_ms,r.median_G,color=col,marker=marker,s=30,label=label if k==32 else None)
    current=data('fig4_time_control')
    for method,col,label in [('time',amber,'Time-budget deterministic'),('hybrid',cyan,'Learned: time run')]:
        for k,marker in [(32,'o'),(64,'s')]:
            r=current.query('k==@k and method==@method').iloc[0]
            d.scatter(r.median_ms,r.median_G,edgecolor=col,facecolor='white',marker=marker,s=35,label=label if k==32 else None,zorder=4)
    d.set_xlabel('Median complete time (ms)');d.set_ylabel('Median gap (bit/s/Hz)');d.legend(frameon=False,fontsize=5.5,loc='lower right');tidy(d)
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
    title(b,'b','');z=data('fig5_decomposition_distribution')
    for off,col,lo,hi,lab in [(-.12,navy,'slack_lo','slack_hi','Upper-bound slack'),(.12,cyan,'suboptimality_lo','suboptimality_hi','Optimum to rate floor')]:
        for j,k in enumerate((2,4,6,8)):
            q=z.query('k==@k').set_index('statistic')
            b.plot([q.loc['q25',lo],q.loc['q75',hi]],[j+off]*2,color=col,lw=7,alpha=.18)
            for stat,dy,mark,face in [('mean',-.035,'o','white'),('median',.035,'s',col)]:
                r=q.loc[stat]
                b.plot([r[lo],r[hi]],[j+off+dy]*2,color=col,lw=1.2)
                b.scatter([r[lo],r[hi]],[j+off+dy]*2,marker=mark,s=12,facecolor=face,edgecolor=col,zorder=4)
        values=data('fig5_integer_table_reference')['slack_above_table_reference' if lo=='slack_lo' else 'shortfall_below_table_reference']
        b.plot(values.quantile([.25,.75]),[4+off]*2,color=col,lw=7,alpha=.18)
        b.scatter(values.mean(),4+off-.035,marker='o',facecolor='white',edgecolor=col,s=16)
        b.scatter(values.median(),4+off+.035,marker='s',color=col,s=16)
    b.axhline(3.5,color=grey,ls=':',lw=.7)
    b.set_yticks(range(5),['2 analytic','4 analytic','6 analytic','8 analytic','16 table']);b.set_ylim(4.5,-1.1);b.set_xlabel('Contribution (bit/s/Hz)');tidy(b,'x')
    b.legend(handles=[lines.Line2D([],[],color=navy,label='Ceiling / above table'),lines.Line2D([],[],color=cyan,label='Action / below table'),lines.Line2D([],[],color=grey,marker='o',mfc='white',ls='',label='Mean'),lines.Line2D([],[],color=grey,marker='s',ls='',label='Median'),lines.Line2D([],[],color=grey,alpha=.4,lw=5,label='Endpoint IQR')],frameon=False,ncol=2,fontsize=5.5,loc='upper right')
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
    f,ax=plt.subplots(3,2,figsize=(7.03,6.95),layout='constrained',gridspec_kw={'wspace':.075,'hspace':.12})
    a,b,c,d,e,g=ax.flat
    for panel,letter in zip(ax.flat,'abcdef'):title(panel,letter,'')
    summaries=[]
    for j,(name,col) in enumerate([('HUB',navy),('LO',amber)]):
        old=data('fig6_'+name);valid=old[np.isfinite(old.G)];timely=valid[valid.ms<=250]
        z=data('fig6_calibration_'+name);test=z[z['split']=='test'];summaries.append(test)
        ec(a,timely.G,col,name+' certificate',total=1873)
        ec(a,z.equal_power_reference_gap,col,name+' fixed-power reference',total=1873,ls='--')
        dif=(valid.later_LTS_fixed_action_rate-valid.L_proxy).dropna().sort_values().to_numpy()
        b.step(dif,np.arange(1,len(dif)+1)/len(dif),where='post',color=col,label=name)
        comparison=data('fig6_comparison_'+name)
        payload=data('fig6_payload_'+name)
        marker='o' if name=='HUB' else 's'
        offset=-.09 if name=='HUB' else .09
        e.scatter(payload.user+offset,100*payload.ber,marker=marker,s=19,color=col,label=name)
        g.scatter(payload.user+offset,payload.evm_rms_percent,marker=marker,s=19,color=col,label=name)
        for m,row in enumerate(comparison.itertuples()):
            y=2*j+m
            for offset,field,alpha in [(-.22,'floor_coverage',1),(0,'interval_coverage',.65),(.22,'joint_score_coverage',.3)]:
                c.bar(y+offset,getattr(row,field),.20,color=col,alpha=alpha)
            lo,hi,later=row.median_LP,row.median_UF,row.median_later_rate
            d.plot([lo,hi],[y,y],color=col,lw=2.3,ls='-' if m else '--')
            d.plot([lo,hi],[y,y],'|',color=col,ms=8)
            d.scatter(later,y,marker='D',color=ink,s=17,zorder=3)
            d.scatter(row.median_LF,y,marker='^',color=grey,s=18,zorder=3)
            d.text((lo+hi)/2,y-.17,f'{lo:.2f} to {hi:.2f}',ha='center',fontsize=6.3)
    a.axvline(.1,color=grey,ls=':',lw=1);a.set_xlim(0,.30);a.set_xlabel('Early-input gap (bit/s/Hz)');a.set_ylabel('Fraction of 1,873 frames');pct(a);tidy(a);a.legend(frameon=False,loc='lower right',fontsize=5.9)
    b.axvline(0,color=grey,ls=':',lw=1);b.set_xlabel('Later rate − early floor (bit/s/Hz)');b.set_ylabel('Fraction of eligible frames');pct(b);tidy(b);b.legend(frameon=False)
    c.set_xticks(range(4),['HUB\nraw','HUB\nphase','LO\nraw','LO\nphase']);c.set_ylabel('Observed test-frame fraction');pct(c);tidy(c);c.axhline(.95,color=grey,ls=':',lw=.7)
    c.legend(handles=[patches.Patch(color=grey,alpha=v,label=l) for v,l in [(1,'Projected floor'),(.65,'Combined interval'),(.3,'Both residual events')]],
             frameon=True,facecolor='white',edgecolor='none',framealpha=.95,fontsize=6,loc='lower center')
    d.set_yticks(range(4),['HUB raw','HUB phase','LO raw','LO phase']);d.set_ylim(3.65,-.6);d.set_xlim(left=0);d.set_xlabel('Median rate endpoint (bit/s/Hz)');tidy(d,'x')
    d.scatter([],[],marker='D',color=ink,label='Later rate');d.scatter([],[],marker='^',color=grey,label='Vector floor');d.legend(frameon=False,fontsize=5.8,loc='lower center',ncol=2)
    for axis,ylabel in ((e,'Uncoded bit error rate (%)'),(g,'RMS error vector magnitude (%)')):
        axis.set(xticks=range(6),xlabel='User in six-user transmission',ylabel=ylabel)
        tidy(axis)
    e.set_yscale('log')
    e.set_ylim(.001,100)
    e.set_yticks([.001,.01,.1,1,10,100],['0.001','0.01','0.1','1','10','100'])
    e.legend(frameon=False,loc='center right')
    g.set_ylim(bottom=0)
    g.legend(frameon=False,loc='upper left')
    save(f,'fig6_hardware')
if __name__=='__main__':
    for fn in (pipes,conflict,uncertainty,scaling,phase,hardware):fn()
    print('Six figures drawn from checked, disclosable sources.')

