"""Independent exact-decimal threshold reconstruction and forced native P3 fallback."""
from grid import *
from decimal import Decimal as D,localcontext
from unittest.mock import patch
import polish
def check_fallback():
    rng=np.random.default_rng(111999);k=8;h=np.ascontiguousarray(rng.normal(size=(k,4,4))+1j*rng.normal(size=(k,4,4)))
    expected=polish.match
    def test(k,I,J,w):
        # The first matching uses 2^27 heuristic scores; the seven dual certificates use the 2^40 tick table.
        if np.max(np.abs(w))>2**33:raise ArithmeticError('injected dual failure')
        return expected(k,I,J,w)
    with patch.object(polish,'match',test):r,_,_=solve(h)
    assert r['witness']=='P3' and len(r['proposals'])==7;replay(h,r)
    u=dict(r);u['terms']=list(u['terms']);u['terms'][0]=str(int(u['terms'][0])+1)
    try:replay(h,u)
    except AssertionError:pass
    else:raise AssertionError('replay accepted corrupt ledger')
    return True
def run(phase):
    cfg,base,dest,n=which(phase);positive=check_fallback();mismatch=0;count=0;maxpad=0.;mind=np.inf
    with localcontext() as ctx:
        ctx.prec=76;ln=D(2).ln()
        for i in range(n):
            with gzip.open(dest/'shards'/f'{i:03d}.jsonl.gz','rt') as f:
                for line in f:
                    a=json.loads(line);r=a['receipt'];k=r['k'];val=D(int(r['U'])-int(r['L']))/(D(int(r['den']))*D(k//2)*ln);gv=D.from_float(r['G'])
                    assert val>=0 and gv>=val,(a['id'],str(val),str(gv))
                    maxpad=max(maxpad,float(gv-val));mind=min(mind,abs(float(val)-.15));count+=1;mismatch+=int((val<=D('0.15'))!=(gv<=D('0.15')))
    assert mismatch==0
    writej(dest/'independent_gap_audit.json',dict(distinct=count,invalid=0,threshold_mismatches=mismatch,smallest_distance_from_point15=mind,max_upward_pad=maxpad,forced_P3=positive,mutated_ledger_rejected=True))
if __name__=='__main__':run(sys.argv[1])

