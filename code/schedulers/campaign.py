"""Frozen pilot benchmark and identical, lock-gated, native Gate 3 co-primary replay."""
import sys,os,datetime,shutil,hashlib,csv,gzip,json,contextlib
from pathlib import Path
from polish import *
import evaluate,solver,audit
from verify import replay,controls
home=Path(__file__).resolve().parent
old=home.parent/'Gate_2'; res=home/'results'
evaluate.out=home;evaluate.res=res
fams=('A','B','C','UMa');grid=(.02,.05,.10,.15);methods=('legacy','det','standalone','hybrid')
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):return hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
def writej(path,d):path.write_text(json.dumps(d,indent=2),encoding='utf-8')
def putcsv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def rows(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def validate():
    assert engine is not None
    controls(); data=[]
    for seed in evaluate.seeds:
        summary=json.loads((res/f'seed_{seed}.json').read_text());assert summary['epochs']==15 and summary['per_epoch']==4096
        with evaluate.worker(seed) as pred:
            for i in range(64):
                for fam in ('analytic','A','B','C'):
                    raw=np.load(old/'data'/f'val_{fam}_{i:04d}.npz')['h'];db=(0,10,20)[(i//3)%3];h,_=normalized(raw,len(raw),db)
                    t0=now();r,_,tim=solve(h,'hybrid',pred);replay(h,r)
                    data.append(dict(seed=seed,family=fam,block=i,k=len(h),db=db,G=r['G'],total_ns=tim['total_ns'],gpu_ms=pred.gpu))
        print('validated',seed,flush=True)
    putcsv(res/'validation.csv',data);score=[]
    for seed in evaluate.seeds:
        d=[v for v in data if v['seed']==seed];assert len(d)==256
        g=np.array([v['G'] for v in d]);score.append(dict(seed=seed,ecdf=float((g[:,None]<=grid).mean()),median_G=float(np.median(g)),median_ms=float(np.median([v['total_ns'] for v in d])/1e6)))
    best=min(score,key=lambda s:(-s['ecdf'],s['median_G'],s['median_ms'],s['seed']))['seed'];shutil.copyfile(res/f'seed_{best}.pt',res/'locked_proposer.pt')
    files=[p for p in sorted(home.glob('*.py'))]+[home/'exact_match.cpp',home/'seeds.csv',home/'data_manifest.csv',home/'protocol.md',home/'native/exact_match.dll',res/'locked_proposer.pt',res/'validation.csv']+[old/(n+'.py') for n in ('solver','witness','enclosures','network','train_gpu','evaluate','audit','generate_native')]
    writej(res/'freeze.json',dict(utc=stamp(),seed=best,scores=score,primary='det',control='legacy',threshold=.15,caps_ms={'32':250,'64':1000},repeats=3,source={str(p.relative_to(home.parent)):sha(p) for p in files}))
    print('FROZEN',best,score,flush=True)
def which(phase):
    assert phase in ('pilot','test')
    cfg=json.loads((res/'freeze.json').read_text())
    for p,hv in cfg['source'].items():assert sha(home.parent/p)==hv,p
    if phase=='test':
        l=json.loads((res/'gate2b_lock.json').read_text());assert l['pass'] and l['replay_complete'] and l['freeze']==sha(res/'freeze.json')
        root=home.parent/'Gate_3';n=128
    else:root=home;n=24
    dest=root/'results';dest.mkdir(exist_ok=True,parents=True);return cfg,root,dest,n
def runone(h,m,pred):
    if m=='legacy':
        r,b,t=solver.solve(h,'subgrad')
        ti=dict(total_ns=t['total_ns'],neural_ns=0,enclosure_ns=t['endpoint_ns']+t['enclosure_ns'],dual_ns=t['matching_ns'],primal_ns=t['primal_ns'],serialize_ns=t['receipt_ns'])
    else:r,b,ti=solve(h,m,pred if m!='det' else None)
    return r,b,ti
def one_row(f,i,k,m,rep,r,t,pred,db=10):
    norm=k//2*np.log(2);div=int(r['den'])*norm
    return dict(family=f,block=i,k=k,db=db,method=m,rep=rep,G=r['G'],Lbit=int(r['L'])/div,Ubit=int(r['U'])/div,dc='' if r['dc_tick'] is None else r['dc_tick']/Q/norm,Sd=r['Sd_tick']/Q/norm,pool_conflict='' if 'A_pool_tick' not in r else (r['R_tick']-r['A_pool_tick'])/Q/norm,witness=r['witness'],proposals=r.get('branch_count',''),gpu_ms=pred.gpu if m in ('standalone','hybrid') else 0,**t)
def bench(phase):
    cfg,root,dest,n=which(phase); assert not (dest/'times.csv').exists(),'use existing complete run or diagnose interrupted run'
    # One shard per independent ordinal supports exact restart without repeating a completed measurement.
    shard=dest/'shards';shard.mkdir(exist_ok=True)
    with evaluate.worker(cfg['seed']) as pred:
        raw=np.load(old/'data/val_A_0000.npz')['h'];h,_=normalized(raw,len(raw),10)
        cold=[]
        for m in methods:
            r,_,t=runone(h,m,pred);cold.append(dict(method=m,total_ms=t['total_ns']/1e6))
        if not (dest/'startup.json').exists():writej(dest/'startup.json',cold)
        for i in range(n):
            path=shard/f'{i:03d}.csv';arc=shard/f'{i:03d}.jsonl.gz'
            if path.exists() and arc.exists():continue
            measurements=[];copies=0
            with gzip.open(arc,'wt',compresslevel=1,encoding='utf-8') as gz:
                for fi,f in enumerate(fams):
                    raw=np.load(root/'data'/f'pilot_{f}_{i:04d}.npz')['h']
                    for k in (32,64):
                        h,_=normalized(raw,k,10);first={}
                        for rep in range(3):
                            rot=(i+fi+rep+(k==64))%4;bnd={}
                            for m in methods[rot:]+methods[:rot]:
                                r,b,t=runone(h,m,pred);bnd[m]=(int(r['U']),int(r['L']));sig=hashlib.sha256(b).hexdigest()
                                # CUDA accumulation can be nondeterministic; archive each distinct receipt, including changed repeats.
                                if sig not in first:
                                    gz.write(json.dumps(dict(id=[f,i,k,10,m,rep],receipt=r),separators=(',',':'))+'\n');first[sig]=True;copies+=1
                                row=one_row(f,i,k,m,rep,r,t,pred);row['receipt_sha']=sig;measurements.append(row)
                            assert bnd['hybrid'][0]<=bnd['det'][0] and bnd['hybrid'][1]>=bnd['det'][1],(f,i,k,rep)
            assert len(measurements)==96;putcsv(path,measurements)
            print(phase,i+1,'/',n,'distinct receipts',copies,flush=True)
    rr=[r for i in range(n) for r in rows(shard/f'{i:03d}.csv')];assert len(rr)==96*n;putcsv(dest/'times.csv',rr)
def final(phase):
    cfg,root,dest,n=which(phase);rr=rows(dest/'times.csv');assert len(rr)==n*96
    indices={};total=0;seen=set()
    for i in range(n):
        cache={}
        with gzip.open(dest/'shards'/f'{i:03d}.jsonl.gz','rt') as f:
            for line in f:
                entry=json.loads(line);fam,idx,k,db,m,rep=entry['id'];r=entry['receipt'];key=(fam,idx,k)
                if key not in cache:cache[key]=normalized(np.load(root/'data'/f'pilot_{fam}_{idx:04d}.npz')['h'],k,db)[0]
                (audit.replay if m=='legacy' else replay)(cache[key],r)
                sig=hashlib.sha256(json.dumps(r,separators=(',',':')).encode()).hexdigest();seen.add((fam,idx,k,m,sig));total+=1
    cases={}
    for r in rr:
        k=int(r['k']);idx=int(r['block']);fam=r['family'];m=r['method'];assert (fam,idx,k,m,r['receipt_sha']) in seen
        cases.setdefault((fam,idx,k,m),[]).append(r)
    assert len(cases)==len(fams)*n*2*len(methods);observed=[]
    for (f,i,k,m),reps in cases.items():
        assert sorted(int(q['rep']) for q in reps)==[0,1,2]
        # If stochastic GPU outputs differ use conservative max gap, paired median latency.
        g=max(float(q['G']) for q in reps);ms=float(np.median([float(q['total_ns']) for q in reps]))/1e6
        observed.append(dict(family=f,block=i,k=k,method=m,G=g,ms=ms,ok=int(g<=.15 and ms<={32:250,64:1000}[k])))
    putcsv(dest/'block_decisions.csv',observed);out=[]
    for k in [32,64]:
        for m in methods:
            for f in ['all','CDL',*fams]:
                o=[x for x in observed if x['k']==k and x['method']==m and (f=='all' or (f=='CDL' and x['family']!='UMa') or x['family']==f)]
                t=np.array([x['ms'] for x in o]);g=np.array([x['G'] for x in o]);cap={32:250,64:1000}[k]
                for cut in grid:out.append(dict(k=k,method=m,family=f,tau=cut,n=len(o),gap=int((g<=cut).sum()),ontime=int((t<=cap).sum()),joint=int(((g<=cut)&(t<=cap)).sum()),median_G=float(np.median(g)),median_ms=float(np.median(t))))
    putcsv(dest/'ecdf.csv',out);hits={k:next(x['joint'] for x in out if x['k']==k and x['method']=='det' and x['family']=='all' and x['tau']==.15) for k in [32,64]}
    rng=np.random.default_rng(19073);boots={};diff={}
    for k in [32,64]:
        a=np.array([[next(x['ok'] for x in observed if x['family']==f and x['block']==i and x['k']==k and x['method']=='det') for i in range(n)] for f in fams])
        b=np.array([[next(x['ok'] for x in observed if x['family']==f and x['block']==i and x['k']==k and x['method']=='hybrid') for i in range(n)] for f in fams]);draw=rng.integers(n,size=(10000,4,n));ix=np.arange(4)[None,:,None]
        boots[k]=float(np.quantile(a[ix,draw].mean((1,2)),.025))
        diff[k]=[float(v) for v in [np.mean(b-a),*np.quantile((b-a)[ix,draw].mean((1,2)),[.025,.975])]]
    passed=hits[32]>=.8*4*n and hits[64]>=.6*4*n and (phase=='pilot' or (boots[32]>.70 and boots[64]>.50))
    result=dict(utc=stamp(),phase=phase,threshold=.15,latency_caps_ms=[250,1000],passages=hits,denominator=4*n,bootstrap_lower=boots,paired_learning_difference_and_ci=diff,hierarchical_learning=bool(passed and diff[32][0]>=.1 and diff[32][1]>0 and diff[64][0]>=0),replay_complete=True,violations=0,verified_distinct=total,timed=len(rr),freeze=sha(res/'freeze.json'),channels=sha(root/'data_manifest.csv'),times=sha(dest/'times.csv'),decisions=sha(dest/'block_decisions.csv'))
    result['pass']=bool(passed);writej(dest/('gate2b_lock.json' if phase=='pilot' else 'native_primary.json'),result);print(json.dumps(result),flush=True)
if __name__=='__main__':
    if sys.argv[1]=='validate':validate()
    elif sys.argv[1]=='bench':bench(sys.argv[2])
    elif sys.argv[1]=='final':final(sys.argv[2])

