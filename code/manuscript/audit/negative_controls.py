"""Challenge the auditor's independent rejection checks using a sealed real witness."""
import copy,gzip,hashlib,io,json
import numpy as np
from prepare import archive,dump,zipfile
from receipts import verify,normalized,exact_dyadics,dig,T,endpoints,cached_roots
def main():
    with zipfile.ZipFile(archive('Gate_3')) as z:
        rr=[json.loads(r) for r in gzip.decompress(z.read('Gate_3/results/shards/000.jsonl.gz')).splitlines()]
        entry=next(e for e in rr if e['receipt'].get('z4'));f,i,k,db,_,_=entry['id'];r=entry['receipt']
        with np.load(io.BytesIO(z.read(f'Gate_3/data/pilot_{f}_{i:04d}.npz')),allow_pickle=False) as a:raw=a['h']
    h,_=normalized(raw,k,db);g,G,rho,I,J=endpoints(h,0.);root,pen=cached_roots(g,G,rho,I,J,T);ei=np.zeros((k,k),int);ei[I,J]=ei[J,I]=np.arange(len(I));den,hh=exact_dyadics(h.transpose(0,2,1))
    b=dict(raw=dig(h),tables={},kernels=(g,G,rho,I,J,root,pen),edges=ei,hden=den,hscaled=hh,rate_cache={});verify(r,h,b)
    def balance(t):t['terms'][0]=str(int(t['terms'][0])+1);t['terms'][1]=str(int(t['terms'][1])-1)
    variants={'sum-preserving transfer between two ledger terms':balance,'altered covered table digest':lambda t:t.update(H_sha='0'*64),'invalid odd set':lambda t:t['z4'][0][0].append(t['z4'][0][0][0]),'duplicated primal user':lambda t:t['pair'][0].__setitem__(0,t['pair'][0][1]),'negative lower-rate tick':lambda t:t['L_pair'].__setitem__(0,-1),'mismatched denominator':lambda t:t.update(den=str(int(t['den'])-1)),'non-upward displayed gap':lambda t:t.update(G=0.)}
    for name,mut in variants.items():
        r1=copy.deepcopy(r);mut(r1)
        try:verify(r1,h,b)
        except (AssertionError,ValueError):pass
        else:raise AssertionError(f'missed corruption: {name}')
    dump('negative_controls.json',dict(positive_control_id=entry['id'],rejected=list(variants),unexpected_acceptances=0))
if __name__=='__main__':main()
