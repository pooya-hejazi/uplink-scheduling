"""Pilot-only eligibility and synchronization using redundant LTS; never select a target count."""
import numpy as np
def synchronize(x,pre,cp,fft,slot,post):
    # Per-user common timing shift. Pool correlation over antennas/time, using ten distinct reserved pilot repetitions.
    z=(x[...,::2].astype(float)+1j*x[...,1::2].astype(float))/32768
    offsets=np.arange(-64,65,2); users=z.shape[1];sc=np.zeros((users,len(offsets)))
    for j,lag in enumerate(offsets):
        starts=[pre+cp+lag+t*(fft+cp) for t in [1,2,3,4,5,6,7,8]]
        X=np.stack([z[...,a:a+fft] for a in starts],axis=-2)
        F=np.fft.fft(X,axis=-1); active=np.r_[1:27,38:64];null=np.r_[0,27:38]
        band=np.mean(abs(F[...,active])**2,axis=(-1,-2));guard=np.mean(abs(F[...,null])**2,axis=(-1,-2))
        sc[:,j]=np.median(np.log((band+1e-20)/(guard+1e-20)),axis=(0,2))
    # Median across tied maxima, preferred smallest absolute delay.
    chosen=[int(offsets[np.lexsort((abs(offsets),-line))[0]]) for line in sc]
    return chosen,sc,offsets
def strength(x,no,pre,cp,fft,lag,pf,shift):
    active=np.flatnonzero(abs(pf)>.5);n=x.shape[2];v=np.empty((x.shape[1],n));co=np.empty_like(v)
    def transform(raw,t):
        z=raw[...,2*t:2*(t+fft):2].astype(float)+1j*raw[...,2*t+1:2*(t+fft):2].astype(float)
        F=np.fft.fft(z,axis=-1)
        return (np.fft.fftshift(F,axes=-1) if shift else F)[...,active]
    for u,l in enumerate(lag):
        a=pre+cp+l;fts=np.stack([transform(x[:,u],a+j*(fft+cp)) for j in range(2,8)],axis=1)
        noise=np.stack([transform(no,pre+cp+j*(fft+cp)) for j in range(2,8)],axis=1)
        power=np.mean(abs(fts)**2,axis=(0,1,3));npow=np.mean(abs(noise)**2,axis=(0,1,3))
        v[u]=10*np.log10(np.maximum(power/np.maximum(npow,1e-30),1e-30))
        cc=abs(np.sum(fts[:,:-1].conj()*fts[:,1:],axis=-1))/np.sqrt(np.maximum(1e-30,(abs(fts[:,:-1])**2).sum(-1)*(abs(fts[:,1:])**2).sum(-1)))
        co[u]=np.mean(cc,axis=(0,1))
    return v,co

