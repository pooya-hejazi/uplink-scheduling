"""Independent two-user continuous optimum using rational Gram and 75-bit real-root isolation."""
from inputs import *
import sympy as s
from fractions import Fraction as F
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING
def mul(a,b):
    p=[v*w for v in a for w in b];return min(p),max(p)
def point(v):return (v,v)
def add(a,b):return a[0]+b[0],a[1]+b[1]
def poly(p,I):
    z=point(F(0))
    for c in p.all_coeffs():z=add(mul(z,I),point(F(c)))
    return z
def bound(h):
    # Scaling both positive powers raises both SINRs: the global maximum spends all K*p_avg.
    a,b=h;ga=sum(F(float(v.real))**2+F(float(v.imag))**2 for v in a);gb=sum(F(float(v.real))**2+F(float(v.imag))**2 for v in b)
    r=i=F(0)
    for u,v in zip(a,b):
        R,I,U,V=map(lambda q:F(float(q)),[u.real,u.imag,v.real,v.imag]);r+=R*U+I*V;i+=R*V-I*U
    cross=ga*gb-r*r-i*i;assert cross>=0
    x=s.symbols('x');q=s.Rational(1,5)-x;A=s.Poly(1+ga*x,x);B=s.Poly(1+gb*q,x);D=s.Poly(1+ga*x+gb*q+cross*x*q,x);E=A*B
    der=2*D.diff()*E-D*E.diff();lo=F(1,20);hi=F(3,20);cand=[point(lo),point(hi)]
    if not der.is_zero:
        for (l,u),_ in der.intervals(eps=s.Rational(1,2**75)):
            l=max(lo,F(l));u=min(hi,F(u))
            if l<=u:cand.append((l,u))
    ys=[]
    for I in cand:
        dd=poly(D,I);ee=poly(E,I);assert min(dd)>0 and min(ee)>0;v=mul(dd,dd);ys.append((v[0]/ee[1],v[1]/ee[0]))
    raw=(max(l for l,r in ys),max(r for l,r in ys))
    with localcontext() as ctx:
        ctx.prec=60
        ctx.rounding=ROUND_FLOOR;l=(Decimal(raw[0].numerator)/Decimal(raw[0].denominator)).ln().next_minus()
        ctx.rounding=ROUND_CEILING;u=(Decimal(raw[1].numerator)/Decimal(raw[1].denominator)).ln().next_plus()
    return np.nextafter(float(l),-np.inf),np.nextafter(float(u),np.inf)
def main():
    from campaign import normalized,rows,putcsv
    guard();w=[]
    for f in geoms:
        for j in range(128):
            a=analytic(f,j);h,_=normalized(a,2,10);lo,hi=bound(h[:,:,0]);v=rows(root/'results/oracle'/f'{f}_{j:03d}.csv')[0]
            # Independently recreated exact input bytes must enclose the same global point.
            assert int(v['k'])==2 and float(v['lo_nats'])<=hi+1e-12 and lo<=float(v['hi_nats'])+1e-12 and hi>=lo
            width=np.nextafter((hi-lo)/np.nextafter(np.log(2.),-np.inf),np.inf);assert width<=1e-6
            w.append(dict(family=f,block=j,k=2,lo_nats=lo,hi_nats=hi,G_oracle=width,resolved=1))
    putcsv(root/'results/exact_two.csv',w);print(len(w),'independent two-user rational oracles; maximum width',max(z['G_oracle'] for z in w))
if __name__=='__main__':main()

