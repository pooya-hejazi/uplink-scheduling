"""Run one receipt at a time; timed window excludes corpus I/O, includes raw-envelope build through JSON bytes."""
import csv,gzip,sys,datetime,time
from solver import *
out=Path(__file__).resolve().parent; res=out/'results';res.mkdir(exist_ok=True)
fields=['family','block','k','db','rep','method','scale','G','dc','Sd','Lbit','Ubit','fallback','zero_ok','endpoint_ns','proposer_ns','enclosure_ns','matching_ns','primal_ns','receipt_ns','total_ns']
families=['A','B','C','UMa','O1_60','asu_campus1']
def datestr():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def writeall():
    tag='deterministic'; path=res/(tag+'.csv')
    done=set()
    if path.exists():
        with path.open() as f:done={(r['family'],int(r['block']),int(r['k']),int(r['db']),int(r['rep']),r['method']) for r in csv.DictReader(f)}
    if len(done)==12960 and (res/'deterministic.done').is_file():
        print('complete benchmark already recorded; retaining original timestamps');return
    h0=normalized(np.load(out/'data/pilot_A_0000.npz')['h'],16,10)[0]
    t=now();solve(h0,'subgrad'); print('process warmup ns',now()-t,flush=True)
    with path.open('a',newline='') as f,gzip.open(res/'det_receipts.jsonl.gz','at',encoding='utf-8',compresslevel=2) as receipts:
        w=csv.DictWriter(f,fields)
        if not done:w.writeheader()
        for block in range(24):
            for fam in families:
                if fam in families[4:] and block>=12: continue
                raw=np.load(out/'data'/f'pilot_{fam}_{block:04d}.npz')['h']
                for db in [10,0,20]:
                    for k in [32,64,16]:
                        h,scale=normalized(raw,k,db)
                        for rep in range(3):
                            off=(rep+block+k//16+db//10+families.index(fam))%4
                            for m in METHODS[off:]+METHODS[:off]:
                                key=(fam,block,k,db,rep,m)
                                if key in done:continue
                                r,p,z=solve(h,m)
                                S=k//2; norm=S*np.log(2)
                                # Independent deployed-rate calculation; separate from receipt latency.
                                a=np.array(r['pair']);pw=np.array(r['power'])/PT;s=np.arange(S)
                                vv=np.frombuffer(base64.b64decode(r['receiver'][2]),dtype='<c16').reshape(S,2,-1)
                                true=0.
                                for j in [0,1]:
                                    u,o=a[:,j],a[:,1-j];v=vv[:,j]
                                    true+=np.log1p(pw[u]*abs((v.conj()*h[u,:,s]).sum(1))**2/((abs(v)**2).sum(1)+pw[o]*abs((v.conj()*h[o,:,s]).sum(1))**2)).sum()
                                lb=int(r['L'])/int(r['den']); ub=int(r['U'])/int(r['den'])
                                ok=bool(lb<=true+1e-10 and true<=ub+1e-10)
                                if not ok:raise ArithmeticError(('independent deployed reference outside receipt',key,lb,true,ub))
                                row=dict(zip(fields[:6],key));row.update(scale=scale,G=r['G'],dc='' if r['dc_tick'] is None else r['dc_tick']/Q/norm,Sd=r['Sd_tick']/Q/norm,Lbit=lb/norm,Ubit=ub/norm,fallback=r['fallback'],zero_ok=int(ok),**z);w.writerow(row)
                                if rep==0: receipts.write(json.dumps({'id':[fam,block,db], 'receipt':r},separators=(',',':'))+'\n')
                        f.flush()
                print(fam,block,datestr(),flush=True)
    (res/'deterministic.done').write_text(datestr())
if __name__=='__main__':writeall()

