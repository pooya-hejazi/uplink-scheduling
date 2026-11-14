"""Single entry point for the reviewer repository; run from the code directory."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys,zipfile

CODE=Path(__file__).resolve().parent
ROOT=CODE.parent
WORK=ROOT/'.work'
INPUTS=ROOT/'data/inputs'
LAYERS={'mathematics':'Gate_1','channel_models':'Gate_2','schedulers':'Gate_2B','experiments':'Gate_3','manuscript':'Gate_4'}

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def verify_inputs():
    records=json.loads((ROOT/'data/inputs.json').read_text())
    for row in records:
        path=INPUTS/row['name']
        if not path.exists():raise FileNotFoundError(f'Download the private release asset to {path}; see README.md.')
        if digest(path)!=row['sha256']:raise ValueError('Input SHA-256 mismatch: '+row['name'])
    print('Verified all five input archives.',flush=True)
    return records

def prepare():
    records=verify_inputs()
    marker=WORK/'.prepared'
    if WORK.exists() and not marker.exists():
        raise RuntimeError('Incomplete .work directory: move it to a backup location before preparing again.')
    if not marker.exists():
        WORK.mkdir()
        for row in records:
            with zipfile.ZipFile(INPUTS/row['name']) as archive:
                for member in archive.infolist():
                    path=(WORK/member.filename).resolve()
                    if not path.is_relative_to(WORK.resolve()) or path.suffix.lower() in {'.h5','.hdf5','.iq'}:
                        raise ValueError('Unexpected archive member: '+member.filename)
                archive.extractall(WORK)
        (WORK/'output').mkdir(exist_ok=True)
        for row,layer in zip(records[:4],list(LAYERS.values())[:4]):
            dest=WORK/'output'/(layer+'_Deliverable_Package.zip')
            try:os.link(INPUTS/row['name'],dest)
            except OSError:shutil.copy2(INPUTS/row['name'],dest)
            dest.with_suffix('.sha256').write_text(row['sha256']+'  '+dest.name+'\n')
        for folder,layer in LAYERS.items():
            shutil.copytree(CODE/folder,WORK/layer,dirs_exist_ok=True)
        # Only local launch paths change; frozen archive bytes and algorithms stay intact.
        for path in WORK.glob('Gate_*/*.py'):
            original=path.read_text(encoding='utf-8')
            text=original.replace("GPU_PY='C:/ProgramData/anaconda3/envs/mmocr/python.exe'", "GPU_PY=__import__('os').environ.get('GATE_GPU_PY',sys.executable)")
            if path.name=='generate_ray.py':
                text=text.replace("base=Path('D:/PostDocProposal/PostDocPaper2')", "base=Path(__import__('os').environ.get('DEEPMIMO_ROOT','.'))")
                text=text.replace("base/'audit/frozen/S04-PREFLIGHT-A01/environment'", "Path(__import__('os').environ.get('DEEPMIMO_PYTHON_PATH','.'))")
                text=text.replace("base/'DeepMIMO_sena/O1_60'", "base/'O1_60'").replace("base/'research/reviewer-resolution-20261101/downloads/scene/asu_campus1'", "base/'asu_campus1'")
            if text!=original:path.write_text(text,encoding='utf-8')
        marker.write_text('Prepared from SHA-256-verified immutable inputs.\n')
    print('Research execution workspace ready.',flush=True)

def run(script,args=(),cwd=None):
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    subprocess.run([sys.executable,'-X','utf8',str(script),*map(str,args)],cwd=cwd or ROOT,env=env,check=True)

def main():
    tasks=['verify-math','verify-records','verify-inputs','prepare','figures','supplementary-figures','reviewer-rates','reviewer-decomposition','reviewer-refinement','reviewer-compute','hardware-decode','hardware-evaluate','round2-summary','round2-time-pilot','round2-time-control','round2-refinement','round2-small-reference','round2-hardware','build-paper','build-supplement','build-response','build-diffs','build-native','verify-scheduler','generate-training','train','confirmatory-test','summarize']
    tasks.extend(['round2-check', 'round3-hardware', 'round3-bounds'])
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task',choices=tasks)
    parser.add_argument('--mode',choices=['HUB','LO'])
    parser.add_argument('--tectonic')
    parser.add_argument('--perl',default='perl')
    parser.add_argument('--latexdiff')
    parser.add_argument('--only-cached',action='store_true')
    a=parser.parse_args()
    manuscript=CODE/'manuscript'
    if a.task=='verify-math':run(CODE/'mathematics/verify_gate1.py');return
    if a.task=='verify-records':run(manuscript/'audit/issue.py',['verify']);return
    if a.task=='verify-inputs':verify_inputs();return
    if a.task=='round2-summary':
        run(manuscript/'revision/round2_tables.py')
        return
    if a.task=='figures':
        run(manuscript/'make_figures.py')
        shutil.copytree(manuscript/'figures',ROOT/'results/figures',dirs_exist_ok=True)
        return
    if a.task in ('build-paper','build-supplement'):
        tool='build_paper.py' if a.task=='build-paper' else 'build_supplementary.py'
        arguments=['--source',manuscript]
        if a.tectonic:arguments+=['--tectonic',a.tectonic]
        if a.only_cached:arguments+=['--only-cached']
        run(CODE/'document_tools'/tool,arguments);return
    if a.task in ('build-response','build-diffs'):
        arguments=['--submission',ROOT]
        if a.tectonic:arguments+=['--tectonic',a.tectonic]
        if a.only_cached:arguments+=['--only-cached']
        if a.task=='build-diffs':
            if not a.tectonic or not a.latexdiff:parser.error('build-diffs requires --tectonic and --latexdiff')
            arguments+=['--perl',a.perl,'--latexdiff',a.latexdiff]
        run(CODE/'document_tools'/('build_response.py' if a.task=='build-response' else 'build_diffs.py'),arguments);return
    if (a.task.startswith('hardware-') or a.task in ('round2-hardware','round3-hardware')) and a.mode is None:parser.error('Hardware tasks require --mode HUB or --mode LO')
    prepare()
    if a.task=='prepare':return
    if a.task.startswith('round3-'):
        run(WORK/'Gate_4/revision/round3_diagnostics.py',[a.mode if a.task=='round3-hardware' else 'bounds'],WORK)
        run(WORK/'Gate_4/revision/round2_tables.py',cwd=WORK)
        dest=ROOT/'results/round3';dest.mkdir(parents=True,exist_ok=True)
        for path in (WORK/'Gate_4/revision/round3_data').glob('*'):
            if path.suffix in {'.csv','.json'}:shutil.copy2(path,dest/path.name)
        print('Third-round scalar diagnostics:',dest)
        return
    if a.task=='round2-check':run(WORK/'Gate_4/revision/round2_oracle.py',cwd=WORK);return
    research={'build-native':('Gate_2B/build_native.py',[]),'verify-scheduler':('Gate_2B/verify.py',[]),'generate-training':('Gate_2/generate_native.py',['fit','val','cal64']),'train':('Gate_2B/learn.py',['train']),'confirmatory-test':('Gate_2B/campaign.py',['final','test'])}
    if a.task in research:
        script,arguments=research[a.task];run(WORK/script,arguments,WORK);return
    if a.task=='summarize':
        for script in ['analyze.py','supplement.py']:run(WORK/'Gate_3'/script,cwd=WORK)
        return
    if a.task.startswith('round2-'):
        calls={'round2-time-pilot':('round2_compute.py',['tune']),
               'round2-time-control':('round2_compute.py',['run']),
               'round2-refinement':('round2_refinement.py',['refinement']),
               'round2-small-reference':('round2_refinement.py',['small','--limit','32768']),
               'round2-hardware':('round2_hardware.py',[a.mode])}
        script,arguments=calls[a.task]
        run(WORK/'Gate_4/revision'/script,arguments,WORK)
        run(WORK/'Gate_4/revision/round2_tables.py',cwd=WORK)
    elif a.task.startswith('reviewer-'):
        task=a.task.split('-',1)[1];task='sweep' if task=='refinement' else task
        run(WORK/'Gate_4/revision/reviewer_analysis.py',[task],WORK)
        run(WORK/'Gate_4/revision/reviewer_tables.py',cwd=WORK)
        run(WORK/'Gate_4/revision/round2_tables.py',cwd=WORK)
    elif a.task.startswith('hardware-'):
        run(WORK/'Gate_4/revision/reviewer_hardware.py',[a.task.split('-',1)[1],a.mode],WORK)
    elif a.task=='supplementary-figures':
        run(WORK/'Gate_4/supplementary/make_simulation_supp.py',cwd=WORK)
        run(WORK/'Gate_4/supplementary/make_physics_supp.py',cwd=WORK)
        # Argos plotting uses shipped scalar summaries; raw-source verification is a separate task.
        subprocess.run([sys.executable,'-c',"import sys;sys.path.insert(0,sys.argv[1]);import make_hardware_supp as m;m.renew();m.plot_argos(m.read(m.DATA/'hardware_argos_frames.csv'))",str(WORK/'Gate_4/supplementary')],cwd=WORK,check=True)
    result=ROOT/'results';result.mkdir(exist_ok=True)
    if a.task=='supplementary-figures':
        shutil.copytree(WORK/'Gate_4/supplementary/figures',result/'supplementary_figures',dirs_exist_ok=True)
    else:
        for path in (WORK/'Gate_4/revision/reviewer_data').glob('*'):
            if path.is_file() and path.suffix in {'.csv','.json'} and not re.fullmatch(r'(compute_(A|B|C|UMa)_\d+|refinement_\d+)\.csv',path.name):
                shutil.copy2(path,result/path.name)
        if a.task.startswith('round2-'):
            dest=result/'round2';dest.mkdir(exist_ok=True)
            for path in (WORK/'Gate_4/revision/round2_data').glob('*'):
                if path.suffix in {'.csv','.json'} and not re.fullmatch(r'(time_control_(A|B|C|UMa)_\d+|o1_(budget|depth|small)_\d+)\.csv',path.name):
                    shutil.copy2(path,dest/path.name)
    print('Scalar results / figures:',result)

if __name__=='__main__':main()
