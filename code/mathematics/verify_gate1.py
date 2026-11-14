"""Gate 1 reference fixtures. Run with Python 3.11+ and SciPy; no random draws."""
import math
import platform
from fractions import Fraction as F
from itertools import combinations, permutations, product

import scipy
from scipy import integrate, special

GAMMA = 1 << 40


def log_interval(x, n=24):
    """Rational log enclosure, including x<1 and negative range exponents."""
    if x <= 0 or n < 1:
        raise ValueError("positive log argument and order required")
    x = F(x)
    k = x.numerator.bit_length() - x.denominator.bit_length()
    t = x / (F(2) ** k)
    if t < 1:
        k -= 1
        t *= 2
    assert 1 <= t < 2

    def series(z):
        u = (z - 1) / (z + 1)
        lo = 2 * sum(u**(2*i+1) / (2*i+1) for i in range(n))
        return lo, lo + 2*u**(2*n+1) / ((2*n+1)*(1-u*u))

    a, b = series(t)
    c, d = series(F(2))
    return a + min(k*c, k*d), b + max(k*c, k*d)


def dot(x, y):
    return sum(a*b for a, b in zip(x, y, strict=True))


def matchings(vertices):
    if not vertices:
        yield ()
    else:
        i = vertices[0]
        for j in vertices[1:]:
            for rest in matchings(tuple(v for v in vertices if v not in (i, j))):
                yield ((i, j),) + rest


def table_values(K, H, beta):
    S = K//2
    mats = list(matchings(tuple(range(K))))
    w = {e: max(H[e,s]-beta[s] for s in range(S))
         for e in combinations(range(K), 2)}
    mw = max(sum(w[e] for e in m) for m in mats)
    m = next(m for m in mats if sum(w[e] for e in m) == mw)

    def assign(m):
        return max((sum(H[e,s] for e,s in zip(m, ss)), ss)
                   for ss in permutations(range(S)))
    A, ss = assign(m)
    D = max(assign(m0)[0] for m0 in mats)
    delta = sum(w[e]-H[e,s]+beta[s] for e,s in zip(m,ss))
    diameter = max(w[e]-min(H[e,s]-beta[s] for s in range(S)) for e in w)
    R = sum(beta)+mw
    assert 0 <= R-D <= delta == R-A
    assert delta <= S*diameter
    return D, R, delta, S*diameter


