from pathlib import Path
import json,csv,numpy as np
from rice_io import R,inventory
def render():
    rows=[];docs=[]
    for v in inventory():
        key='_'.join(v[k] for k in ('placement','mode','los','rf_chain'));m=json.loads((R/f'rice_meta_{key}.json').read_text());a=m['attrs']
        raw=np.sort(a['OFDM_DATA_SC']);pf=np.asarray(a['OFDM_PILOT_F']);pf=pf[::2]+1j*pf[1::2];pt=np.asarray(a['OFDM_PILOT']);pt=pt[::2]+1j*pt[1::2];shift=bool(np.allclose(np.fft.fftshift(np.fft.fft(pt)),pf,atol=1e-5))
        assert shift or np.allclose(np.fft.fft(pt),pf,atol=1e-5)
        signed=raw-32 if shift else (raw+32)%64-32;ii=np.argsort(signed)[[12,24,36]]
        probe=R/f'rice_activity_{key}.json';qc=json.loads(probe.read_text()) if probe.exists() else {}
        row=dict(stratum=key,filename=v['url'].split('/')[-1],bytes=v['bytes'],frames=m['fields']['Pilot_Samples']['shape'][0],users=6,slots=64,ordering='shifted' if shift else 'unshifted',tone_storage_indices=raw[ii].tolist(),signed_tones=signed[ii].tolist(),nonzero_probe_frames=qc.get('frame_ids'),nonzero_slots_on_probe=[len(x) for x in qc.get('nonzero_antennas_by_frame',[])])
        assert row['signed_tones']==[-13,1,14]
        rows.append(row)
    with (R/'rice_inventory_verified.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
    txt='The [Rice collection](https://renew.rice.edu/dataset-distributed.html) lists distributed LoS HUB/LO and colocated HUB LoS/NLoS. Registration exposed individual files. The [verified manifest](results/rice_inventory_verified.csv) names eight eligible 6-user HDF5 files, two UE RF-chain recordings per stratum. All eight contain 2,001 frame slots, six time-orthogonal pilot transmitters, 64 stored antenna slots, a noise slot and simultaneous uplink data. These are not eight independent channel campaigns. Rice advertises 61 usable antennas; raw shape, a nonzero noise ADC stream and a pilot-responsive stream are distinct observations.\n\n'
    txt+='**Tone and time conventions.** A 64-bin FFT at 5 MHz yields 78.125 kHz spacing, carrier 3.6 GHz. Validate FFT shift against each file’s recorded time/frequency pilot, then choose the zero-based 12th, 24th and 36th positions (indices 12, 24 and 36) in the *signed-frequency sorted* list of 48 active data tones. In all strata these are signed bins **−13, +1, +14**. In the distributed files these are storage bins **19, 33, 46**; the colocated LoS records use unshifted storage bins **51, 1, 14** for the same frequencies. No control pilot or DC bin is selected. The nominal decision/reference FFT windows are [176,240) and [256,320) in the 1,120 complex-sample slot (64 samples, 16 CP, prefix 160); the stored six per-client alignment corrections are applied to both windows. Later LTS is a noisy check, not ground truth. The measured noise-slot variances are fixed per antenna and tone using the reserved first 128 frames. No simulated block normalization is used.\n\n'
    txt+='Each 2,001-frame selected recording was decoded in full. The first 128 frames are an explicit prefix for eligibility, alignment and noise estimation; no outcome for these frames contributes to utility. Pilot detection in later frames uses the decision pilot versus its own preceding guard interval and requires all six clients. Unavailable decisions and muted frames are separately counted. Calibration chooses RF streams with both signal/noise ≥6 dB and adjacent-LTS coherence ≥0.60 for at least one user; it does not assume 61 or tune to that count. All stored streams remain in the field inventory.\n\n'
    txt+='| Distributed capture (chain A) | Usable RF streams | Scored / eligible-period frames | Abstained | Median G | Median receipt ms | ≤0.10 and ≤250 ms, all post-prefix frames |\n|---|---:|---:|---:|---:|---:|---:|\n'
    aliases=[]
    for ch in ['A','B']:
        aa=json.loads((R/f'rice_activity_colocated_HUB_NLoS_{ch}.json').read_text())
        bb=json.loads((R/f'rice_activity_distributed_HUB_LoS_{ch}.json').read_text())
        common=set(aa['range_sha256'])&set(bb['range_sha256'])
        aliases.append(dict(chain=ch,overlapping_chunks=len(common),equal_hashes=sum(aa['range_sha256'][k]==bb['range_sha256'][k] for k in common),equal_sampled_pilot=aa['pilot_adc_power_by_frame']==bb['pilot_adc_power_by_frame'],equal_sampled_noise=aa['noise_adc_power_by_frame']==bb['noise_adc_power_by_frame']))
    (R/'rice_alias_audit.json').write_text(json.dumps(aliases,indent=2))
    for mode in ['HUB','LO']:
        if not (R/f'rice_replay_{mode}.json').exists():
            txt+=f'| {mode} | pending | pending | pending | pending | pending | pending |\n';continue
        r=json.loads((R/f'rice_replay_{mode}.json').read_text());n=r['frames']-128
        rate=r['fraction_0p1_250ms']*r['decisions']/n
        txt+=f"| {mode} | {r['active_count']}/64 | {r['decisions']}/{n} | {len(r['abstention_frames'])} | {r['median_G']:.4f} | {r['median_ms']:.2f} | {rate:.1%} |\n"
        docs.append(r)
    txt+='\nNo observed violation of the recorded-input certificate on either capture. Each real data frame contains six simultaneous users; the chosen two-user-per-tone schedule is an offline channel-proxy counterfactual. A later reference rate outside an early proxy interval would not be a violation for the early recorded input. Capture hashes, all accepted frame IDs, abstentions, the quality arrays, noise convention, exact filters’ input hashes and elapsed clocks are in the Rice result files. No raw IQ or reconstructed channel tensor is redistributed. The evidence is **one full capture per distributed clock mode**, descriptive only. The roadmap’s twelve independent captures per stratum are unavailable here; no comparative efficacy or population coverage claim is supported.\n\nRice platform acknowledgment: Doost-Mohammady et al., [*RENEW: Programmable and Observable Massive MIMO Networks*](https://doi.org/10.1109/ACSSC.2018.8645391), Asilomar, 2018. Dataset: M. Zafari, [Distributed Multi-User MIMO Datasets](https://doi.org/10.21227/74ez-b275). Reconstruction convention checked against the [official RENEWLab implementation](https://github.com/renew-wireless/RENEWLab/blob/master/PYTHON/IrisUtils/hdf5_lib.py).'
    if len(docs)!=2:
        txt=txt.replace('Each 2,001-frame selected recording was decoded in full.','Full 2,001-frame decoding is in progress; pending cells are not measurements.')
        txt=txt[:txt.index('No observed violation of the recorded-input certificate')]+ 'Full-capture outcome pending. Only the file inventory, decoder inputs, and named completed rows above are established.'
    txt+='\n\n**Identity caveat.** The colocated HUB NLoS and distributed HUB LoS directories list the same chain-A and chain-B filenames, byte lengths, and acquisition timestamps. Sampled pilot and noise powers for the four inspected frame indices match exactly in both A and B. Identical SHA-256 counts for the independently requested common file ranges: '+', '.join(f"{x['chain']} {x['equal_hashes']}/{x['overlapping_chunks']}" for x in aliases)+'. These are probable mirrored recordings, not independent replications. An equality test across two directory paths is not a proof of the physical placement. Unambiguous physical assignment needs author-side provenance; the distributed HUB result is attributed to the source directory only.'
    drift=[]
    for r in docs:
        with (R/f"rice_replay_{r['mode']}.csv").open() as fp:frames=list(csv.DictReader(fp))
        proxy=np.array([float(f['L_proxy']) for f in frames]);ref=np.array([float(f['later_LTS_fixed_action_rate']) for f in frames])
        drift.append(f"{r['mode']} {np.median(ref-proxy):+.3f} bit/s/Hz ({np.sum(ref<proxy)}/{len(ref)} later references below the early lower endpoint)")
    if drift:txt+='\n\n**What the replay does not certify.** With the same implemented action on the second, disjoint LTS window, the median paired change from the early lower endpoint was '+ '; '.join(drift)+'. This observed proxy/reference discrepancy is material. It is not a hardware confidence interval, a measured counterfactual payload rate, or a violation of the early-input theorem.'
    txt=txt.replace('The measured noise-slot variances are fixed per antenna and tone using the reserved first 128 frames.','The measured noise-slot variances are fixed per antenna and tone using the reserved first 128 frames. The verifier uses diagonal noise weighting in ADC units; the pilot does not establish full spatial noise whitening or calibrated radiated watts.')
    if len(docs)==2:
        for r in docs:
            manifest=next(v for v in rows if v['stratum']==f"distributed_{r['mode']}_LoS_A")
            assert r['tones']==manifest['tone_storage_indices'] and r['fftshift']==(manifest['ordering']=='shifted')
            r['signed_tones']=manifest['signed_tones']
            (R/f"rice_replay_{r['mode']}.json").write_text(json.dumps(r,indent=2))
            with (R/f"rice_replay_{r['mode']}.csv").open() as fp:fr=list(csv.DictReader(fp))
            ids={int(v['frame']) for v in fr};absent=set(r['abstention_frames'])
            assert len(ids)==len(fr)==r['decisions'] and not ids&absent and ids|absent==set(range(128,r['frames'])) and r['observed_violations']==0
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(7.7,2.7),layout='constrained')
        for ax,r in zip(axes,docs):
            with (R/f"rice_replay_{r['mode']}.csv").open() as fp:fr=list(csv.DictReader(fp))
            for key,color,lab in [('L_proxy','#14696c','Early certified lower'),('later_LTS_fixed_action_rate','#985a34','Later LTS, same action')]:
                xx=np.sort([float(x[key]) for x in fr]);ax.step(xx,np.arange(1,len(xx)+1)/len(xx),where='post',color=color,label=lab)
            ax.set(title=r['mode']+' · one capture',xlabel='Rate on the specified input (bit/s/Hz)',ylabel='Fraction of scored frames',ylim=(0,1.02));ax.spines[['top','right']].set_visible(False)
        axes[-1].legend(fontsize=8)
        fig.savefig(R/'rice_reference_ecdf.png',dpi=165);fig.savefig(R/'rice_reference_ecdf.svg');plt.close(fig)
        txt+=' [Per-capture proxy and reference distributions](results/rice_reference_ecdf.png).'
    (R.parent/'RICE_RESULTS.md').write_text(txt,encoding='utf8')
if __name__=='__main__':render()

