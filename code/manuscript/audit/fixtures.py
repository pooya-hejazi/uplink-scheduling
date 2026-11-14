"""Alternative exhaustive formulation of the rational toys; replay the entire original fixture corpus too."""
import contextlib,itertools,math,runpy
from fractions import Fraction as F
from decimal import Decimal as D,localcontext
import numpy as np
from scipy import integrate,special,stats
from prepare import OUT,SRC,dump
from sample_dp import permutations,brute
def assignments(k):
    return [[tuple(x) for x in v] for v in permutations(k).tolist()]
def enumerate_table(k,H,beta):
    S=k//2;sched=assignments(k); edges=list(itertools.combinations(range(k),2))
    w={e:max(H[e,j]-beta[j] for j in range(S)) for e in edges}
    # Select a relaxation-optimal unlabelled matching lexicographically, then enumerate all permutations of labels.
    opt=max(sum(H[e,j] for j,e in enumerate(m)) for m in sched)
    unlabelled=sorted({tuple(sorted(m)) for m in sched})
    relaxed=max(sum(w[e] for e in m) for m in unlabelled)
    m=next(m for m in unlabelled if sum(w[e] for e in m)==relaxed)
    A=max(sum(H[e,j] for j,e in enumerate(order)) for order in itertools.permutations(m))
    R=sum(beta)+relaxed;Sd=S*max(w[e]-min(H[e,j]-beta[j] for j in range(S)) for e in edges)
    assert A<=opt<=R and R-opt<=R-A<=Sd
    return opt,R,R-A,Sd
