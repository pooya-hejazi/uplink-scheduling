"""Outward IEEE operations; only dyadic fixed-filter proposals and realized channel bytes are trusted inputs."""
import math,sys
from pathlib import Path
import numpy as np
from numba import njit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Gate_1'))
from verifier64 import log64,gradual
D=np.nextafter; PLO=D(.05,-np.inf); PHI=D(.2,np.inf)
Q=2**40; PT=20*2**20
strict=njit(fastmath=False,cache=True)
@strict
def dn(x): return np.nextafter(x,-np.inf)
@strict
def up(x): return np.nextafter(x,np.inf)
# Tabulate certified log(t) for t=1+j/256 using Gate 1; on each cell 0<=z=(t-a)/(t+a)<1/512.
@strict
def log_table():
    t=np.empty((257,2))
    for j in range(257): t[j,0],t[j,1]=log64(1+j/256.)
    return t
def get_table():
    if not gradual(): raise ArithmeticError('gradual binary64 required')
    return log_table()
@strict
def logi(x,T,hi):
    m,e=math.frexp(x); t=2*m; e-=1; j=int((t-1)*256); a=1+j/256.
    # t-a is exact by Sterbenz; use the first three positive odd terms, then bound the tail.
    if hi:
        z=up((t-a)/dn(t+a)); zz=up(z*z)
        v=up(1/5.+2e-16+up(zz/6.)) # remaining terms <= z^6/6 when z<1/512
        v=up(1/3.+2e-16+up(zz*v))
        l=up(T[j,1]+up(2*up(z*up(1.+up(zz*v)))))
        return up(l+up(e*T[256,1 if e>=0 else 0]))
    z=max(0.,dn((t-a)/up(t+a))); zz=max(0.,dn(z*z))
    v=dn(dn(1/3.)+dn(zz*dn(1/5.)))
    l=dn(T[j,0]+dn(2*dn(z*dn(1.+dn(zz*v)))))
    return dn(l+dn(e*T[256,0 if e>=0 else 1]))
def endpoints(h,eps):
    h=np.asarray(h,dtype=np.complex128); k,n,s=h.shape
    eps=np.broadcast_to(np.asarray(eps,dtype=float),(k,s))
    if k!=2*s or not 2<=k<=64 or not 1<=n<=256 or np.any(~np.isfinite(h)) or np.any(~np.isfinite(eps)) or np.any(eps<0): raise ValueError('invalid channel/ball')
    peak=max(np.max(abs(h.real)),np.max(abs(h.imag)))
    if not 2**-100<=peak<=2**100: raise ValueError('unsupported dynamic range')
    b=22-int(np.frexp(peak)[1]); sc=2.**b
    re=np.ascontiguousarray(np.rint(h.real.transpose(2,0,1)*sc),dtype='int64')
    im=np.ascontiguousarray(np.rint(h.imag.transpose(2,0,1)*sc),dtype='int64')
    # 2*N*2^44 <= 2^53: all Gram integers and dyadic rescalings are exactly representable.
    rt=re.transpose(0,2,1); it=im.transpose(0,2,1)
    rr=(re@rt+im@it)/sc**2; ri=(re@it-im@rt)/sc**2
    norm2=rr.diagonal(axis1=1,axis2=2).T
    no0=np.maximum(0,D(np.sqrt(norm2),-np.inf)); no1=D(np.sqrt(norm2),np.inf)
    pad=D(D(np.sqrt(2.*n),np.inf)*(.5/sc),np.inf)
    rad=D(eps+pad,np.inf)
    g=np.maximum(0,D(np.maximum(0,D(no0-rad,-np.inf))**2,-np.inf))
    G=D(D(no1+rad,np.inf)**2,np.inf)
    I,J=np.triu_indices(k,1)
    R=rr[:,I,J].T; V=ri[:,I,J].T
    mag=np.maximum(0,D(np.sqrt(np.maximum(0,D(D(R*R,-np.inf)+D(V*V,-np.inf),-np.inf))),-np.inf))
    err=D(D(D(no1[I]*rad[J],np.inf)+D(no1[J]*rad[I],np.inf),np.inf)+D(rad[I]*rad[J],np.inf),np.inf)
    nlow=np.maximum(0,D(mag-err,-np.inf)); den=D(G[I]*G[J],np.inf)
    rho=np.maximum(0,D(D(nlow*nlow,-np.inf)/den,-np.inf))
    if not np.all(np.isfinite(G)) or not np.all(np.isfinite(rho)) or np.any(rho>1): raise ArithmeticError('bad Gram interval')
    return np.ascontiguousarray(g),np.ascontiguousarray(G),np.ascontiguousarray(rho),I,J
