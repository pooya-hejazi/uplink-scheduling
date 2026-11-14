"""Hashes bind the actual normalized-channel source bytes. Never include Rice raw samples in the package."""
from pathlib import Path
import csv,hashlib,platform,sys
import numpy as np,scipy,networkx,numba
home=Path(__file__).resolve().parent
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
if __name__=='__main__':
    groups={};seen=set()
    with (home/'results/channel_manifest.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['id','partition','family','draw','source_numpy_shape','file_sha256','channel_sha256','seed','tone_bins','users_or_original_rows','min_xyz','max_xyz'])
        for p in sorted((home/'data').glob('*.npz')):
            part,rest=p.stem.split('_',1);fam,idx=rest.rsplit('_',1)
            if part=='cal':continue # unused early 32-user calibration draw excluded from every score
            with np.load(p) as a:
                h=a['h'];ch=hashlib.sha256(np.ascontiguousarray(h).tobytes()).hexdigest()
                if ch in seen:raise AssertionError('duplicate topology bytes')
                seen.add(ch); groups[part,fam]=groups.get((part,fam),0)+1
                xyz=a['xyz'];w.writerow([p.stem,part,fam,idx,str(h.shape),sha(p),ch,int(a['seed']) if 'seed' in a else '',a['bins'].tolist(),a['perm'].tolist(),xyz.min(axis=0).tolist() if xyz.size else '',xyz.max(axis=0).tolist() if xyz.size else ''])
    print(groups)
    print(sys.version,platform.platform(),'numpy',np.__version__,'scipy',scipy.__version__,'networkx',networkx.__version__,'numba',numba.__version__)

