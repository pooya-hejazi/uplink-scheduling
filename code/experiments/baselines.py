"""Paired classical controls on the native and ray grids, P3 and small-K DP comparators."""
from grid import *
def run(group):
    guard();solver.blossom=match;audit.check=check4
    # Gate 2's policy arithmetic is unchanged; these separate control runs use the same faster native witness as the candidate.
    # Its two dual slots here carry quarter ticks. The untouched archived legacy benchmark uses its original half-tick format.
    where=root3/'results'/('controls_'+group);where.mkdir(exist_ok=True)
    fs=fams if group=='native' else ('O1_60','asu_campus1') if group=='ray' else geoms
    for f in fs:
        n=(len(json.loads((root3/f'{f}_tiles.json').read_text())) if group=='ray' else 128)
        for i in range(n):
            file=where/f'{f}_{i:03d}.csv'
            if file.exists():continue
            raw=source(f,i);rr=[]
            for k in (16,32,64):
                for db in [-5,0,10,20]:
                    h,sc=normalized(raw,k,db)
                    for m in ('sequential','equal_match','cold'):
                        r,b,t=solver.solve(h,m);audit.replay(h,r);den=int(r['den'])*(k//2)*np.log(2)
                        rr.append(dict(family=f,block=i,k=k,db=db,method=m,G=r['G'],L=int(r['L'])/den,U=int(r['U'])/den,ms=t['total_ns']/1e6,witness=r['witness'],hash=hashlib.sha256(b).hexdigest()))
            putcsv(file,rr)
        print('all classical controls',f,flush=True)
if __name__=='__main__':run(sys.argv[1])

