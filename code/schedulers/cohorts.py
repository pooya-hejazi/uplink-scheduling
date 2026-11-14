from pathlib import Path
from hashlib import sha256
import csv,json,sys
HOME=Path(__file__).resolve().parent
OLD=HOME.parent/'Gate_2'
FAMS=('A','B','C','UMa')
def key(part,f,i):return int.from_bytes(sha256(f'{part}|{f}|{i}'.encode()).digest()[:4],'little')
def ids():
    seen=set()
    for part,fams,n in [('fit',('analytic','A','B','C'),1024),('val',('analytic','A','B','C'),64),('cal',('C','UMa'),256),('cal64',('C','UMa'),256),('pilot',FAMS,24)]:
        for f in fams:
            for i in range(n):seen.add(key('gate2-v1|'+part,f,i))
    rows=[]
    for split,domain,n in [('pilot','CF-native-v2B-20261113',24),('test','CF-native-v3-20261113',128)]:
        for f in FAMS:
            for i in range(n):
                s=key(domain,f,i);assert s not in seen;seen.add(s)
                rows.append(dict(split=split,family=f,block=i,seed=s))
    return rows
def freeze():
    rows=ids();path=HOME/'seeds.csv'
    content='split,family,block,seed\n'+''.join(f"{r['split']},{r['family']},{r['block']},{r['seed']}\n" for r in rows)
    if path.exists():assert path.read_bytes()==content.encode()
    else:path.write_bytes(content.encode())
    print(len(rows),'unique disjoint reserved IDs',sha256(path.read_bytes()).hexdigest())
def generate(split):
    import importlib,os
    if split=='test':
        decision=json.loads((HOME/'results/gate2b_lock.json').read_text());assert decision['pass'] and decision['replay_complete']
    sys.path.insert(0,str(OLD));g=importlib.import_module('generate_native')
    dest=HOME/('data' if split=='pilot' else '../Gate_3/data');dest.mkdir(exist_ok=True,parents=True)
    table={(r['family'],r['block']):r['seed'] for r in ids() if r['split']==split}
    g.out=dest;g.seed_for=lambda _,f,i:table[f,i]
    for f in FAMS:g.make('pilot',f,24 if split=='pilot' else 128)
    import numpy as np
    old={r['channel_sha256'] for r in csv.DictReader((OLD/'results/channel_manifest.csv').open())}
    if split=='test':old.update(r['channel_sha256'] for r in csv.DictReader((HOME/'data_manifest.csv').open()))
    with (dest.parent/'data_manifest.csv').open('w',newline='') as fp:
        w=csv.writer(fp);w.writerow(['split','family','block','seed','channel_sha256','file_sha256'])
        for (f,i),seed in table.items():
            p=dest/f'pilot_{f}_{i:04d}.npz'
            with np.load(p) as a:h=a['h'];assert int(a['seed'])==seed and h.shape==(64,16,64)
            hv=sha256(np.ascontiguousarray(h).tobytes()).hexdigest();assert hv not in old;old.add(hv)
            w.writerow([split,f,i,seed,hv,sha256(p.read_bytes()).hexdigest()])
if __name__=='__main__':
    freeze()
    if len(sys.argv)>1:generate(sys.argv[1])

