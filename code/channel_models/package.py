"""Package only redistributable code, generated simulations and evidence; no Rice IQ or decoded channel arrays."""
import hashlib,json,zipfile
from pathlib import Path
home=Path(__file__).resolve().parent;root=home.parent
def hashfile(p):
    with p.open('rb') as fp:return hashlib.file_digest(fp,'sha256').hexdigest()
def package():
    assert (home/'results/rice_replay_HUB.json').exists() and (home/'results/rice_replay_LO.json').exists(), 'wait for both full hardware replays'
    assert 'Full-capture outcome pending' not in (home/'REPORT.md').read_text(encoding='utf8')
    selected=set(home.glob('*.py'))|set(home.glob('*.md'))|{home/'rice_index.png'}
    logs=['audit_controls','audit_deterministic','audit_neural','bench','train','evaluate','imperfect','generation','cal_generation','manifest','teachers','rice_inventory','rice_probe','decode_HUB','LO_memory_replay','summary']
    selected|={home/(n+'.log') for n in logs if (home/(n+'.log')).exists()}
    selected|={home/'teachers/manifest.csv'}
    selected|=set((home/'data').glob('pilot_*.npz'))|set((home/'data').glob('*_source.json'))
    selected|={p for p in (home/'results').iterdir() if p.is_file() and p.suffix in {'.gz','.csv','.done','.pt','.json','.svg','.png'} and not p.name.startswith('rice_meta_')}
    # Original HDF5 attributes contain device identifiers; only the verified inventory, hashes and aggregate scores are shared.
    selected|={root/'Research_Execution_Roadmap.md',root/'output/pdf/Research_Execution_Roadmap.pdf',root/'output/pdf/Gate_2_Report.pdf',root/'Gate_1/verifier64.py',root/'Gate_1/Proofs.md',root/'Gate_1/SHA256SUMS'}
    original=root/'output/Gate_1_Deliverable_Package.zip'
    with zipfile.ZipFile(original) as gz:
        for line in gz.read('Gate_1/SHA256SUMS').decode().splitlines():
            sha,file=line.split('  ',1);assert hashlib.sha256(gz.read(file)).hexdigest()==sha
    selected.add(original)
    # The activity probes hold aggregate powers and range hashes; no raw samples. Never include private staging.
    assert all('rice_private' not in p.parts and p.suffix!='.hdf5' for p in selected)
    for p in selected:
        if not p.is_file():raise FileNotFoundError(p)
    sums=home/'SHA256SUMS';sums.write_text(''.join(hashfile(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in sorted(selected)),encoding='utf8');selected.add(sums)
    target=root/'output/Gate_2_Deliverable_Package.zip';stage=target.with_suffix('.tmp.zip')
    with zipfile.ZipFile(stage,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(selected):z.write(p,p.relative_to(root))
    with zipfile.ZipFile(stage) as z:
        assert z.testzip() is None
        for line in z.read('Gate_2/SHA256SUMS').decode().splitlines():
            sha,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==sha
    stage.replace(target);print(len(selected),'files',target.stat().st_size,'bytes',hashfile(target))
if __name__=='__main__':package()

