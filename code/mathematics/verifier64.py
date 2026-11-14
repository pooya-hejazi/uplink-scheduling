"""Compiled binary64 interval kernel for priced MMSE power boxes. Numba, no fastmath."""
import math
import numpy as np
from numba import njit

strict=njit(fastmath=False,cache=False)


@strict
def down(x):
    return np.nextafter(x,-np.inf)


@strict
def up(x):
    return np.nextafter(x,np.inf)


@strict
def log_unit(t):
    # 1 <= t <= 2. Bound all basic operations; no vendor transcendental in the log.
    denlo=down(t+1.0); denhi=up(t+1.0)
    u0=max(0.0,down(max(0.0,down(t-1.0))/denhi))
    u1=up(up(t-1.0)/denlo)
    sq0=max(0.0,down(u0*u0)); sq1=up(u1*u1)
    v0,v1=u0,u1; l,h=0.0,0.0
    for j in range(20):
        den=2*j+1
        l=down(l+down(v0/den)); h=up(h+up(v1/den))
        v0=max(0.0,down(v0*sq0)); v1=up(v1*sq1)
    rem=up(v1/down(41.0*down(1.0-sq1)))
    return down(2.0*l),up(2.0*up(h+rem))


@strict
def log64(x):
    if not math.isfinite(x) or x<=0.0: return -np.inf,np.inf
    m,k=math.frexp(x); t=2.0*m; k-=1
    l,h=log_unit(t); a,b=log_unit(2.0)
    if k<0: a,b=b,a
    return down(l+down(k*a)),up(h+up(k*b))


@strict
def sinr_hi(x,y,r):
    # x upper, y and r lower. Keep the interference term in [0,1].
    if not (math.isfinite(x) and math.isfinite(y)): return np.inf
    loss=max(0.0,down(down(r*y)/up(1.0+y)))
    return up(x*up(1.0-loss))


@strict
def rate_hi(g0,G0,g1,G1,r,a,A,b,B):
    X=up(G0*A); Y=up(G1*B)
    x=max(0.0,down(g0*a)); y=max(0.0,down(g1*b))
    l1=log64(up(1.0+sinr_hi(X,y,r)))[1]
    l2=log64(up(1.0+sinr_hi(Y,x,r)))[1]
    return up(l1+l2)


@strict
def price_hi(q,a,b,lam):
    if not math.isfinite(q): return np.inf
    cost=down(lam*max(0.0,down(a+b)))
    v=up(q-cost)
    return v if math.isfinite(v) else np.inf


@strict
def roots(g,G,h,H,r,a,A):
    n=len(r); out=np.empty(n)
    for i in range(n):
        out[i]=rate_hi(g[i],G[i],h[i],H[i],r[i],a,A,a,A)
    return out


@strict
def root_prices(cached,low,lam):
    out=np.empty(len(cached))
    for i in range(len(cached)): out[i]=price_hi(cached[i],low,low,lam)
    return out


@strict
def refine(roots_priced,g,G,h,H,r,low,high,lam,selected):
    # 4 x 4 leaves; each chosen rectangle commits only after every leaf is covered.
    out=roots_priced.copy(); grid=np.empty(5); grid[0]=low; grid[4]=high
    for i in range(1,4): grid[i]=min(high,max(grid[i-1],low+(high-low)*(i/4.0)))
    for e in selected:
        z=-np.inf
        for i in range(4):
            for j in range(4):
                a,A,b,B=grid[i],grid[i+1],grid[j],grid[j+1]
                q=rate_hi(g[e],G[e],h[e],H[e],r[e],a,A,b,B)
                z=max(z,price_hi(q,a,b,lam))
        out[e]=min(out[e],z)
    return out


def checked_table(g,G,h,H,r,low,high,prices,beta,priority,budget):
    """One flattened row per edge×tone (tones contiguous); inputs are outward endpoints."""
    r=np.asarray(r,dtype=np.float64)
    if r.ndim!=1 or not r.size: raise ValueError("nonempty flattened table required")
    g,G,h,H=(np.asarray(v,dtype=np.float64) for v in (g,G,h,H))
    beta=np.asarray(beta,dtype=np.float64); priority=np.asarray(priority,dtype=np.float64)
    if (any(v.shape!=r.shape for v in (g,G,h,H,priority)) or beta.ndim!=1 or not beta.size
        or r.size%beta.size or len(prices)<1 or len(prices)>4 or not isinstance(budget,int) or budget<0):
        raise ValueError("invalid dimensions or work budget")
    if (not all(np.isfinite(v).all() for v in (g,G,h,H,r,beta,priority,prices))
        or np.any(g<0) or np.any(h<0) or np.any(g>G) or np.any(h>H) or np.any((r<0)|(r>1))
        or not (0<=low<=high<np.inf) or min(prices)<0):
        raise ValueError("invalid endpoint or price")
    if not gradual(): raise RuntimeError("binary64 gradual underflow required")
    cached=roots(g,G,h,H,r,low,high); tables=[]; counts=[]
    for lam in prices:
        root=root_prices(cached,low,lam)
        adjusted=root.reshape(-1,beta.size)-beta
        # Top two tones per edge compete for a hard global budget. This is a priority only.
        best=np.argsort(-adjusted,axis=1,kind="stable")[:,:min(2,beta.size)]
        pool=(best+np.arange(best.shape[0])[:,None]*beta.size).ravel()
        chosen=pool[np.lexsort((pool,-priority[pool]))[:budget]]
        tables.append(refine(root,g,G,h,H,r,low,high,lam,chosen))
        counts.append(len(chosen))
    return tables,(r.size,tuple(counts))


@strict
def gradual():
    x=np.nextafter(0.0,1.0)
    return x>0 and x+x>x and down(1.0)<1.0<up(1.0)
