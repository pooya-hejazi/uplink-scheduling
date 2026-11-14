"""Package scientific inputs, witnesses, scripts and results. Never archive restricted Rice input or credentials."""
from pathlib import Path
import hashlib,json,zipfile,sys,os
root=Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as fp:return hashlib.file_digest(fp,'sha256').hexdigest()
def main(stage):
    d=root/stage;report=root/'output/pdf'/(stage+'_Report.pdf');assert report.exists()
    paths={report}
    for p in d.rglob('*'):
        if not p.is_file() or any(v.startswith('.') or v in ('__pycache__','rice_private','calibration_sensitivity') for v in p.relative_to(d).parts):continue
        if p.name=='SHA256SUMS' or p.suffix in ('.pdb','.lib','.pyc','.nbi','.nbc','.h5','.hdf5','.pkl') or p.name.endswith('.tmp'):continue
        if p.suffix=='.log' and p.stat().st_size>2_000_000:continue
        paths.add(p)
    if stage=='Gate_2B':
        paths.update(root/'Gate_2'/s for s in ['solver.py','enclosures.py','witness.py','evaluate.py','audit.py','train_gpu.py','generate_native.py','network.py','bench.py','teachers.py','generate_ray.py','imperfect.py'])
        paths.update(root/'Gate_1'/s for s in ['verifier64.py','verify_gate1.py','gaussian_bounds.py'])
        paths.update((root/'Gate_2/results'/f) for f in ['selection.json','thresholds.json'])
        paths.update(root/'Gate_3'/n for n in ['diagnostics.py','extra_audit.py','grid.py','structure.py','inputs.py'])
    if stage=='Gate_3':
        paths.add(root/'Research_Execution_Roadmap.md')
        paths.add(root/'Gate_2B/reporting.py');paths.add(root/'Gate_2B/package.py')
        for p in (root/'Gate_2/results').glob('rice_*'):
            if p.suffix in ('.csv','.json'):paths.add(p)
        paths.update(root/'Gate_2'/s for s in ['rice_io.py','rice_signal.py','rice_decode.py','RICE_RESULTS.md'])
        paths.update([root/'Gate_2B/results/gate2b_lock.json',root/'Gate_2B/results/freeze.json',root/'Gate_2B/protocol.md',root/'Gate_2B/results/locked_proposer.pt',root/'Gate_2/results/calibration_scores.csv'])
        # Release the exact fixed external MLP parameters as numeric arrays; Python pickle never needs to be executed by a reviewer.
        model=d/'results/pair_mlp.pkl'
        if model.exists():
            import pickle,numpy as np
            assert sha(model)==(d/'results/pair_mlp_sha.txt').read_text();m=pickle.loads(model.read_bytes());p=d/'results/pair_mlp_parameters.npz';np.savez(p,W0=m.coefs_[0],W1=m.coefs_[1],b0=m.intercepts_[0],b1=m.intercepts_[1]);paths.add(p)
    index=d/'SHA256SUMS';files=sorted(paths);index.write_text(''.join(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in files),encoding='utf8');files.append(index)
    out=root/'output'/(stage+'_Deliverable_Package.zip');temp=out.with_suffix('.tmp');assert temp.parent==root/'output'
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as archive:
        for p in files:archive.write(p,p.relative_to(root).as_posix(),compress_type=zipfile.ZIP_STORED if p.suffix in ('.gz','.png','.pdf','.pt') else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(temp) as arc:
        assert arc.testzip() is None and len(arc.namelist())==len(set(arc.namelist()))==len(files)
        for path in arc.namelist():assert '.hdf5' not in path and '/rice_private/' not in path
    temp.replace(out);out.with_suffix('.sha256').write_text(sha(out)+'  '+out.name+'\n');print(out,len(files),out.stat().st_size,sha(out))
if __name__=='__main__':main(sys.argv[1])

