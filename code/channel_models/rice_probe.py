"""Probe RF activity on the same four frame IDs of every listed HDF5. Full-capture replays verify their entire frame range."""
import json,concurrent.futures
import numpy as np,h5py
from rice_io import inventory,R,Remote
from rice_decode import schema
def probe(row):
    key='_'.join(row[k] for k in ('placement','mode','los','rf_chain'));dest=R/f'rice_activity_{key}.json'
    if dest.exists():return
    r=Remote(row)
    with h5py.File(r,'r') as f:
        d,m,p=schema(f);ps=d['Pilot_Samples'];ns=d['Noise_Samples'];n=m['frames'];fr=[0,1,n//2,n-1]
        active=[];energies=[];noise=[]
        for k in fr:
            v=ps[k,0]; no=ns[k,0,0];a=np.any(v!=0,axis=(0,2));active.append(np.flatnonzero(a).tolist())
            energies.append(np.mean(v.astype(float)**2,axis=(0,2)).tolist());noise.append(np.mean(no.astype(float)**2,axis=1).tolist())
    m.update(frame_ids=fr,nonzero_antennas_by_frame=active,pilot_adc_power_by_frame=energies,noise_adc_power_by_frame=noise,etag=row['etag'],source=row['url'],range_sha256=r.chunks)
    dest.write_text(json.dumps(m,indent=2));print(key,[len(i) for i in active],m['tones'],flush=True)
    r.session.close()
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(4) as pool:list(pool.map(probe,inventory()))

