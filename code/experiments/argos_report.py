"""Update only the Argos addendum to an existing, timestamped confirmatory campaign."""
import json,csv,hashlib,math,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import pandas as pd
root=Path(__file__).resolve().parent;out=root/'results/argos'
conditions=('static','env','mob')
labels=['Static','Environmental mobility','Mobile']
def main():
    summary=json.loads((root/'results/argos_summary.json').read_text());order={s['regime']:s for s in summary['regimes']};rec=pd.read_csv(out/'frame_summaries.csv');pairs=pd.read_csv(out/'pair_summaries.csv')
    assert len(order)==3 and len(rec)==96 and not rec.duplicated(['frame','regime']).any()
    fig,axes=plt.subplots(1,3,figsize=(8.0,2.7),layout='constrained');cmap=plt.colormaps['viridis'].copy();cmap.set_bad('#e6e9eb');norm=Normalize(0,1)
    srows=[]
    for ax,key,title in zip(axes,conditions,labels):
        m=order[key];q=rec[rec.regime==key];valid=q[q.quality_pass==1];a=pairs[pairs.regime==key]
        x=np.full((6,6),np.nan)
        if len(valid):
            assert np.isclose(np.median(valid.first_mean_rho),m['first_lts_quartiles'][1])
            assert len(a)==15
            for row in a.itertuples():x[row.user_i-1,row.user_j-1]=x[row.user_j-1,row.user_i-1]=row.median_frame_rho_first
        ax.imshow(x,vmin=0,vmax=1,cmap=cmap);ax.set_xticks(range(6),labels=range(1,7));ax.set_yticks(range(6),labels=range(1,7));ax.tick_params(length=0,labelsize=7);ax.set_title(f'{title}\n{len(valid)}/32 usable frames',fontsize=9);ax.set_xlabel('User',fontsize=8)
        if key=='static':ax.set_ylabel('User',fontsize=8)
        q1=m['first_lts_quartiles'];q2=m['second_lts_quartiles'];qu=m['unfiltered_finite_first_lts_quartiles'];delta=m['paired_delta_quartiles']
        srows.append(dict(recording=title,frames_available=m['recorded_frames'],RFs=len(m['rf_indices']),planned=32,valid=m['frames_accepted'],median_first=q1[1] if q1 else '',q25_first=q1[0] if q1 else '',q75_first=q1[2] if q1 else '',median_second=q2[1] if q2 else '',paired_median_second_minus_first=delta[1] if delta else '',unfiltered_median=qu[1] if qu else ''))
    bar=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=axes,shrink=.82);bar.ax.tick_params(labelsize=7);bar.set_label('Median pair correlation (squared)',fontsize=8)
    fig.savefig(out/'spatial_correlation.png',dpi=180);fig.savefig(out/'spatial_correlation.svg');plt.close(fig)
    with (out/'condition_summaries.csv').open('w',newline='',encoding='utf8') as fp:
        w=csv.DictWriter(fp,list(srows[0]));w.writeheader();w.writerows(srows)
    nfmt=lambda v:'—' if v=='' else f'{v:.4f}'
    lines=['# Rice Argos: measured six-user spatial correlations','',summary['statement'],'','| Recording | RF streams | Valid / planned | First pilot median [IQR] | Second pilot median | All finite frames, first pilot |','|---|---:|---:|---:|---:|---:|']
    for a in srows:lines.append(f"| {a['recording']} | {a['RFs']} | {a['valid']}/32 | {nfmt(a['median_first'])} [{nfmt(a['q25_first'])}, {nfmt(a['q75_first'])}] | {nfmt(a['median_second'])} | {nfmt(a['unfiltered_median'])} |")
    lines+=['','![Pairwise squared spatial correlation](results/argos/spatial_correlation.png)','','Each heat-map cell is the median over valid frames of that pair’s average over 52 occupied tones. The diagonal is omitted. The table takes the median after averaging all 15 pairs within a frame; it cannot be recovered by averaging the heat-map cells. A value of 0 means orthogonal channel vectors; 1 means parallel up to complex gain. These are descriptive sample statistics. The interquartile ranges describe variation across the selected frames, not statistical confidence.','','**Measurement and quality.** The licensed source holds one recording per regime from the same November 2015 six-user UHF setup. Each HDF5 frame packs six user pilot slots plus a separate noise slot. Read all eight simultaneous RF streams. Use the first 64 frames solely for the recorded RF mask and select the 32 predeclared later frames without replacement. Compute 64-point FFTs from the first and second disjoint LTS windows at offsets 47 and 111; remove DC and guards. Unit-magnitude LTS signs cancel in the normalized inter-user statistic at each tone. Receiver gain control was enabled in the source: these are recorded digital receive-vector correlations, not a de-embedded propagation or fading model. The first pilot is the primary check; the second is a sensitivity, not independent replication. No Gates 2B/3 success decision, threshold or independent Rice clock session is altered.','','**Reproduce.** Register through the [official Rice survey](https://renew.rice.edu/dataset-argos.html) and accept its license. The selection and thresholds are in [the supplemental protocol](ARGOS_PROTOCOL.md). Run `python Gate_3/argos_source.py`, `python Gate_3/argos_fetch.py`, `python Gate_3/argos.py`, then `python Gate_3/argos_report.py`. These scripts use the inherited scientific environment plus requests, h5py and Matplotlib. Only a private excluded working directory stores the requested IQ, and the range hashes identify exactly which bytes were processed. [Per-frame diagnostics](results/argos/frame_summaries.csv), [pair-by-frame results](results/argos/pair_frames.csv), [calibration mask](results/argos/rf_diagnostics.csv), and [condition summaries](results/argos/condition_summaries.csv) are included.','','**Attribution.** Clayton Shepard, Jian Ding, Ryan E. Guerra and Lin Zhong, [*Understanding Real Many-Antenna MU-MIMO Channels*](https://www.yecl.org/publications/shepard2016asilomar.pdf), Asilomar 2016. FFT convention: [Rice RENEWLab legacy Argos decoder](https://github.com/renew-wireless/RENEWLab/blob/master/PYTHON/IrisUtils/hdf5_lib.py). Rice University retains rights to the original measurements.']
    (root/'ARGOS.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    supplement=root/'SUPPLEMENT.md';pars=supplement.read_text(encoding='utf8').split('\n\n');ix=[k for k,p in enumerate(pars) if p.startswith(('No Argos spatial-control values','Argos companion spatial check:'))];assert len(ix)==1;pars[ix[0]]='Argos companion spatial check: '+summary['statement'];supplement.write_text('\n\n'.join(pars),encoding='utf8')
    print('Updated three descriptive rows, addendum, figure, and existing Argos paragraph.')
if __name__=='__main__':main()

