"""Complete labelled enumeration with outward continuous power-box subdivision; limits are explicit."""
from grid import *
from enclosures import up,dn,mix
from numba import njit
import heapq
@njit(cache=True)
def perbox(i,j,s,g,G,r,e,lo,hi,lam,T):
    fromlo=dn(lo[i]/PT);tolo=up(hi[i]/PT);othlo=dn(lo[j]/PT);othhi=up(hi[j]/PT)
    p0=max(fromlo,min(tolo,1/max(1,lam)-1/max(1e-250,G[i,s])));p1=max(othlo,min(othhi,1/max(1,lam)-1/max(1e-250,G[j,s])))
    value=0.
    for t in (0,1):
        v=G[i,s] if t==0 else G[j,s];p=p0 if t==0 else p1;l=fromlo if t==0 else othlo;h=tolo if t==0 else othhi
        z=up(1+up(v*p));z0=dn(1+dn(v*p));d0=dn(dn(v/z)-lam);d1=up(up(v/z0)-lam)
        delta=max(0.,up(max(0.,-d0)*up(p-l)),up(max(0.,d1)*up(h-p)));value=up(value+up(up(logi(z,T,True)-dn(lam*p))+delta))
    xx=max(0.,dn(g[i,s]*fromlo));yy=max(0.,dn(g[j,s]*othlo));tx=max(0.,dn(xx/up(1+xx)));ty=max(0.,dn(yy/up(1+yy)));loss=max(0.,dn(dn(r[e,s]*tx)*ty))
    return min(up(value+up(2*logi(up(1-loss),T,True))),up(mix(g,G,i,j,s,r[e,s],fromlo,tolo,othlo,othhi,T)-dn(lam*dn(fromlo+othlo))))
@njit(cache=True)
def bound(pa,ed,g,G,r,lo,hi,prices,T):
    k=len(lo);b=1e99
    for lam in prices:
        v=up(lam*up((k*PT//10)/PT))
        for s in range(len(pa)):v=up(v+perbox(pa[s,0],pa[s,1],s,g,G,r,ed[s],lo,hi,lam,T))
        b=min(b,v)
    return b
@njit(cache=True)
def initial(allp,alled,g,G,r,lo,hi,prices,T):
    E,S=r.shape;hh=np.empty((len(prices),E,S));k=len(lo);e=0
    for i in range(k):
        for j in range(i+1,k):
            for s in range(S):
                for z,lam in enumerate(prices):hh[z,e,s]=perbox(i,j,s,g,G,r,e,lo,hi,lam,T)
            e+=1
    vals=np.empty(len(allp))
    for p in range(len(allp)):
        b=1e99
        for z,lam in enumerate(prices):
            v=up(lam*up((k*PT//10)/PT))
            for s in range(S):v=up(v+hh[z,alled[p,s],s])
            b=min(b,v)
        vals[p]=b
    return vals
def schedules(k):
    ar=np.array([p for p in itertools.permutations(range(k)) if all(p[z]<p[z+1] for z in range(0,k,2))],int).reshape(-1,k//2,2);return ar,edgeid(k,ar[:,:,0],ar[:,:,1])
def single(h,mats,limit=192):
    k=len(h);S=k//2;norm=S*np.log(2);g,G,r,I,J=endpoints(h,0.);nom=nominal(h,I,J);rec,_,_=solve(h);replay(h,rec)
    lo=np.full(k,PT//20);hi=np.full(k,PT//5);upper=np.nextafter(int(rec['U'])/int(rec['den']),np.inf);lb=int(rec['L'])/int(rec['den'])
    P,Ed=mats;pr=np.array([0.,2.,4.,6.,8.,9.,10.,11.,12.,14.,16.,20.]);ub=initial(P,Ed,g,G,r,lo,hi,pr,T)
    for j in np.argsort(ub)[-min(12,len(P)):]:
        pa,p,v=refine(h,P[j],nom);l=lower(h,p,pa,v,np.zeros((S,2,2)),T).sum()/Q;lb=max(lb,l)
    heap=[(-min(upper,z),i,j,lo,hi) for i,(j,z) in enumerate(enumerate(ub)) if min(upper,z)>lb]
    heapq.heapify(heap);idx=len(heap)+len(P);count=0;fixed=-np.inf
    while heap and max(-heap[0][0],fixed)-lb>1e-6*norm and count<limit:
        ng,_,j,a,b=heapq.heappop(heap);axis=np.argmax(b-a);m=(b[axis]+a[axis])//2
        if m<=a[axis]:fixed=max(fixed,-ng);continue
        for direction in [0,1]:
            x=a.copy();y=b.copy()
            if direction:y[axis]=m
            else:x[axis]=m
            if x.sum()>k*PT//10:continue
            y=np.minimum(y,k*PT//10-x.sum()+x);v=min(-ng,bound(P[j],Ed[j],g,G,r,x,y,pr,T))
            if v>lb:
                heapq.heappush(heap,(-v,idx,j,x,y));idx+=1
                pp=(x+y)//2;rem=int(pp.sum()-k*PT//10)
                if rem>0:
                    for a0 in range(k):
                        cut=min(rem,int(pp[a0]-x[a0]));pp[a0]-=cut;rem-=cut
                vv=filt(h,P[j],pp);lb=max(lb,float(lower(h,pp,P[j],vv,np.zeros((S,2,2)),T).sum())/Q)
        count+=1
    U=max(lb,fixed,-heap[0][0] if heap else -np.inf);assert U<=upper and lb<=upper
    return dict(k=k,labelled=len(P),split_boxes=count,lo_nats=lb,hi_nats=U,G_oracle=np.nextafter((U-lb)/norm,np.inf),resolved=int(np.nextafter((U-lb)/norm,np.inf)<=1e-6),candidate_G=rec['G'])
def main():
    guard();mats={k:schedules(k) for k in (2,4,6,8)};dest=root3/'results/oracle';dest.mkdir(exist_ok=True)
    for f in geoms:
        for i in range(128):
            path=dest/f'{f}_{i:03d}.csv'
            if path.exists():continue
            raw=analytic(f,i);rs=[]
            for k in mats:
                # K=6 requires three distinct frequency bins (64 is not divisible by 3).
                s=k//2;scale=np.sqrt(10/(.1*np.median(np.mean(abs(raw.astype(complex))**2,axis=1))));h=np.ascontiguousarray(raw[:k,:,np.floor(np.arange(s)*64/s).astype(int)].astype(complex)*scale)
                rs.append(dict(family=f,block=i,**single(h,mats[k])))
            putcsv(path,rs)
        print('continuous',f,flush=True)
if __name__=='__main__':main()

