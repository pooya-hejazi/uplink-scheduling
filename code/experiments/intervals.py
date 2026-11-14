"""Within-family bootstrap over complete topology/tile blocks, reusing draws for every SNR and K."""
from pathlib import Path
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent/'results'
def run():
    data=pd.read_csv(R/'sensitivity_grid.csv');out=[]
    for f,d in data.groupby('family'):
        a=d.pivot(index='block',columns=['k','db'],values='G');assert not a.isna().any().any();n=len(a);rng=np.random.default_rng(19073)
        q=[]
        for _ in range(50):q.append(np.median(a.to_numpy()[rng.integers(n,size=(200,n))],axis=1))
        lo,hi=np.quantile(np.concatenate(q),[.025,.975],axis=0)
        for j,(k,db) in enumerate(a.columns):out.append(dict(family=f,k=k,db=db,n=n,median=a.iloc[:,j].median(),ci_lo=lo[j],ci_hi=hi[j],draws=10000))
    pd.DataFrame(out).to_csv(R/'sensitivity_intervals.csv',index=False)
    h=pd.read_csv(R/'policy_rate_bands.csv');z=[]
    for (f,arm),v in h.groupby(['family','arm']):
        rng=np.random.default_rng(19073);n=len(v);a=(v.warm_actual-v.cold_actual).to_numpy();boot=a[rng.integers(n,size=(10000,n))].mean(1)
        z.append(dict(family=f,arm=arm,n=n,paired_actual_difference=a.mean(),ci_lo=np.quantile(boot,.025),ci_hi=np.quantile(boot,.975),kind='statistical actual gross LS action difference, not a certified horizon win'))
    pd.DataFrame(z).to_csv(R/'paired_rate_intervals.csv',index=False)
if __name__=='__main__':run()

