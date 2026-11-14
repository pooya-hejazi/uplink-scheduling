"""Validate immutable release packages; fix the sample before running any numerical checks."""
from pathlib import Path
import csv, datetime, hashlib, io, json, os, platform, shutil, subprocess, sys, tarfile, tempfile, zipfile
import importlib.metadata as md

AUD = Path(__file__).resolve().parent
RELEASE = Path(os.environ.get('GATE_RELEASES', str(AUD.parents[1] / 'output')))
WORK = Path(os.environ.get('GATE4_SCRATCH', str(Path(tempfile.gettempdir()) / 'g4_independent_cpu_v1'))).resolve()
SRC = WORK / 'release'
ENV = WORK / 'venv'
OUT = AUD / 'results'
OUT.mkdir(exist_ok=True)
def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
def read_rows(b):
    return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'), newline='')))
def write_rows(name, records):
    with (OUT/name).open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f,records[0].keys()); w.writeheader(); w.writerows(records)
def path_hash(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def archive(g):
    return RELEASE / (g+'_Deliverable_Package.zip')
def sample():
    p=archive('Gate_3'); seed=path_hash(p)
    assert seed==p.with_suffix('.sha256').read_text().split()[0]
    with zipfile.ZipFile(p) as z:
        units=[]
        for kind,manifest,key in [('native','data_manifest','family'),('analytic','analytic_seeds','family'),('ray','ray_manifest','scene')]:
            for r in read_rows(z.read('Gate_3/'+manifest+'.csv')):
                f,i=r[key],int(r['block'])
                label=f'{kind}|{f}|{i}'
                rank=hashlib.sha256(b'Gate4-receipt-audit-v1\0'+bytes.fromhex(seed)+b'\0'+label.encode('ascii')).hexdigest()
                units.append(dict(source=kind,family=f,block=i,rank_sha256=rank))
        assert len(units)==1152==len({(r['family'],r['block']) for r in units})==len({r['rank_sha256'] for r in units})
        units.sort(key=lambda r:r['rank_sha256'])
        write_rows('eligible_sample_frame.csv',units); write_rows('precommitted_sample.csv',units[:58])
        summary=dict(protocol='Without replacement: sort by SHA256(ASCII Gate4-receipt-audit-v1 || NUL || binary ZIP SHA256 || NUL || ASCII source|family|block); take smallest ceil(0.05N) hashes. No stratification, outcome filtering, geography weighting or replacement.',population=1152,selected=58,snrs_db=[-5,0,10,20],release_sha256=seed,sample_sha256=path_hash(OUT/'precommitted_sample.csv'),frame_sha256=path_hash(OUT/'eligible_sample_frame.csv'))
        file=OUT/'sample_commitment.json'
        if file.exists():
            old=json.loads(file.read_text()); assert all(old[k]==v for k,v in summary.items())
        else:
            summary['committed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();dump(file.name,summary)
        print('Committed sample',summary['sample_sha256'],flush=True)
def validate():
    SRC.mkdir(parents=True,exist_ok=True); evidence={}
    for g in ('Gate_1','Gate_2','Gate_2B','Gate_3'):
        p=archive(g); digest=path_hash(p)
        if p.with_suffix('.sha256').exists(): assert digest==p.with_suffix('.sha256').read_text().split()[0]
        with zipfile.ZipFile(p) as z:
            manifest=g+'/SHA256SUMS'; names=z.namelist(); entries=dict((v.split('  ',1)[1],v.split('  ',1)[0]) for v in z.read(manifest).decode().splitlines())
            assert len(names)==len(set(names))==len(entries)+1 and set(names)-{manifest}==set(entries)
            for n,h in entries.items():
                with z.open(n) as f: assert hashlib.file_digest(f,'sha256').hexdigest()==h,(g,n)
                # Share no mutable worktree source, trained weight, released DLL, or result cache with the auditor.
                needed=(g=='Gate_1' and n.startswith(g+'/') and n.endswith('.py')) or (g in ('Gate_2','Gate_2B') and n.startswith(g+'/') and (n.endswith(('.py','.cpp')) or n.endswith(('/build.json','/freeze.json','/gate2b_lock.json')))) or (g=='Gate_3' and n in ('Gate_3/inputs.py','Gate_3/exact_two.py','Gate_3/oracle.py','Gate_3/grid.py','Gate_3/structure.py'))
                if needed:
                    dest=SRC/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
            evidence[g]=dict(sha256=digest,bytes=p.stat().st_size,manifest_entries=len(entries),inner_manifest_sha256=hashlib.sha256(z.read(manifest)).hexdigest(),detached_sha256=p.with_suffix('.sha256').exists())
            print('Verified',g,len(entries),'members',flush=True)
    with zipfile.ZipFile(archive('Gate_2')) as z:
        assert hashlib.sha256(z.read('output/Gate_1_Deliverable_Package.zip')).hexdigest()==evidence['Gate_1']['sha256']
    with zipfile.ZipFile(archive('Gate_3')) as z,zipfile.ZipFile(archive('Gate_2B')) as z2:
        pre='Gate_2B/results/'; freeze=z.read(pre+'freeze.json'); lock=z.read(pre+'gate2b_lock.json')
        assert z2.read(pre+'freeze.json')==freeze and z2.read(pre+'gate2b_lock.json')==lock
        authority=json.loads(z.read('Gate_3/results/native_primary.json'))
        assert json.loads(lock)['freeze']==authority['freeze']==hashlib.sha256(freeze).hexdigest()
        for field,name in [('channels','data_manifest.csv'),('decisions','results/block_decisions.csv'),('times','results/times.csv')]:
            assert hashlib.sha256(z.read('Gate_3/'+name)).hexdigest()==authority[field]
        with zipfile.ZipFile(archive('Gate_2')) as prior:
            for name,expected in json.loads(freeze)['source'].items():
                name=name.replace('\\','/')
                zp=z2 if name in z2.namelist() else prior
                assert hashlib.sha256(zp.read(name)).hexdigest()==expected,name
    dump('release_integrity.json',evidence)
def environment(hardware_io=False):
    if not hardware_io:
        if ENV.exists():raise FileExistsError(f'Use a fresh GATE4_SCRATCH directory: {ENV}')
        subprocess.run([sys.executable,'-I','-m','venv','--without-pip',str(ENV)],check=True)
    pkg=ENV/'Lib/site-packages'; pkgs={}
    packages=[('h5py','3.12.1')] if hardware_io else [('numpy','2.3.4'),('scipy','1.16.3'),('numba','0.62.1'),('llvmlite','0.45.1'),('networkx','3.4.2'),('threadpoolctl','3.5.0'),('mpmath','1.3.0'),('sympy','1.13.3')]
    for name,version in packages:
        d=md.distribution(name); assert d.version==version,(name,d.version)
        # Install only the pinned local packages, by hard link, into a site-isolated venv.
        # No global/user site-packages or editable workspace imports are enabled.
        tree=hashlib.sha256();total=0
        for top in [d.locate_file(name),d.locate_file(name+'.py'),d._path]:
            if not top.exists():continue
            for f in (top.rglob('*') if top.is_dir() else (top,)):
                if not f.is_file() or '__pycache__' in f.parts or f.suffix in ('.pyc','.nbi','.nbc'): continue
                rel=f.relative_to(d.locate_file('')); target=pkg/rel;target.parent.mkdir(exist_ok=True,parents=True)
                if target.exists():assert path_hash(target)==path_hash(f)
                else:
                    try:os.link(f,target)
                    except OSError:shutil.copyfile(f,target)
                tree.update(rel.as_posix().encode()+b'\0'+bytes.fromhex(path_hash(f)));total+=1
        pkgs[name]=dict(version=version,files=total,linked_content_sha256=tree.hexdigest())
    if hardware_io:
        info=json.loads((OUT/'environment.json').read_text());info['optional_hardware_io']=pkgs
        info['optional_hardware_io_scope']='h5py is used only to locate narrowly bounded authenticated Rice source windows; the optional source check requires HTTPS.'
        dump('environment.json',info);return
    dump('environment.json',dict(platform=platform.platform(),cpu=platform.processor(),python=sys.version,python_executable_sha256=path_hash(sys.executable),dependencies=pkgs,venv_system_site_packages=False,source='Local exact-version binary distributions; base CPython stdlib and native system/Conda math-runtime DLLs. No network required for released/native computational checks; no torch, GPU or model weights are used.',threads=1))
    print('Fresh isolated CPU environment created',flush=True)
def build():
    archive_dir=Path(os.environ.get('GATE4_TOOL_ARCHIVES',str(Path(tempfile.gettempdir())/'gate2b-toolchain-v1')))
    builddir=WORK/'toolchain';builddir.mkdir(parents=True,exist_ok=True)
    spec=json.loads((SRC/'Gate_2B/native/build.json').read_text()); zname='zig-windows-x86_64-0.13.0'
    zp=archive_dir/(zname+'.zip');lp=archive_dir/'lemon-1.3.1.tar.gz'
    assert path_hash(zp)==spec['zig_zip_sha256'] and path_hash(lp)==spec['lemon_archive_sha256']
    # Compiler installation is read-only; compare its entire binary and included sources to the pinned ZIP.
    with zipfile.ZipFile(zp) as zz:
        for info in zz.infolist():
            if info.is_dir():continue
            f=archive_dir/info.filename
            with zz.open(info) as fp:assert path_hash(f)==hashlib.file_digest(fp,'sha256').hexdigest(),info.filename
    with tarfile.open(lp) as t:
        for m in t.getmembers():
            if m.isfile() and (m.name.startswith('lemon-1.3.1/lemon/') or m.name=='lemon-1.3.1/LICENSE'):
                t.extract(m,builddir,filter='data')
    lemon=builddir/'lemon-1.3.1';(lemon/'lemon/config.h').write_text('#define LEMON_VERSION "1.3.1"\n#define LEMON_HAVE_LONG_LONG 1\n')
    dll=SRC/'Gate_2B/native/exact_match.dll';zig=archive_dir/zname/'zig.exe'
    cmd=[str(zig),'c++','-std=c++14','-O3','-DNDEBUG','-DWIN32','-shared','-I'+str(lemon),str(SRC/'Gate_2B/exact_match.cpp'),str(lemon/'lemon/base.cc'),'-o',str(dll)]
    cmd_env=os.environ.copy();cmd_env.update(ZIG_GLOBAL_CACHE_DIR=str(builddir/'global-cache'),ZIG_LOCAL_CACHE_DIR=str(builddir/'local-cache'))
    p=subprocess.run(cmd,env=cmd_env,cwd=builddir,check=True,capture_output=True,text=True);print(p.stdout,p.stderr,flush=True)
    dump('build.json',dict(compiler='Zig 0.13.0 C++ frontend',compiler_archive_sha256=path_hash(zp),lemon_archive_sha256=path_hash(lp),flags=['-std=c++14','-O3','-DNDEBUG','-DWIN32','-shared'],compiled_source_sha256=path_hash(SRC/'Gate_2B/exact_match.cpp'),compiled_dll_sha256=path_hash(dll),released_dll_sha256=spec['dll_sha256'],fresh_local_and_global_build_cache=True))
if __name__=='__main__':
    {'sample':sample,'validate':validate,'environment':environment,'hardware_io':lambda:environment(True),'build':build}[sys.argv[1]]()
