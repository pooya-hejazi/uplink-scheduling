"""Independent integer verifier and exact-dyadic primal checker, without any proposer."""
import base64, csv, gzip, hashlib, io, json, math, statistics
from decimal import Decimal as D, localcontext, ROUND_FLOOR, ROUND_CEILING
from collections import Counter, defaultdict
import numpy as np
from prepare import archive, OUT, dump, read_rows, write_rows, zipfile
from enclosures import endpoints,cached_roots,priced,leaves,lower,get_table
Q=2**40; PT=20*2**20; T=get_table()
def dig(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def floating(a,shape):
    assert a[0]=='<c16' and a[1]==list(shape)
    x=np.frombuffer(base64.b64decode(a[2],validate=True),np.complex128).reshape(shape)
    assert np.isfinite(x).all();return x
def exact_dyadics(values):
    vals=np.ascontiguousarray(values,np.complex128)
    fr=[v.as_integer_ratio() for v in vals.view(np.float64).ravel().tolist()]
    den=max(v for _,v in fr)
    return den,np.array([x*(den//d) for x,d in fr],dtype=object).reshape(*vals.shape,2)
def exact_rate(hscaled, hden, pa, power, v, Lticks, U, den):
    # A common dyadic scale for each filter cancels algebraically; only integer dot-products remain.
    _,w=exact_dyadics(v);own=hscaled[pa[:,0],np.arange(len(pa))];other=hscaled[pa[:,1],np.arange(len(pa))]
    highs=[]
    with localcontext() as ctx:
        ctx.prec=55
        for a in range(2):
            vr,vi=w[:,a,:,0],w[:,a,:,1]; nv=(vr*vr+vi*vi).sum(1)
            assert min(nv)>0
            def mag(x):
                hr,hi=x[:,:,0],x[:,:,1]
                return (vr*hr+vi*hi).sum(1)**2+(vr*hi-vi*hr).sum(1)**2
            g,m=mag(own if a==0 else other),mag(other if a==0 else own)
            u,b=pa[:,a],pa[:,1-a];denom=nv*(hden*hden*PT)+m*power[b]
            factor=g*power[u]+denom
            if a==0: numer=factor; div=denom
            else: numer*=factor;div*=denom
        for n,d,l in zip(numer,div,Lticks):
            n,d=D(int(n)),D(int(d));ctx.rounding=ROUND_FLOOR
            lo=(n/d).ln().next_minus()
            assert D(int(l))/Q<=lo or (n==d and int(l)==0),(str(lo),int(l))
            ctx.rounding=ROUND_CEILING
            highs.append((n/d).ln().next_plus())
        actual_hi=sum(highs,D(0));ctx.rounding=ROUND_FLOOR
        assert actual_hi<=D(U)/D(den)
    return actual_hi,tuple(Lticks)
def normalized(raw,k,db):
    v=raw.astype(np.complex128)
    sc=np.sqrt(10**(db/10)/(.1*np.median(np.mean(np.abs(v)**2,axis=1))))
    inds=np.arange(k//2)*(v.shape[2]//(k//2))
    return np.ascontiguousarray(v[:k][:,:,inds]*sc),float(sc)
def paired(v,k):
    a=np.array(v,dtype=np.int64)
    assert a.shape==(k//2,2) and sorted(a.ravel())==list(range(k))
    return a
def rebuild_table(h,rec,geom):
    key=(rec['H_sha'],rec.get('lambda_price',rec.get('lambda')),tuple(rec['leaves']),tuple(rec['anchor_input'][::2]) if 'anchor_input' in rec else None,'lambda' in rec)
    if key in geom['tables']:return geom['tables'][key]
    g,G,r,I,J,box,pen=geom['kernels'];k=len(h);S=k//2; lam=rec.get('lambda_price',rec.get('lambda'))
    assert type(lam)==int and lam>=0
    water=np.clip(1/max(lam,1)-1/np.maximum(G,1e-280),.05,.2)
    if 'anchor_input' in rec:
        dtype,shape,b64=rec['anchor_input'];assert dtype in ('<f4','<f8') and shape==[k,S]
        a=np.frombuffer(base64.b64decode(b64,validate=True),np.dtype(dtype)).reshape(shape)
        assert np.isfinite(a).all() and np.all((a>=.05-1e-8)&(a<=.2+1e-8))
        anchors=[a]
    elif 'lambda' in rec:anchors=[np.full_like(G,.125),water]
    else:anchors=[water]
    sel=np.asarray(rec['leaves'],dtype=np.int64)
    assert len(set(sel))==len(sel) and all(0<=p<r.size for p in sel)
    for a in anchors:
        H=priced(g,G,r,I,J,T,box,pen,lam,a)
        leaves(H,sel,g,G,r,I,J,T,lam)
        assert np.isfinite(H).all() and np.abs(H).max()<400
        table=np.ceil(H*Q).astype('int64')
        if dig(table)==rec['H_sha']:break
    else:raise AssertionError('raw-to-table digest mismatch')
    geom['tables'][key]=table
    return table
def verify(r,h,b):
    k,n,S=h.shape;assert (k,n)==(r['k'],r['n']) and b['raw']==r['raw_sha']
    if 'eps_sha' in r:assert r['eps_sha']==dig(np.zeros((k,S)))
    H=rebuild_table(h,r,b);I,J=b['kernels'][3:5];ei=b['edges'];s=np.arange(S)
    bet=np.asarray(r['beta'],dtype=np.int64);assert len(bet)==S
    w=(H-bet).max(axis=1);witness=r['witness'];lam=r.get('lambda',r.get('lambda_price'))
    assert witness in ('odd-set4','odd-set','P3+diagnostic','P3')
    if 'pairs' in r:
        match=paired(r['pairs'],k); idx=ei[tuple(match.T)]; weights=sum(map(int,w[idx]))
        new='y4' in r; factor=4 if new else 2; zfactor=1 if new else 2
        y=r['y4' if new else 'y2'];z=r['z4' if new else 'z']; assert len(y)==k and all(type(t)==int for t in y)
        assert max(abs(t) for t in y)*2+sum(abs(v)*zfactor for _,v in z)<2**62
        lhs=np.array(y,dtype='int64')[I]+np.array(y,dtype='int64')[J]; obj=sum(y)
        for vertices,value in z:
            assert min(vertices)>=0 and max(vertices)<k and len(vertices)%2==1 and len(set(vertices))==len(vertices)>=3 and type(value)==int and value>=0
            member=np.isin(np.arange(k),vertices); lhs[member[I]&member[J]]+=value*zfactor;obj+=(len(vertices)//2)*value*zfactor
        assert np.all(lhs>=factor*w) and obj==factor*weights
        c=r['cols'];ay=np.array(r['ay']);ab=np.array(r['ab']);assert sorted(c)==list(range(S))
        matched=H[idx];assert np.all(ay[:,None]+ab>=matched)
        A=sum(map(int,matched[s,c]));assert A==sum(map(int,ay))+sum(map(int,ab))
        rb=sum(r['beta'])+weights;dc=rb-A
        assert dc==r['dc_tick'] and dc>=0 and ('A_tick' not in r or A==r['A_tick']); R=rb
    if witness.startswith('P3'):
        alpha=np.array(r['alpha']);base=alpha[I]+alpha[J]
        assert np.all(H<=base[:,None]+bet) and np.array_equal(bet,(H-base[:,None]).max(0))
        R=sum(map(int,alpha))+sum(r['beta'])
    assert ('R_tick' not in r or r['R_tick']==R) and r['Sd_tick']==int(np.ptp(H-bet,axis=1).max())*S
    if r['dc_tick'] is not None:assert 0<=r['dc_tick']<=r['Sd_tick']
    if 'pool_pair' in r:
        p_idx=ei[tuple(paired(r['pool_pair'],k).T)]; assert r['A_pool_tick']==sum(map(int,H[p_idx,s]))<=R
        if r['A_tick'] is not None:assert r['A_pool_tick']>=r['A_tick']
    pair=paired(r['pair'],k);ids=ei[tuple(pair.T)];p=np.asarray(r['power'],np.int64)
    assert len(p)==k and PT//20<=min(p)<=max(p)<=PT//5 and int(p.sum())<=k*PT//10
    v=floating(r['receiver'],(S,2,n));rates=lower(h,p,pair,v,np.zeros((S,2,2)),T).tolist()
    assert rates==r['L_pair'] and ('LF_pair' not in r or r['LF_pair']==rates and r['LP_pair'] is None)
    available=k*PT//10;A0=sum(map(int,w[ids]));Alab=sum(map(int,H[ids,s])); power=sum(map(int,p))
    recomputed=[(R-sum(r['beta'])-A0)*PT,(sum(r['beta'])+A0-Alab)*PT,lam*Q*(available-power),lam*Q*power+(Alab-sum(rates))*PT]
    U=lam*Q*available+R*PT;L=sum(rates)*PT;den=Q*PT
    assert all(t>=0 for t in recomputed) and recomputed==list(map(int,r['terms'])) and sum(recomputed)==U-L
    assert (U,L,den)==tuple(int(r[x]) for x in ('U','L','den'))
    key=(tuple(pair.flat),tuple(p),r['receiver'][2])
    if key not in b['rate_cache']:b['rate_cache'][key]=exact_rate(b['hscaled'],b['hden'],pair,p,v,rates,U,den)
    rate,checked_pair_rates=b['rate_cache'][key]
    assert tuple(rates)==checked_pair_rates
    # Each distinct upper must bound the same action's independently outward-bounded true rate.
    with localcontext() as ctx:
        ctx.prec=70;ctx.rounding=ROUND_CEILING
        lnlo=D(2).ln().next_minus(); lnhi=D(2).ln().next_plus()
        ctx.rounding=ROUND_FLOOR
        glo_den=D(S)*lnlo
        assert rate<=D(U)/D(den)
        ctx.rounding=ROUND_CEILING
        ghi_den=D(S)*lnhi
        g_hi=(D(U-L)/D(den))/glo_den
        ctx.rounding=ROUND_FLOOR
        g_lo=(D(U-L)/D(den))/ghi_den
        assert D.from_float(r['G'])>=g_hi and (g_hi<=D('.15'))==(g_lo<=D('.15'))==(r['G']<=.15)
        return dict(U=U,L=L,den=den,G=r['G'],pass_gap=int(g_hi<=D('.15')),witness=witness,exact_gap=str(g_hi),upward_pad=float(D.from_float(r['G'])-g_lo),independent_rate_nats=rate)
def run():
    with zipfile.ZipFile(archive('Gate_3')) as z:
        prefix='Gate_3/';base=prefix+'results/';man={(q['family'],int(q['block'])):q for q in read_rows(z.read(prefix+'data_manifest.csv'))}
        timings=read_rows(z.read(base+'times.csv')); assert len(timings)==12288
        bysig={}; ids=set(); cases=defaultdict(list); out=[]; tested=Counter(); exact_actions=0
        for shard in range(128):
            cache={}; shrows=read_rows(z.read(base+f'shards/{shard:03}.csv'))
            assert shrows==timings[shard*96:(shard+1)*96]
            for line in gzip.decompress(z.read(base+f'shards/{shard:03}.jsonl.gz')).splitlines():
                a=json.loads(line);f,i,k,db,m,rep=a['id'];r=a['receipt'];assert i==shard and db==10 and r.get('mode',r.get('method'))==({'legacy':'subgrad'}.get(m,m))
                sig=hashlib.sha256(json.dumps(r,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
                assert sig not in bysig and (f,i,k,db,m,rep) not in ids;ids.add((f,i,k,db,m,rep))
                key=f,k
                if key not in cache:
                    data=z.read(prefix+f'data/pilot_{f}_{i:04d}.npz');ref=man[f,i];assert hashlib.sha256(data).hexdigest()==ref['file_sha256']
                    with np.load(io.BytesIO(data),allow_pickle=False) as a0:raw=a0['h']
                    assert dig(raw)==ref['channel_sha256'];h,_=normalized(raw,k,db)
                    g,G,rho,I,J=endpoints(h,0.);init,pen=cached_roots(g,G,rho,I,J,T);edge=np.zeros((k,k),int);edge[I,J]=edge[J,I]=np.arange(len(I))
                    hden,hscaled=exact_dyadics(h.transpose(0,2,1));cache[key]=(h,dict(raw=dig(h),tables={},kernels=(g,G,rho,I,J,init,pen),edges=edge,hden=hden,hscaled=hscaled,rate_cache={}))
                h,b=cache[key];v=verify(r,h,b)
                bysig[sig]=(f,i,k,db,m,rep,v);tested[v['witness']]+=1
                out.append(dict(receipt_sha256=sig,family=f,block=i,k=k,db=db,method=m,first_rep=rep,raw_sha256=r['raw_sha'],H_sha256=r['H_sha'],**v))
            exact_actions+=sum(len(b['rate_cache']) for h,b in cache.values())
            if shard%8==7:print('Checked raw shards',shard+1,'/',128,'distinct',len(out),flush=True)
        allowed=set()
        for t in timings:
            f,i,k,db,m,rep=t['family'],int(t['block']),int(t['k']),int(t['db']),t['method'],int(t['rep'])
            sig=t['receipt_sha'];first=bysig[sig];v=first[-1]
            assert (f,i,k,db,m)==first[:5] and rep>=first[5] and float(t['G'])==v['G'] and v['witness']==t['witness']
            assert all(int(t[q])>=0 for q in ('total_ns','neural_ns','enclosure_ns','dual_ns','primal_ns','serialize_ns')) and int(t['total_ns'])>0
            factor=v['den']*(k//2)*math.log(2)
            for q,tv in [('L','Lbit'),('U','Ubit')]:assert math.isclose(v[q]/factor,float(t[tv]),rel_tol=4e-16)
            cases[f,i,k,m].append((rep,sig,v,int(t['total_ns'])));allowed.add(sig)
        assert len(ids)==len(allowed)==len(bysig)==8192 and len(cases)==4096
        output=[]; nondegrade=0
        for (f,i,k,m),rows in sorted(cases.items()):
            rows.sort();assert [r[0] for r in rows]==[0,1,2]
            g=max(x[2]['G'] for x in rows);ms=statistics.median(x[3] for x in rows)/1e6
            ok=int(all(x[2]['pass_gap'] for x in rows) and ms<={32:250,64:1000}[k])
            output.append(dict(family=f,block=i,k=k,method=m,G=g,ms=ms,ok=ok))
            if m=='hybrid':
                det=sorted(cases[f,i,k,'det'])
                for a,b0 in zip(rows,det):
                    assert a[2]['U']<=b0[2]['U'] and a[2]['L']>=b0[2]['L'];nondegrade+=1
        official={(q['family'],int(q['block']),int(q['k']),q['method']):(float(q['G']),float(q['ms']),int(q['ok'])) for q in read_rows(z.read(base+'block_decisions.csv'))}
        assert len(official)==len(output) and all(official[r['family'],r['block'],r['k'],r['method']]==(r['G'],r['ms'],r['ok']) for r in output)
        write_rows('receipt_checks.csv',out);write_rows('rebuilt_block_decisions.csv',output)
        dump('receipt_summary.json',dict(distinct=len(out),timing_links=len(timings),raw_topologies=len(man),method_size_decisions=len(output),raw_independent_primal_actions=exact_actions,four_term_nonnegative_identities=len(out),witnesses=dict(tested),hybrid_nondegradation_pairs=nondegrade,smallest_threshold_distance=min(abs(float(x['exact_gap'])-.15) for x in out),largest_upward_display_pad=max(x['upward_pad'] for x in out),violations=0))
if __name__=='__main__':run()
