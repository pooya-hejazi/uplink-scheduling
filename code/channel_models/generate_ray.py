"""Use the archived DeepMIMO v3 implementation's original v2 ray reader and channel model."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
from scipy.io import loadmat
base=Path(__import__('os').environ.get('DEEPMIMO_ROOT','.'))
sys.path.insert(0,str(Path(__import__('os').environ.get('DEEPMIMO_PYTHON_PATH','.'))))
from DeepMIMOv3 import consts as c
from DeepMIMOv3.params import default_params
from DeepMIMOv3.raytracing_v2 import extract_data_from_ray,load_ray_data,load_scenario_params,load_bs_loc
from DeepMIMOv3.construct_deepmimo import generate_MIMO_channel
out=Path(__file__).resolve().parent/'data'; out.mkdir(exist_ok=True)
for name,folder in [('O1_60',base/'O1_60'),('asu_campus1',base/'asu_campus1')]:
    prefix=folder/name; par=default_params()
    par[c.PARAMSET_SCENARIO_PARAMS]=sp=load_scenario_params(str(prefix)+'.params.mat')
    par[c.PARAMSET_OFDM][c.PARAMSET_OFDM_BW]=.020
    par[c.PARAMSET_OFDM][c.PARAMSET_OFDM_SC_NUM]=64
    par[c.PARAMSET_OFDM][c.PARAMSET_OFDM_SC_SAMP]=np.arange(64)
    tx,rx=par[c.PARAMSET_ANT_BS],par[c.PARAMSET_ANT_UE]
    tx[c.PARAMSET_ANT_SHAPE]=np.array([16,1]); rx[c.PARAMSET_ANT_SHAPE]=np.array([1,1])
    par[c.PARAMSET_NUM_PATHS]=25
    rays=load_ray_data(str(prefix),1); loc=rays[c.LOAD_FILE_EXT[5]][:,1:4]
    # Locate positive-path users using the archive's id/count/4-values-per-path layout.
    buf=rays[c.LOAD_FILE_EXT[0]]; j=1; counts=np.zeros(len(loc),int)
    for i in range(len(loc)):
        counts[i]=int(buf[j+1]); j+=2+4*counts[i]
    assert j==len(buf)
    d=np.diff(np.unique(np.round(loc[:,0],4))); step=float(np.median(d[d>1e-4]))
    width=step*12
    cells=np.floor((loc[:,:2]-loc[:,:2].min(0))/width+1e-7).astype(int)
    groups={}
    for i in np.flatnonzero(counts): groups.setdefault(tuple(cells[i]),[]).append(i)
    tiles=[]; rng=np.random.default_rng(9017)
    for cell in [v for v in sorted(groups) if len(groups[v])>=64]:
        if any(max(abs(np.array(cell)-v))<2 for v,_ in tiles): continue
        tiles.append((cell,rng.choice(groups[cell],64,replace=False)))
        if len(tiles)==12: break
    assert len(tiles)==12,(name,width,len(tiles))
    ids=np.sort(np.concatenate([u for _,u in tiles])); rd=extract_data_from_ray(rays,ids,par)
    rx[c.PARAMSET_ANT_ROTATION]=np.zeros((len(ids),3))
    h,los=generate_MIMO_channel(rd[c.OUT_PATH],par,tx,rx)
    assert np.isfinite(h).all()
    for i,(cell,u) in enumerate(tiles):
        ix=np.searchsorted(ids,u); v=h[ix,0]
        assert v.shape==(64,16,64) and np.all(np.linalg.norm(v,axis=1)>0)
        np.savez(out/f'pilot_{name}_{i:04d}.npz',h=v,xyz=loc[u],perm=u,bins=np.arange(64),paths=counts[u],cell=cell,bs=load_bs_loc(str(prefix),1),width=width)
    files=[f for f in folder.glob(name+'*.mat') if (f.name.startswith(name+'.1.') and 'BSBS' not in f.name) or f.name[len(name):] in ['.params.mat','.Loc.mat','.TX_Loc.mat','.RX_Loc.mat']]
    (out/f'{name}_source.json').write_text(json.dumps({'scene':name,'bs':1,'carrier_hz':float(sp[c.PARAMSET_SCENARIO_PARAMS_CF]),'width_m':width,'files':{f.name:hashlib.file_digest(f.open('rb'),'sha256').hexdigest() for f in files}},indent=2))
    print(name,'tiles',len(tiles),'width',width,flush=True)

