"""Directly observed scalar phase stress; MSE controls, not physical array-throughput claims."""
from grid import *
from scipy.special import ive
from scipy.optimize import brentq
import math
def params(law,m):
    if law=='binary':return np.arccos(m),2*m*m-1
    if law=='uniform':
        a=brentq(lambda a:np.sinc(a/np.pi)-m,.0001,np.pi);return a,np.sinc(2*a/np.pi)
    if law=='wrapped':return np.sqrt(-2*np.log(m)),m**4
    a=brentq(lambda x:ive(1,x)/ive(0,x)-m,1e-6,100);return a,ive(2,a)/ive(0,a)
def draw(r,law,a,n):
    if law=='binary':return r.choice([-a,a],n)
    if law=='uniform':return r.uniform(-a,a,n)
    if law=='wrapped':return r.normal(0,a,n)
    return r.vonmises(0,a,n)
def calc(m,c,assume):
    v=1-m*m;noise=.5;vr=(v+c)/2;vi=(v-c)/2;ar=(v+assume)/2;ai=(v-assume)/2
    wr=ar/(ar+noise/2);wi=ai/(ai+noise/2)
    return (1-wr)**2*vr+wr*wr*noise/2+(1-wi)**2*vi+wi*wi*noise/2
def run():
    guard();rr=[];sy=[];rng=np.random.default_rng(313725)
    for m in (.70,.90):
        for law in ('binary','uniform','wrapped','von_mises'):
            a,m2=params(law,m);c=m2-m*m;ordinary=calc(m,c,0);oracle=calc(m,c,c);den=ordinary-oracle
            for i in range(128):
                eps=draw(rng,law,a,1024)
                # Same realization across M; the scalar minimax comparison deliberately assumes the known m1.
                for M in (16,64,256,1024):
                    hw=np.sqrt(2*np.log(4/.05)/M);x1=np.cos(eps[:M]).mean();x2=np.cos(2*eps[:M]).mean();v=1-m*m
                    lo=max(-v,x2-hw-m*m);hi=min(v,x2+hw-m*m)
                    star=0 if lo>hi else np.clip(0,lo,hi)
                    for policy,c0 in [('ordinary',0),('oracle',c),('binary_assumed',m*m-1),('minimax_known_mean',star)]:
                        mse=calc(m,c,c0)
                        rr.append(dict(m1=m,law=law,block=i,M=M,policy=policy,true_c=c,m2=m2,assumed_c=c0,ordinary_mse=ordinary,oracle_mse=oracle,MSE=mse,retained_gain='' if abs(den)<1e-15 else (ordinary-mse)/den,joint_moment_hit=int(abs(x1-m)<=hw and abs(x2-m2)<=hw),empty=int(lo>hi)))
                # Two taps share an oscillator, with different tap phases; cross-tap terms are retained.
                w=np.exp(1j*eps)-m;tap=np.stack((w,.6j*w),axis=1);ind=np.stack((w,.6j*(np.exp(1j*draw(rng,law,a,len(w)))-m)),axis=1)
                for share,x in [('AP_shared',tap),('independent',ind)]:
                    x=x-x.mean(0);cov=x.T@x.conj()/len(x);ps=x.T@x/len(x);aug=np.block([[cov,ps],[ps.conj(),cov.conj()]])
                    assert np.linalg.eigvalsh(aug).min()>-1e-12
                    sy.append(dict(m1=m,law=law,block=i,regime=share,cross_tap_abs=abs(ps[0,1]),minimum_augmented_eigenvalue=np.linalg.eigvalsh(aug).min()))
    putcsv(root3/'results/phase_mse.csv',rr);putcsv(root3/'results/cross_tap.csv',sy)
if __name__=='__main__':run()

