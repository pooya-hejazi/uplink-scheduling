"""Compare the compiled lazy-table kernel with the independent exact reference."""
import math
from fractions import Fraction as F
from itertools import product

import numba
import numpy as np

from verifier64 import checked_table, gradual, log64
from verify_gate1 import log_interval, rate_arg


def main():
    print(f"compiled-kernel check | Numba {numba.__version__} | NumPy {np.__version__}")
    assert gradual()
    xs=[float.fromhex('0x0.0000000000001p-1022'),float.fromhex('0x1.fffffffffffffp+1023'),
        np.nextafter(1.,0.),1.,np.nextafter(1.,2.),3/2,2.,91/100]
    for exp in (-1022,-70,-1,0,30,512):
        xs.extend(math.ldexp(v,exp) for v in (1.,1.125,1.75))
    for x in xs:
        a,b=log64(x); l,h=log_interval(F(x),32)
        assert F(a)<=l<=h<=F(b),x
    assert log64(-1)==(-np.inf,np.inf)
    print(f"PASS binary64 logs on {len(xs)} inputs including subnormal, max finite and both sides of 1")
    g=np.array([0.,.25,1.,2.,.75,1.25]*2)
    h=g[::-1].copy(); r=np.array([0.,.25,1.,.5,.125,.875]*2)
    G=g+.125; H=h+.25; beta=np.array([-.5,.25,.5]); pr=np.arange(len(g),dtype=float)
    low,high=.125,.875; ps=[0.,.25]
    root,_=checked_table(g,G,h,H,r,low,high,ps,beta,pr,0)
    lazy,counts=checked_table(g,G,h,H,r,low,high,ps,beta,pr,2)
    for j,lam in enumerate(ps):
        assert np.all(lazy[j]<=root[j]) and np.count_nonzero(lazy[j]!=root[j])<=2
        for i,z in enumerate(lazy[j]):
            for a,b in product((F(low),F(1,2),F(high)),repeat=2):
                # Independent upper rational log oracle on the sampled power and gain intervals.
                q=log_interval(rate_arg(F(G[i])*a,F(h[i])*b,F(r[i])))[1]
                q+=log_interval(rate_arg(F(H[i])*b,F(g[i])*a,F(r[i])))[1]
                assert F(z)>=q-F(lam)*(a+b),(j,i,a,b)
    assert counts==(12,(2,2))
    for power_rail,arr in ((-1,g),(low,np.full(len(g),np.nan))):
        try: checked_table(arr,G,h,H,r,power_rail,high,ps,beta,pr,1)
        except ValueError: pass
        else: raise AssertionError("bad input accepted")
    x=np.array([np.finfo(float).max])
    out,_=checked_table(x,x,x,x,np.array([0.]),1.,2.,[0.],np.array([0.]),np.array([0.]),1)
    assert out[0][0]==np.inf
    print("PASS lazy roots, bounded refinements, exact rational comparisons, invalid/overflow handling")
    for K,cap in ((32,32),(64,128)):
        S=K//2; M=S*K*(K-1)//2; x=np.arange(M)
        g=(2+(x%13)).astype('float64')*.125; h=(2+(x%11)).astype('float64')*.125
        r=(x%9)/8; pr=((73*x)%101).astype('float64'); beta=np.zeros(S)
        tabs,counts=checked_table(g,g,h,h,r,.125,.875,[0.,.125,.25,.5],beta,pr,cap)
        assert all(np.isfinite(t).all() for t in tabs) and counts==(M,(cap,)*4)
        eager=4*16*M; leaves=16*sum(counts[1]); calls=M+leaves
        print(f"  K={K} unpriced roots={M} priced root updates={4*M} "
              f"refinement leaves={leaves} eager leaves={eager} "
              f"optional-leaf ratio={eager/leaves:.2f}x all rate-box call ratio={eager/calls:.3f}x")
    print("ALL COMPILED KERNEL CHECKS PASSED; counts are not end-to-end latency measurements")


if __name__=="__main__":
    if not __debug__: raise RuntimeError("run without -O")
    main()
