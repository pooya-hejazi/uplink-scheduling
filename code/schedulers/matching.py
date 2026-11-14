"""Pinned native blossom proposal, independent integer dual check. Original exact fallback if unavailable."""
import ctypes as C,sys
from pathlib import Path
import numpy as np
home=Path(__file__).resolve().parent;sys.path.insert(0,str(home.parent/'Gate_2'))
from witness import blossom as reference,check,edgeid,assignment
dll=home/'native/exact_match.dll'
def ptr(a):return C.c_void_p(a.ctypes.data)
engine=None
if dll.exists():
    dll_handle=C.CDLL(str(dll));engine=dll_handle.exact;engine.restype=C.c_int
    engine.argtypes=[C.c_int]+[C.c_void_p]*5
def check4(k,I,J,w,pairs,y,z):
    value=check(k,I,J,4*w,pairs,2*y,z)
    if value%4:raise ArithmeticError('noninteger value')
    return value//4
def match(k,I,J,w):
    w=np.asarray(w,dtype='int64')
    if engine is None:
        p,y,z,m=reference(k,I,J,w);return p,2*y,[(b,4*t) for b,t in z],m
    if not w.size or np.max(abs(w.astype(float)))>=2**47:raise ArithmeticError('matching weight range')
    w=np.ascontiguousarray(w);m=np.empty(k,'int32');y=np.empty(k,'int64');mask=np.empty(k,'uint64');zz=np.empty(k,'int64')
    n=engine(k,ptr(w),ptr(m),ptr(y),ptr(mask),ptr(zz))
    if not 0<=n<=k or (m<0).any() or (m>=k).any() or np.any(m[m]!=np.arange(k)) or np.any(m==np.arange(k)):raise ArithmeticError('native matching failed')
    pairs=np.array([(i,int(m[i])) for i in range(k) if m[i]>i],int)
    # LEMON carries quarter-tick potentials; check against the exact original tick table.
    B=[(tuple(i for i in range(k) if (int(mask[t])>>i)&1),int(zz[t])) for t in range(n)]
    return pairs,y,B,check4(k,I,J,w,pairs,y,B)

