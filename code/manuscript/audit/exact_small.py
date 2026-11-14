"""Global two-user check from rational Gram inputs by Bernstein derivative subdivision (no solver)."""
import math
from decimal import Decimal as D,localcontext,ROUND_FLOOR,ROUND_CEILING
from fractions import Fraction as F
from itertools import zip_longest
from inputs import analytic
from receipts import exact_dyadics,normalized
from prepare import archive,dump,write_rows,read_rows,zipfile
def mul(a,b):
    out=[0]*(len(a)+len(b)-1)
    for i,v in enumerate(a):
        for j,w in enumerate(b):out[i+j]+=v*w
    return out
def poly(p,x):return sum(c*x**i for i,c in enumerate(p))
def bound(h):
    den,R=exact_dyadics(h);a,b=R;ar,ai=a.T;br,bi=b.T
    ga=F(int(sum(ar**2+ai**2)),den**2);gb=F(int(sum(br**2+bi**2)),den**2)
    u=int(sum(ar*br+ai*bi));v=int(sum(ar*bi-ai*br));C=ga*gb-F(u*u+v*v,den**4)
    assert C>=0 and ga>0 and gb>0
    s=F(1,5);a=F(1,20);b=F(3,20)
    det=[1+s*gb,ga-gb+s*C,-C];prod=mul([1,ga],[1+s*gb,-gb])
    deriv=lambda p:[i*c for i,c in enumerate(p) if i]
    P=[2*l-r for l,r in zip_longest(mul(deriv(det),prod),mul(deriv(prod),det),fillvalue=0)]
    while len(P)<4:P.append(F(0))
    y0,y1=poly(P,a),poly(P,b);d=deriv(P)
    co=[y0,y0+(b-a)*poly(d,a)/3,y1-(b-a)*poly(d,b)/3,y1]
    common=math.lcm(*(v.denominator for v in co));co=tuple(int(v*common) for v in co)
    cand=[(a,a),(b,b)]
    def visit(A,B,ctrl,depth):
        if min(ctrl)>=0 or max(ctrl)<=0:return
        if depth>=90:cand.append((A,B));return
        u,v,w,x=ctrl;mid=(A+B)/2;q=u+3*v+3*w+x
        if q==0:cand.append((mid,mid))
        visit(A,mid,(8*u,4*(u+v),2*(u+2*v+w),q),depth+1)
        visit(mid,B,(q,2*(v+2*w+x),4*(w+x),8*x),depth+1)
    visit(a,b,co,0)
    def range_q(p,A,B):
        values=[poly(p,A),poly(p,B)]
        if p[2] and A< -p[1]/(2*p[2]) <B:values.append(poly(p,-p[1]/(2*p[2])))
        return min(values),max(values)
    bounds=[]
    for A,B in cand:
        dl,du=range_q(det,A,B);el,eu=range_q(prod,A,B);assert dl>0 and el>0
        bounds.append((dl*dl/eu,du*du/el))
    lo=max(x[0] for x in bounds);hi=max(x[1] for x in bounds)
    with localcontext() as ctx:
        ctx.prec=80;ctx.rounding=ROUND_FLOOR
        l=(D(lo.numerator)/D(lo.denominator)).ln().next_minus()
        ctx.rounding=ROUND_CEILING
        u=(D(hi.numerator)/D(hi.denominator)).ln().next_plus()
    return l,u,len(cand)
def main():
    out=[]
    with zipfile.ZipFile(archive('Gate_3')) as z:
        for r in read_rows(z.read('Gate_3/results/exact_two.csv')):
            f,i=r['family'],int(r['block']);raw=analytic(f,i);h,_=normalized(raw,2,10);a,b,n=bound(h[:,:,0])
            released_lo=D.from_float(float(r['lo_nats']));released_hi=D.from_float(float(r['hi_nats']))
            assert released_lo<=a<=b<=released_hi,(f,i,a,b,released_lo,released_hi)
            out.append(dict(family=f,block=i,stationary_and_boundary_candidates=n,independent_lo_nats=str(a),independent_hi_nats=str(b),sealed_lo_nats=r['lo_nats'],sealed_hi_nats=r['hi_nats']))
    assert len(out)==512;write_rows('exact_two_replay.csv',out);dump('exact_two_summary.json',dict(analytic_units=len(out),method='exact rational cubic derivative represented in the Bernstein basis and bisected 90 times wherever its convex hull straddles zero; rational candidate boxes, outward 80-digit decimal logarithms',sealed_global_values_enclosed=len(out),interval_failures=0))
if __name__=='__main__':main()