def main():
    from verify_gate1 import log_interval
    from verifier64 import log64
    from matching import engine,match
    assert engine is not None
    # Exhaustively compare the newly linked C++ helper with integer enumeration; larger samples use exact Python certificates.
    rng=np.random.default_rng(186420);nmat=0
    for k in [2,4,6,8,16,32,64]:
        I,J=np.triu_indices(k,1)
        for w in [rng.integers(-2**28,2**28,len(I)),np.where((I<k//2)==(J<k//2),20,-19),np.zeros(len(I),dtype='int64')]:
            m,y,z,val=match(k,I,J,w)
            assert len(set(m.ravel()))==k and val==sum(int(w[i*(2*k-i-1)//2+j-i-1]) for i,j in np.sort(m,axis=1))
            lhs=y[I]+y[J];obj=sum(map(int,y))
            for B,t in z:
                f=np.isin(np.arange(k),B);lhs+=(f[I]&f[J])*t;obj+=len(B)//2*t
            assert obj==4*val and np.all(lhs>=4*w)
            if k<=8:assert val==brute(np.broadcast_to(w[:,None],(len(w),k//2)),permutations(k),k)
            nmat+=1
    # Root/child rational tables, T1/T2 signed rounding, a zero channel with all four ledger terms positive.
    a=(F(1),F(0));b=a[::-1];c=(F(3,5),F(4,5));d=(-c[1],c[0]);hs=((a,b,c,d),(a,c,b,d))
    inner=lambda x,y:sum(u*v for u,v in zip(x,y))
    strength=lambda p,s:2-inner(hs[s][p[0]],hs[s][p[1]])**2/2
    products=[math.prod(strength(p,j) for j,p in enumerate(m)) for m in assignments(4)]
    assert sorted(products)==[F(1764,625)]*2+[F(91,25)]*4 and max(products)==F(91,25)
    for k in (2,4,6):
        S=k//2;es=list(itertools.combinations(range(k),2))
        for bet in ((F(0),)*S,tuple(F(2*s-3,7) for s in range(S))):
            H={(e,s):F(e[0]-2*e[1],9)+bet[s] for e in es for s in range(S)}
            opt,R,delta,diam=enumerate_table(k,H,bet);assert opt==R and delta==diam==0
    es=list(itertools.combinations(range(6),2));B=[F(-1,3),F(0),F(1,4)]
    H={(e,s):F((7*j+5*s+2*j*s)%17-8,7) for j,e in enumerate(es) for s in range(3)}
    D0,R,dc,sd=enumerate_table(6,H,B);assert (R-D0,dc,sd)==(F(37,84),F(37,84),F(52,7))
    triangles={e:int(e[0]//3==e[1]//3) for e in es}
    assert max(sum(triangles[e] for e in m) for m in assignments(6))==2 and sum(triangles.values())/2==3
    Q=2**40;assert [math.ceil(Q*x) for x in [F(-3,2*Q),F(-1,Q),F(0),F(5,3*Q)]]==[-1,-1,0,2]
    H={(e,s):3-s for e in itertools.combinations(range(4),2) for s in range(2)}
    af,rl,conf,_=enumerate_table(4,H,[0,0])
    terms=[F(1,7),conf,F(5)-4,af+4];assert sum(terms)==F(78,7) and terms==[F(1,7),1,1,9]
    def pair_arg(x,y,r):return (1+y+x+(1-r)*x*y)/(1+y)
    def checked_bound(B):
        (a,A),(b,C)=B;return log_interval(pair_arg(A,b,F(3,4)))[1]+log_interval(pair_arg(C,a,F(3,4)))[1]-(a+b)/5
    lo,mid,hi=F(1,2),F(5,4),F(2);par=checked_bound(((lo,hi),(lo,hi)))
    child=min(par,max(checked_bound(((lo,mid),(lo,hi))),checked_bound(((mid,hi),(lo,hi)))))
    ab=0
    for x,y in itertools.product([lo,mid,hi],repeat=2):
        val=sum(log_interval(z)[0] for z in [pair_arg(x,y,F(3,4)),pair_arg(y,x,F(3,4))])-(x+y)/5
        assert val<=child<=par;ab+=1
    assert pair_arg(0,7,0)==1 and pair_arg(3,2,1)==2 and pair_arg(3,2,0)==4
    for avail in [3,5,8]:
        rail=[1+(v-1)*min(1,F(avail-3,5)) for v in [1,3,4]];assert sum(rail)<=avail and min(rail)>=1 and max(rail)<=4
    assert 2*(1-F(292893,10**6))**2>=1>2*(1-F(292894,10**6))**2
    xf=(F(47,25)**2)/(1+F(1,13)**2);ball=F(9,5)**2/(1+F(1,5)**2);proj=(2-F(3,25))**2/(1+F(1,13)**2)
    assert ball<proj==xf and max(0,2-3)==0 and inner((1,0),(0,7))==0
    for n,alpha,rank in [(256,F(1,40),251),(256,F(1,20),245),(16,F(1,40),17)]:assert math.ceil((1-alpha)*(n+1))==rank
    tie_hits=0;Z=(1,1,2,7,8)
    for k,z0 in enumerate(Z):tie_hits+=z0<=sorted(Z[:k]+Z[k+1:])[2]
    assert tie_hits>=3
    with localcontext() as ctx:
        ctx.prec=100
        for v in [F(1),F(2),F(1,2),F(3,2),F(9,13),F(100,91)]:
            l,u=log_interval(v);ref=(D(v.numerator)/v.denominator).ln()
            assert D(l.numerator)/l.denominator<=ref<=D(u.numerator)/u.denominator
        exp_inputs=[float.fromhex('0x0.0000000000001p-1022'),float.fromhex('0x1.fffffffffffffp+1023'),np.nextafter(1.,0.),1.,np.nextafter(1.,2.),1.5,2.,.91]+[math.ldexp(i,e) for i in (1,1.125,1.75) for e in (-1022,-70,-1,0,30,512)]
        for v in exp_inputs:
            l,u=log64(v);ref=D.from_float(float(v)).ln();assert D.from_float(l)<=ref<=D.from_float(u)
        gap=2*(D(100)/91).ln()
    # Alternative Gaussian integration: expectation of monotone functions using the survival CDF and integration by parts, no inverse CDF or density.
    def gaussian(shape,m,A):
        amp=math.sqrt(A);nu=math.sqrt(1/32);ll=math.log(2)
        def surv(q):
            t=special.gammaincc(shape,q*q)
            if t>=1:return 1.
            if t<=0:return 0.
            blockfail=-math.expm1(m*math.log1p(-float(t)))
            return special.bdtrc(5,256,blockfail)
        def Uder(q):
            x=amp+q*nu;return 4*nu*x/(1+x*x)/ll
        def Lder(q):
            t=q*nu;x=amp-t
            if x<=0:return 0.
            return 2*nu/ll*((2*t-2*x)/(1+t*t+x*x)-2*t/(1+t*t))
        u0=2*math.log1p(A)/ll
        quad=lambda f:integrate.quad(lambda q:surv(q)*f(q),0,16,points=[2,3,4,5,6,7],epsabs=2e-12,limit=160)[0]
        return dict(radius=nu*quad(lambda q:1),upper=u0+quad(Uder),lower=u0+quad(Lder))
    answer={}
    for A in [10,160]:
        ball=gaussian(16,512,A);proj=gaussian(1,64,A);g1=ball['upper']-ball['lower'];g2=ball['upper']-proj['lower']
        expected=([5.278436475,3.006443079] if A==10 else [3.153709814,1.335321612])
        assert abs(g1-expected[0])<6e-10 and abs(g2-expected[1])<6e-10
        answer[str(A)]=dict(ball=ball,projected=proj,ball_gap=g1,projected_gap=g2)
    for name in ['verify_gate1','check_verifier64']:
        print('Running complete archived suite',name,flush=True)
        with (OUT/(name+'.stdout.txt')).open('w',encoding='utf-8') as f,contextlib.redirect_stdout(f):runpy.run_path(str(SRC/'Gate_1'/(name+'.py')),run_name='__main__')
    dump('fixture_summary.json',dict(physical_products=sorted(map(str,products)),physical_gap_nats=str(gap),t2_relaxation_loss=str(R-D0),t2_posterior=str(dc),t2_prior=str(sd),ledger=list(map(str,terms)),gaussian=answer,native_match_controls=nmat,compiled_log_decimal_checks=len(exp_inputs),rational_power_box_grid_points=ab,complete_archived_control_suites=['verify_gate1','check_verifier64'],violations=0))
if __name__=='__main__':main()