def discrete():
    a,b=(F(1),F(0)),(F(0),F(1))
    c,d=(F(3,5),F(4,5)),(F(-4,5),F(3,5))
    hs=((a,b,c,d),(a,c,b,d))
    pairs=list(combinations(range(4),2))
    def arg(e,s):
        i,j=e
        return 2-dot(hs[s][i],hs[s][j])**2/2
    vals=[]
    for e in pairs:
        f=tuple(sorted(set(range(4))-set(e)))
        val=arg(e,0)*arg(f,1)
        vals.append(val)
        print(f"  tone1={e[0]+1}{e[1]+1} tone2={f[0]+1}{f[1]+1} product={val}")
    assert sorted(vals)==[F(1764,625)]*2+[F(91,25)]*4
    assert F(4)/max(vals)==F(100,91)
    lo,hi=log_interval(F(100,91))
    decscale=10**12
    print(f"  exact gap=2*ln(100/91); interval in 1e-12 aggregate nats: "
          f"[{math.floor(2*lo*decscale)}, {math.ceil(2*hi*decscale)}]")
    for beta in ([0,0],[0,3],[-5,2]):
        assert max(2+beta[1]-beta[0],2+beta[0]-beta[1])>=2
    for K in (2,4,6):
        edges=list(combinations(range(K),2)); S=K//2
        for beta in ([F(0)]*S,[F(2*s-3,7) for s in range(S)]):
            H={(e,s):F(e[0]-2*e[1],9)+beta[s] for e in edges for s in range(S)}
            D,R,dc,sd=table_values(K,H,beta)
            assert D==R and dc==sd==0
    H={(e,s):F((i*7+s*5+i*s*2)%17-8,7) for i,e in enumerate(combinations(range(6),2))
       for s in range(3)}
    D,R,dc,sd=table_values(6,H,[F(-1,3),F(0),F(1,4)])
    print(f"  K=6 same-table check: relaxation-label={R-D}, posterior={dc}, prior={sd}")
    print("PASS T2 six labels, flat and separable K=2/4/6, posterior conflict inequality")

    # Two triangles: the odd-set dual beats a degree-only fractional solution.
    tris=({0,1,2},{3,4,5}); edges=list(combinations(range(6),2))
    w={e:F(1) if any(set(e)<=t for t in tris) else F(0) for e in edges}
    assert all(sum(set(e)<=t for t in tris)>=v for e,v in w.items())
    assert max(sum(w[e] for e in m) for m in matchings(tuple(range(6))))==2
    assert sum((len(t)//2) for t in tris)==2 and sum(v/2 for v in w.values())==3
    ws=[F(-3,2*GAMMA),F(-1,GAMMA),F(0),F(5,3*GAMMA)]
    for w0 in ws:
        assert 0 <= F(math.ceil(GAMMA*w0),GAMMA)-w0 < F(1,GAMMA)
    assert [math.ceil(GAMMA*w0) for w0 in ws]==[-1,-1,0,2]
    print("PASS T1 odd-set integer witness=2 versus fractional=3; signed ceil ticks=-1,-1,0,2")
    # A physical positive-slack ledger: loose table, feasible low rates at zero channels.
    H={(e,s):F(3 if s==0 else 2) for e in pairs for s in range(2)}
    D,R,dc,_=table_values(4,H,[0,0])
    price,P,total=F(1),F(5),F(4)
    U=price*P+R+F(1,7); L=F(0)
    ledger=[U-price*P-R,dc,price*(P-total),D+price*total-L]
    assert min(ledger)>=0 and sum(ledger)==U-L
    print("PASS four-term same-candidate ledger:", "+".join(map(str,ledger)), "=", U-L)


def rate_arg(x,y,r):
    return 1+x*(1-r*y/(1+y))


def interval_and_receiver():
    def box_hi(B,r,lam):
        (x,X),(y,Y)=B
        return (log_interval(rate_arg(X,y,r))[1]+log_interval(rate_arg(Y,x,r))[1]
                -lam*(x+y))
    B=((F(1,2),F(2)),(F(1,2),F(2))); mid=F(5,4); r=F(3,4); lam=F(1,5)
    children=(((B[0][0],mid),B[1]),((mid,B[0][1]),B[1]))
    parent=box_hi(B,r,lam); child=min(parent,max(box_hi(C,r,lam) for C in children))
    for x,y in product((B[0][0],mid,B[0][1]),repeat=2):
        lower=log_interval(rate_arg(x,y,r))[0]+log_interval(rate_arg(y,x,r))[0]-lam*(x+y)
        assert lower<=child<=parent
    assert children[0][0][1]==children[1][0][0] and box_hi(B,r,lam)==parent
    assert rate_arg(F(0),F(7),F(0))==1 and rate_arg(F(3),F(2),F(1))==2
    assert rate_arg(F(3),F(2),F(0))==4
    singleton=((F(1),F(1)),(F(1),F(1)))
    assert box_hi(singleton,F(1),F(0))>=2*log_interval(F(3,2))[0]
    rails=[F(1),F(3),F(4)]; pmin=F(1)
    for P in (F(3),F(5),F(8)):
        f=min(F(1),(P-3*pmin)/sum(v-pmin for v in rails))
        p=[pmin+(v-pmin)*f for v in rails]
        assert all(pmin<=x<=4 for x in p) and sum(p)<=P
    eps=F(1,10**6)
    # r <= 1-1/sqrt(2) iff 2(1-r)^2 >= 1 on [0,1].
    for rr,pred in ((F(292893,10**6),True),(F(292893,10**6)+eps,False)):
        assert (2*(1-rr)**2>=1)==pred
    for q in (F(1),F(2),F(1,2),F(3,2),F(9,13),F(100,91)):
        l,u=log_interval(q); il,iu=log_interval(1/q)
        assert l<=u and l+il<=0<=u+iu and u-l<F(1,2**65)
    l,u=log_interval(F(2))
    assert F(693147180559945309,10**18)<l<u<F(693147180559945310,10**18)
    print("PASS log enclosure, signed exponents, root/child coverage, zero gain, rails and curvature neighbors")

    # Desired and interfering error in an unobserved antenna changes oracle, not the projection.
    h0=(F(2),F(0)); h1=(F(0),F(2)); v=(F(1),F(0))
    e0=(F(-3,25),F(4,25)); e1=(F(1,13),F(0)); eps=F(1,5)
    hh0=tuple(a+b for a,b in zip(h0,e0)); hh1=tuple(a+b for a,b in zip(h1,e1))
    assert dot(e0,e0)<=eps**2 and dot(e1,e1)<=eps**2
    def lower(D,I):
        return max(F(0),abs(dot(v,h0))-D)**2/(dot(v,v)+(abs(dot(v,h1))+I)**2)
    actual=abs(dot(v,hh0))**2/(dot(v,v)+abs(dot(v,hh1))**2)
    assert lower(eps,eps)<=lower(abs(dot(v,e0)),abs(dot(v,e1)))<=actual
    assert lower(F(3),eps)==0
    assert dot(v,(0,7))==0 and dot((0,7),(0,7))==49
    print("PASS T3 vector/projected desired+interference, null crossing, oracle orthogonal escape")
    def rank(n,a): return math.ceil((n+1)*(1-a))
    assert (rank(256,F(1,40)),rank(256,F(1,20)),rank(16,F(1,40)))==(251,245,17)
    Z=(1,1,2,7,8); k=3
    hits=sum(z<=sorted(Z[:j]+Z[j+1:])[k-1] for j,z in enumerate(Z))
    assert hits>=k
    print("PASS T4 conservative ties; n=256 ranks 251/245; n=16 rank 17 -> infinity")


def expectation(shape, draws, k, n, func):
    """Integrate in uniform order-statistic coordinates; func maps radius to output."""
    def value(t):
        b=special.betaincinv(k,n+1-k,t)
        # Invert the single-link survival function without cancellation near b=1.
        survival=-math.expm1(math.log(b)/draws)
        q=math.sqrt(special.gammainccinv(shape,survival))
        return func(q)
    val,err=integrate.quad(value,0,1,epsabs=4e-10,epsrel=4e-10,limit=250)
    return val,err


def gaussian():
    from gaussian_bounds import certified_gaussian
    N,K,S,n,k=16,32,16,256,251
    a=math.sqrt(10); nu=1/math.sqrt(32); ln2=math.log(2)
    def upper(t): return 2*math.log1p((a+t)**2)/ln2
    def lower(t): return 2*math.log1p(max(0.,a-t)**2/(1+t*t))/ln2
    def calc(shape,draws,fn):
        v,e=expectation(shape,draws,k,n,lambda q:fn(nu*q))
        assert math.isfinite(v) and e<2e-8
        return v
    def independent_check(shape,draws,fn):
        # Different integration variable, no beta or gamma inverse. Tail beyond q=16 is negligible.
        cons=special.betaln(k,n+1-k)+special.gammaln(shape)
        def integrand(q):
            z=q*q
            one_tail=special.gammaincc(shape,z)
            if not 0<one_tail<1:return 0.
            logF=math.log1p(-one_tail); logB=draws*logF
            bb=-math.expm1(logB)
            if bb==0:return 0.
            lp=(math.log(2*draws)+(2*shape-1)*math.log(q)-z-cons
                +(draws-1)*logF+(k-1)*logB+(n-k)*math.log(bb))
            return math.exp(lp)*fn(q*nu)
        return integrate.quad(integrand,0,16,points=[3,4,5,6,7],epsabs=2e-11,limit=250)[0]
    print("Gaussian fixture: conditional proper complex Gaussian errors; N=16 K=32 S=16; "
          "nominal combined SNR=10 dB; p=1, noise=I, nu^2=1/32, n=256; alpha_F=alpha_P=1/40")
    rigor=certified_gaussian()
    def show(ab):
        # Integer outward decimal policy, including negative numbers.
        return f"[{math.floor(ab[0]*10**6)/10**6:.6f}, {math.ceil(ab[1]*10**6)/10**6:.6f}]"
    for z,(A2,convention) in enumerate(((10,"combined"),(160,"per antenna"))):
        a=math.sqrt(A2)
        print(f"  nominal 10 dB {convention}, A^2={A2}")
        vals=[]
        for name,shape,draws in (("vector",N,K*S),("projected",1,2*K)):
            outputs=[]
            for fn,idx in ((lambda t:t,0),(lower,2*z+2),(upper,2*z+1)):
                one=calc(shape,draws,fn); two=independent_check(shape,draws,fn)
                assert abs(one-two)<2e-8,(one,two)
                assert rigor[name][idx][0]<F(one)<rigor[name][idx][1]
                outputs.append(one)
            vals.append(outputs)
            print(f"    {name}: shape={shape}, primitives={draws}, rank={k}; "
                  f"E[radius]={outputs[0]:.9f} in {show(rigor[name][0])}, E[L]={outputs[1]:.9f}")
        (ev,lv,up),(ep,lp,_)=vals
        assert 0<ep<ev and 0<lv<lp<up
        ub=rigor["vector"][2*z+1]
        print(f"    E[U]={up:.9f}, ball and projected comparisons use identical U")
        for val,typ in ((lv,"vector"),(lp,"projected")):
            lb=rigor[typ][2*z+2]
            print(f"    E[G_{typ}]={up-val:.9f} bit/s/Hz in {show((ub[0]-lb[1],ub[1]-lb[0]))}")
    print(f"  radius ratio={ev/ep:.9f}; nominal no-error gap=0")
    print("PASS exact-law integrals: two deterministic quadratures and outward integer bounds")


if __name__=="__main__":
    if not __debug__:
        raise RuntimeError("run without -O: audit assertions must be enabled")
    print(f"Gate 1 | Python {platform.python_version()} | SciPy {scipy.__version__}")
    discrete()
    interval_and_receiver()
    gaussian()
    print("ALL REFERENCE FIXTURES PASSED")
