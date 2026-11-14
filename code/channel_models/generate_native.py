"""Gate 2 inputs only; the pilot, conformal and fit partitions have separate keys."""
from pathlib import Path
import sys, hashlib, time
import numpy as np
import torch
from sionna.phy import config
from sionna.phy.channel import cir_to_ofdm_channel
from sionna.phy.channel.tr38901 import CDL, UMa, Antenna, AntennaArray
out=Path(__file__).resolve().parent/'data'
out.mkdir(exist_ok=True)
torch.set_num_threads(2)
f=3.5e9
ut=Antenna('single','V','omni',f)
def array(n): return AntennaArray(1,n,'single','V','omni',f)
bs_sites=np.array([[0,0,25],[500,0,25],[0,500,25],[500,500,25]],dtype='f')
freq=torch.arange(-32,32,dtype=torch.float32)*312500.
def seed_for(part,fam,i):
    return int.from_bytes(hashlib.sha256(f'gate2-v1|{part}|{fam}|{i}'.encode()).digest()[:4],'little')
def make(part,fam,n):
    t=time.perf_counter()
    cs=CDL(fam,100e-9,f,ut,array(16),'uplink',spec_version='19.2') if fam in ('A','B','C') else None
    if fam=='UMa': cs=UMa(f,'low',ut,array(4),'uplink',enable_pathloss=True,enable_shadow_fading=True,spec_version='19.2')
    for i in range(n):
        target=out/f'{part}_{fam}_{i:04d}.npz'
        if target.exists(): continue
        k=64 if part in ('pilot','cal64') else (32 if part=='cal' else (8,16,32)[i%3])
        seed=seed_for(part,fam,i); rng=np.random.default_rng(seed)
        config.seed=seed
        if cs is not None: cs.torch_rng.manual_seed(seed)
        xyz=np.empty((0,3),dtype='f')
        with torch.no_grad():
            if fam in ('A','B','C'):
                a,tau=cs(k,1,20e6)
                h=cir_to_ofdm_channel(freq,a,tau,normalize=False)[:,0,:,0,0,0].numpy()
            elif fam=='UMa':
                xy=rng.uniform(40,460,(k,2))
                xyz=np.column_stack([xy,np.full(k,1.5)]).astype('f')
                u=torch.tensor(xyz[None]); b=torch.tensor(bs_sites[None])
                cs.set_topology(u,b,torch.zeros_like(u),torch.zeros_like(b),torch.zeros_like(u),torch.zeros((1,k),dtype=torch.bool))
                a,tau=cs(1,20e6)
                h=cir_to_ofdm_channel(freq,a,tau,normalize=False)[0,:,:,:,0,0].permute(2,0,1,3).reshape(k,16,64).numpy()
            else:
                g=(rng.normal(size=(k,16,4))+1j*rng.normal(size=(k,16,4)))/np.sqrt(8)
                if i%2: g[1::2]=.85*g[::2]+np.sqrt(1-.85**2)*g[1::2]
                delay=rng.uniform(0,250e-9,(k,4))
                h=np.einsum('knp,kpf->knf',g,np.exp(-2j*np.pi*delay[:,:,None]*freq.numpy()))
        perm=rng.permutation(k); h=np.asarray(h[perm],dtype='complex64')
        assert h.shape==(k,16,64) and np.isfinite(h).all() and np.all(np.sum(abs(h)**2,axis=1)>0)
        bins=np.arange(64) if part in ('pilot','cal64') else np.arange(0,64,64//(k//2))
        tmp=target.with_suffix('.tmp.npz')
        np.savez(tmp,h=h[:,:,bins],bins=bins,seed=seed,perm=perm,xyz=xyz[perm] if len(xyz) else xyz)
        tmp.replace(target)
        if i==0 or (i+1)%128==0: print(part,fam,i+1,round(time.perf_counter()-t,2),flush=True)
    print('finished',part,fam,n,round(time.perf_counter()-t,2),flush=True)
if __name__=='__main__':
    for part in sys.argv[1:] or ['pilot','val','fit','cal']:
        for fam in {'pilot':['A','B','C','UMa'],'fit':['analytic','A','B','C'],'val':['analytic','A','B','C'],'cal':['C','UMa'],'cal64':['C','UMa']}[part]:
            make(part,fam,{'pilot':24,'val':64,'fit':1024,'cal':256,'cal64':256}[part])

