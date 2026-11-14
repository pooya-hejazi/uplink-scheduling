"""Forward discrete dynamic program; release DP code is not imported for the K=16 check."""
import io,itertools,math,sys
from collections import Counter
from fractions import Fraction as F
from decimal import Decimal as D,localcontext
import numpy as np
from numba import njit
from prepare import OUT,archive,read_rows,write_rows,dump,zipfile,path_hash
from receipts import normalized,dig,Q,PT
from polish import table
from inputs import analytic
@njit(cache=True)
def forward(H,k):
    N=1<<k;sentinel=np.int64(-2**62)
    V=np.full(N,sentinel,dtype=np.int64);V[0]=0
    count=np.empty(N,np.int8);count[0]=0
    for mask in range(1,N):count[mask]=count[mask//2]+mask%2
    for mask in range(N-1):
        if V[mask]==sentinel:continue
        s=count[mask]//2;e=0
        for i in range(k-1):
            if mask&(1<<i):e+=k-i-1;continue
            a=mask|(1<<i)
            for j in range(i+1,k):
                if not mask&(1<<j):
                    b=a|(1<<j)
                    V[b]=max(V[b],V[mask]+H[e,s])
                e+=1
    return V[-1]
def permutations(k):
    return np.asarray([p for p in itertools.permutations(range(k)) if all(p[j]<p[j+1] for j in range(0,k,2))],dtype=int).reshape(-1,k//2,2)
def brute(H,pa,k):
    i,j=pa.transpose(2,0,1);e=i*(2*k-i-1)//2+j-i-1
    val=H[e,np.arange(k//2)].sum(1)
    return int(val.max())
def examine():
    sample=read_rows((OUT/'precommitted_sample.csv').read_bytes());assert len(sample)==58
    nested={k:permutations(k) for k in [2,4,6,8]}
    ctrl=np.random.default_rng(74551)
    for k,maps in nested.items():
        for _ in range(3):
            hw=ctrl.integers(-1000,1000,(k*(k-1)//2,k//2));assert forward(hw,k)==brute(hw,maps,k)
    rows=[];small=[]
    with zipfile.ZipFile(archive('Gate_3')) as z:
        for ix,r in enumerate(sample):
            kind,f,i=r['source'],r['family'],int(r['block'])
            if kind=='analytic':raw=analytic(f,i)
            else:
                with np.load(io.BytesIO(z.read(f'Gate_3/data/pilot_{f}_{i:04}.npz')),allow_pickle=False) as p:raw=p['h']
            vals={int(x['db']):x for x in read_rows(z.read(f'Gate_3/results/grid_{kind}/{f}_{i:03}.csv')) if x['k']=='16'}
            assert set(vals)=={-5,0,10,20}
            for snr,ref in sorted(vals.items()):
                h,_=normalized(raw,16,snr);H,_,I,J,lam,_=table(h)
                assert np.max(np.abs(H))<2**53
                optimum=int(forward(H,16));expected=int(ref['dp_H'])
                assert optimum==expected and int(ref['matched_A'])<=optimum<=int(ref['R']),(kind,f,i,snr,optimum,expected)
                gap=(int(ref['R'])-optimum)/(Q*8*math.log(2));assert math.isclose(gap,float(ref['loss']),rel_tol=1e-15,abs_tol=1e-18)
                assert int(ref['R'])-int(ref['matched_A'])>=int(ref['R'])-optimum
                rows.append(dict(source=kind,family=f,block=i,k=16,db=snr,raw_sha256=dig(h),table_sha256=dig(H),sealed_dp_H=expected,forward_dp_H=optimum,relaxed_R=int(ref['R']),matched_A=int(ref['matched_A']),price=lam))
            if kind=='analytic':
                # The released nested small continuous cases use K=2/4/6/8 at 10 dB (only K=16 stores an integer optimum).
                oracle=read_rows(z.read(f'Gate_3/results/oracle/{f}_{i:03}.csv'))
                c128=raw.astype(np.complex128);sc=np.sqrt(10/(.1*np.median(np.mean(np.abs(c128)**2,axis=1))))
                for ref in oracle:
                    k=int(ref['k']);S=k//2;bins=(np.arange(S)*raw.shape[-1])//S
                    h=np.ascontiguousarray(c128[:k,:,bins]*sc);H,_,_,_,lam,_=table(h)
                    integer=int(forward(H,k));exhaustive=brute(H,nested[k],k)
                    assert integer==exhaustive and len(nested[k])==int(ref['labelled'])==math.factorial(k)//2**S
                    # This is an independently checkable bound from the priced integer table. A continuous branch-and-bound interval is a different quantity.
                    dpU=(integer/Q)+lam*k*.1
                    assert dpU>=float(ref['lo_nats'])
                    small.append(dict(source=kind,family=f,block=i,k=k,db=10,raw_sha256=dig(h),table_sha256=dig(H),forward_dp_H=integer,bruteforce_H=exhaustive,enumerated_labelled_schedules=len(nested[k]),dp_upper_nats=dpU,sealed_continuous_lower_nats=ref['lo_nats'],sealed_continuous_upper_nats=ref['hi_nats']))
            if (ix+1)%10==0:print('sample',ix+1,'/58',flush=True)
    write_rows('sample_dp.csv',rows);write_rows('nested_small_dp.csv',small)
    dump('sample_dp_summary.json',dict(population=1152,sampled_units=len(sample),strata=dict(Counter(r['source'] for r in sample)),k16_registered_optima_checked=len(rows),nested_analytic_tables_exhaustively_enumerated=len(small),nested_schedule_count=sum(r['enumerated_labelled_schedules'] for r in small),signed_random_enumeration_controls=12,exact_tick_mismatches=0))
if __name__=='__main__':examine()
