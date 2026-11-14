"""Seeded analytic benchmarks; accept no new ray or topology before the gate lock."""
import csv,hashlib,json,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent;old=root.parent/'Gate_2';sys.path.insert(0,str(root.parent/'Gate_2B'))
from cohorts import ids
geoms=('orthogonal','near_collinear','frequency_flat','frequency_selective')
def seed(f,i):return int.from_bytes(hashlib.sha256(f'Gate3|geometry|{f}|{i}'.encode()).digest()[:8],'little')
def guard():
    b=root.parent/'Gate_2B/results'
    j=json.loads((b/'gate2b_lock.json').read_text());assert j['pass'] and j['replay_complete'] and j['freeze']==hashlib.sha256((b/'freeze.json').read_bytes()).hexdigest()
def analytic(f,i):
    guard();rng=np.random.default_rng(seed(f,i));k=64;n=16;s=64
    def cn(shape):return (rng.normal(size=shape)+1j*rng.normal(size=shape))/np.sqrt(2)
    if f=='orthogonal':
        basis=np.linalg.qr(cn((n,n)))[0].T
        v=basis[np.arange(k)%n,:,None]*np.sqrt(n)*np.exp(1j*rng.uniform(-np.pi,np.pi,(k,1,s)))
    elif f=='near_collinear':
        common=cn((1,n,1));v=np.sqrt(.99)*common+np.sqrt(.01)*cn((k,n,s))
    elif f=='frequency_flat':v=np.broadcast_to(cn((k,n,1)),(k,n,s))
    elif f=='frequency_selective':
        taps=cn((k,n,4))/2;delay=rng.uniform(0,250e-9,(k,4));hz=(np.arange(s)-32)*312500
        v=np.einsum('knl,kls->kns',taps,np.exp(-2j*np.pi*delay[:,:,None]*hz))
    else:raise ValueError(f)
    return np.ascontiguousarray(v,dtype=np.complex64)
def rules():
    guard();dest=root/'data';dest.mkdir(exist_ok=True)
    with (root/'analytic_seeds.csv').open('w',newline='') as fp:
        w=csv.writer(fp);w.writerow(['family','block','seed']);w.writerows((f,i,seed(f,i)) for f in geoms for i in range(128))
def ray():
    guard();base=Path('D:/PostDocProposal/PostDocPaper2')
    sys.path.insert(0,str(base/'audit/frozen/S04-PREFLIGHT-A01/environment'))
    from DeepMIMOv3 import consts as c
    from DeepMIMOv3.params import default_params
    from DeepMIMOv3.raytracing_v2 import extract_data_from_ray,load_ray_data,load_scenario_params,load_bs_loc
    from DeepMIMOv3.construct_deepmimo import generate_MIMO_channel
    dest=root/'data';dest.mkdir(exist_ok=True);record=[]
    for f,folder in [('O1_60',base/'DeepMIMO_sena/O1_60'),('asu_campus1',base/'research/reviewer-resolution-20261101/downloads/scene/asu_campus1')]:
        spec=json.loads((old/'data'/f'{f}_source.json').read_text())
        for name,hv in spec['files'].items():
            with (folder/name).open('rb') as source:assert hashlib.file_digest(source,'sha256').hexdigest()==hv
        prefix=str(folder/f);par=default_params();par[c.PARAMSET_SCENARIO_PARAMS]=load_scenario_params(prefix+'.params.mat')
        par[c.PARAMSET_OFDM].update({c.PARAMSET_OFDM_BW:.020,c.PARAMSET_OFDM_SC_NUM:64,c.PARAMSET_OFDM_SC_SAMP:np.arange(64)})
        tx,rx=par[c.PARAMSET_ANT_BS],par[c.PARAMSET_ANT_UE];tx[c.PARAMSET_ANT_SHAPE]=np.array([16,1]);rx[c.PARAMSET_ANT_SHAPE]=np.array([1,1]);par[c.PARAMSET_NUM_PATHS]=25
        rays=load_ray_data(prefix,1);loc=rays[c.LOAD_FILE_EXT[5]][:,1:4];buf=rays[c.LOAD_FILE_EXT[0]];j=1;counts=np.zeros(len(loc),int)
        for i in range(len(loc)):counts[i]=int(buf[j+1]);j+=2+4*counts[i]
        assert j==len(buf);width=spec['width_m'];cells=np.floor((loc[:,:2]-loc[:,:2].min(0))/width+1e-7).astype(int);groups={}
        for i in np.flatnonzero(counts):groups.setdefault(tuple(cells[i]),[]).append(i)
        pilots=[np.load(old/'data'/f'pilot_{f}_{i:04d}.npz') for i in range(12)]
        forbidden=[p['cell'] for p in pilots];used=set().union(*(set(p['perm']) for p in pilots));tiles=[];rng=np.random.default_rng(62071)
        for cell in sorted(groups):
            if len(groups[cell])<64 or any(np.max(abs(np.array(cell)-v))<2 for v in forbidden):continue
            u=rng.choice(groups[cell],64,replace=False);assert used.isdisjoint(u);used.update(u);forbidden.append(np.array(cell));tiles.append((cell,u))
            if len(tiles)==64:break
        for p in pilots:p.close()
        # Persist choices before channel construction. All are disjoint from pilot users, regardless of guard.
        (root/f'{f}_tiles.json').write_text(json.dumps([dict(block=i,cell=list(map(int,cell)),users=u.tolist()) for i,(cell,u) in enumerate(tiles)]))
        for chunk in range(0,len(tiles),4):
            take=tiles[chunk:chunk+4];group=np.sort(np.concatenate([u for _,u in take]));rd=extract_data_from_ray(rays,group,par);rx[c.PARAMSET_ANT_ROTATION]=np.zeros((len(group),3))
            h,_=generate_MIMO_channel(rd[c.OUT_PATH],par,tx,rx)
            for z,(cell,u) in enumerate(take):
                i=chunk+z;v=h[np.searchsorted(group,u),0];assert v.shape==(64,16,64) and np.isfinite(v).all() and np.all(np.linalg.norm(v,axis=1)>0)
                p=dest/f'pilot_{f}_{i:04d}.npz';np.savez(p,h=v,xyz=loc[u],perm=u,bins=np.arange(64),paths=counts[u],cell=cell,bs=load_bs_loc(prefix,1),width=width)
                record.append(dict(scene=f,block=i,bs=1,carrier=spec['carrier_hz'],width=width,cell_x=cell[0],cell_y=cell[1],file_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        print(f,len(tiles),'guarded test tiles',flush=True)
    with (root/'ray_manifest.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,list(record[0]));w.writeheader();w.writerows(record)
if __name__=='__main__':rules();ray()

