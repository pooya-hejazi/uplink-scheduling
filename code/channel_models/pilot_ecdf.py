"""One denominator per native K, including slow receipts, for the threshold/deadline decision."""
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'results'; d=pd.read_csv(R/'block_medians.csv')
d=d[(d.family.isin(['A','B','C','UMa']))&(d.db==10)]
rows=[];fig,axes=plt.subplots(1,2,figsize=(8,3.2),layout='constrained',sharey=True)
for k,limit,required,ax in zip([32,64],[250,1000],[.8,.6],axes):
    for m,color,label in [('subgrad','#985a34','Subgradient + P3'),('neural','#14696c','Locked proposer')]:
        z=d[(d.k==k)&(d.method==m)]
        assert len(z)==96
        ontime=z.total_ns<=limit*1e6
        gaps=np.sort(z.G.to_numpy()); timely=np.sort(z.G[ontime].to_numpy())
        x=np.r_[0,gaps[gaps<=.35],.35];ax.step(x,np.searchsorted(timely,x,side='right')/96,where='post',color=color,label=label)
        for g in [.02,.05,.10,.15]:
            low=z.G<=g;rows.append(dict(k=k,method=m,tau=g,n=96,gap_only=int(low.sum()),time_only=int(ontime.sum()),both=int((low&ontime).sum()),gap_fail_only=int((~low&ontime).sum()),late_only=int((low&~ontime).sum()),both_fail=int((~low&~ontime).sum())))
    ax.axhline(required,color='#525e64',linestyle=':',label='Required fraction');ax.axvline(.15,color='#71838b',linestyle='--',lw=1)
    ax.set(xlim=(0,.35),ylim=(0,1.02),xlabel='Certified gap (bit/s/Hz)',title=f'K = {k}  ·  {limit:,} ms deadline')
    ax.spines[['right','top']].set_visible(False)
axes[0].set_ylabel('Fraction of all 96 blocks on time and below gap')
axes[1].legend(fontsize=8,loc='lower right')
fig.savefig(R/'known_pilot_ecdf.png',dpi=165);fig.savefig(R/'known_pilot_ecdf.svg');plt.close()
pd.DataFrame(rows).to_csv(R/'deadline_gap_attribution.csv',index=False)

