"""Deterministic outward bounds on the Gaussian integrals, using only integers/Fraction."""
from fractions import Fraction as F
from math import comb, factorial, isqrt

D=1<<144
ONE=(D,D)
ZERO=(0,0)


def enclose(x):
    x=F(x)*D
    return x.numerator//x.denominator, -(-x.numerator//x.denominator)


def add(a,b): return a[0]+b[0],a[1]+b[1]
def scale(a,k): return a[0]*k,a[1]*k
def positive_diff(a,b): return max(0,a[0]-b[1]),max(0,a[1]-b[0])
def mul(a,b): return a[0]*b[0]//D, -(-a[1]*b[1]//D)
def div(a,b):
    assert b[0]>0
    return a[0]*D//b[1],-(-a[1]*D//b[0])


def sqrt_box(a):
    l,h=isqrt(a[0]*D),isqrt(a[1]*D)
    return l,h+(h*h!=a[1]*D)


def power(a,k):
    v=ONE
    while k:
        if k%2: v=mul(v,a)
        a=mul(a,a);k//=2
    return v


def log_series(u):
    u2=mul(u,u); v=u; out=ZERO; n=18
    for j in range(n):
        out=add(out,div(scale(v,2),enclose(2*j+1))); v=mul(v,u2)
    # Uniform remainder for 0 <= u <= 1/3.
    return out[0],out[1]+enclose(F(9,4*(2*n+1)*3**(2*n+1)))[1]


LN2=log_series(enclose(F(1,3)))


def ln_tick(x):
    assert x>=D
    k=x.bit_length()-D.bit_length(); base=D<<k
    return add(scale(LN2,k),log_series(enclose(F(x-base,x+base))))


def binom_cdf_at(f):
    """P(at most 5 failures among 256); f is the single-block success probability."""
    yes=(f,f);no=(D-f,D-f); out=ZERO
    for j in range(6):
        out=add(out,scale(mul(power(no,j),power(yes,256-j)),comb(256,j)))
    return max(0,out[0]),min(D,out[1])


def score_cdf(q,shape,m):
    x=q*q; u=x/1024; term=F(1); total=term
    for j in range(1,22):
        term *= -u/j; total+=term
    # exp(-u) is between the adjacent odd/even Taylor sums on [0,1/4].
    expbox=(enclose(total)[0],enclose(total+term*(-u)/22)[1])
    tail=mul(power(expbox,1024),enclose(sum(x**j/F(factorial(j)) for j in range(shape))))
    single=positive_diff(ONE,tail)
    block=power(single,m)
    return binom_cdf_at(block[0])[0],binom_cdf_at(block[1])[1]


def rates(rad,amplitude):
    up_factor=add(ONE,power(add(amplitude,rad),2))
    lo_factor=add(ONE,div(power(positive_diff(amplitude,rad),2),add(ONE,power(rad,2))))
    def bits(a): return div(scale((ln_tick(a[0])[0],ln_tick(a[1])[1]),2),LN2)
    return bits(up_factor),bits(lo_factor)


def certified_gaussian():
    # Positive Stieltjes-bin masses times monotone endpoint bounds, plus an analytic tail.
    res={}; step=128; nu=sqrt_box(enclose(F(1,32)))
    for name,shape,m in (("vector",16,512),("projected",1,64)):
        accum=[ZERO]*5; prev=None; cprev=ZERO
        for j in range(16*step+1):
            q=F(j,step); rad=mul(nu,enclose(q)); c=score_cdf(q,shape,m)
            vals=[rad,*rates(rad,sqrt_box(enclose(10))),*rates(rad,sqrt_box(enclose(160)))]
            if prev is not None:
                mass=positive_diff(c,cprev)
                for k,(v0,v1) in enumerate(zip(prev,vals)):
                    box=(min(v0[0],v1[0]),max(v0[1],v1[1]))
                    accum[k]=add(accum[k],mul(mass,box))
            prev,cprev=vals,c
        # q>=16: all reported outputs <= 32*q^2 for both choices of amplitude.
        tail=enclose(F(32*256*m*(2**shape)*(16**2+2),2**128))[1]
        res[name]=[(F(a,D),F(b+tail,D)) for a,b in accum]
    return res