@strict
def rxhi(G,g,r,a,A,b):
    y=max(0.,dn(g*b)); loss=max(0.,dn(dn(r*y)/up(1.+y)))
    return up(1.+up(up(G*A)*up(1.-loss)))
@strict
def mix(g,G,i,j,s,r,a,A,b,B,T):
    return up(logi(rxhi(G[i,s],g[j,s],r,a,A,b),T,True)+logi(rxhi(G[j,s],g[i,s],r,b,B,a),T,True))
@strict
def cached_roots(g,G,r,I,J,T):
    E,S=r.shape; z=np.empty_like(r); pen=np.empty_like(r)
    for e in range(E):
        i,j=I[e],J[e]
        for s in range(S):
            z[e,s]=mix(g,G,i,j,s,r[e,s],PLO,PHI,PLO,PHI,T)
            x=max(0.,dn(g[i,s]*PLO)); y=max(0.,dn(g[j,s]*PLO))
            tx=max(0.,dn(x/up(1.+x))); ty=max(0.,dn(y/up(1.+y)))
            loss=max(0.,dn(dn(r[e,s]*tx)*ty))
            pen[e,s]=up(2*logi(up(1.-loss),T,True))
    return z,pen
@strict
def priced(g,G,r,I,J,T,root,pen,lam,anchors):
    K,S=g.shape; t=np.empty_like(g)
    for i in range(K):
        for s in range(S):
            a=anchors[i,s]
            v=G[i,s]; z=up(1.+up(v*a)); z0=dn(1.+dn(v*a))
            d0=dn(dn(v/z)-lam); d1=up(up(v/z0)-lam)
            # Exact anchor in [PLO, PHI]; all outward choices include both signs of the derivative.
            delta=max(0.,up(max(0.,-d0)*up(a-PLO)),up(max(0.,d1)*up(PHI-a)))
            t[i,s]=up(up(logi(z,T,True)-dn(lam*a))+delta)
    H=np.empty_like(root)
    for e in range(len(I)):
        for s in range(S):
            H[e,s]=min(up(root[e,s]-dn(lam*dn(2*PLO))),up(up(t[I[e],s]+t[J[e],s])+pen[e,s]))
    return H
@strict
def leaves(H,chosen,g,G,r,I,J,T,lam):
    S=H.shape[1]; grid=np.linspace(PLO,PHI,5)
    for aidx in chosen:
        e,s=aidx//S,aidx%S; z=-np.inf
        for u in range(4):
            for v in range(4):
                a,A,b,B=grid[u],grid[u+1],grid[v],grid[v+1]
                z=max(z,up(mix(g,G,I[e],J[e],s,r[e,s],a,A,b,B,T)-dn(lam*dn(a+b))))
        H[e,s]=min(H[e,s],z)
@strict
def dotbox(v,h): # center and componentwise product/sum errors, no assumptions on channel quantization
    rl=rh=il=ih=0.
    for a in range(len(v)):
        A,B=v[a].real,v[a].imag; C,Dd=h[a].real,h[a].imag
        rl=dn(rl+dn(dn(A*C)+dn(B*Dd))); rh=up(rh+up(up(A*C)+up(B*Dd)))
        il=dn(il+dn(dn(A*Dd)-up(B*C))); ih=up(ih+up(up(A*Dd)-dn(B*C)))
    x=max(0.,rl,-rh); y=max(0.,il,-ih); X=max(abs(rl),abs(rh)); Y=max(abs(il),abs(ih))
    return max(0.,dn(math.sqrt(max(0.,dn(dn(x*x)+dn(y*y)))))),up(math.sqrt(up(up(X*X)+up(Y*Y))))
@strict
def lower(h,p,pair,v,balls,T):
    S=len(pair); L=np.empty(S,np.int64)
    for s in range(S):
        lo=0.
        for t in range(2):
            i,j=pair[s,t],pair[s,1-t]; u=v[s,t]; nvmax=0.
            for a in range(len(u)): nvmax=up(nvmax+up(up(u[a].real*u[a].real)+up(u[a].imag*u[a].imag)))
            if nvmax==0: raise ArithmeticError('zero receiver')
            nm=up(math.sqrt(nvmax))
            own=max(0.,dn(dotbox(u,h[i,:,s])[0]-up(nm*balls[s,t,0])))
            other=up(dotbox(u,h[j,:,s])[1]+up(nm*balls[s,t,1]))
            numerator=max(0.,dn(dn(p[i]/PT)*max(0.,dn(own*own))))
            denom=up(nvmax+up(up(p[j]/PT)*up(other*other)))
            lo=dn(lo+logi(max(1.,dn(1.+max(0.,dn(numerator/denom)))),T,False))
        L[s]=max(0,int(math.floor(lo*Q)))
    return L

