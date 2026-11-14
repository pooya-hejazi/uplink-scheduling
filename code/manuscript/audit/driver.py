"""Run an audit job under the fresh isolated CPU interpreter."""
import os, subprocess, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare import AUD, ENV, WORK, SRC, OUT
if __name__=='__main__':
    if not __debug__:raise RuntimeError('No Python -O in an audit')
    name=sys.argv[1]
    if sys.prefix!=str(ENV) and Path(sys.prefix).resolve()!=ENV:
        env=os.environ.copy()
        env.update(CUDA_VISIBLE_DEVICES='-1',NVIDIA_VISIBLE_DEVICES='none',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='1',NUMBA_CACHE_DIR=str(WORK/'jit'),NUMBA_DISABLE_CUDA='1',PYTHONNOUSERSITE='1')
        env['PATH']=str(Path(sys.base_prefix)/'Library/bin')+os.pathsep+env['PATH']
        proc=subprocess.run([str(ENV/'Scripts/python.exe'),'-I','-B',str(Path(__file__).resolve()),name],env=env,cwd=WORK)
        sys.exit(proc.returncode)
    assert sys.flags.isolated and __debug__ and os.environ['CUDA_VISIBLE_DEVICES']=='-1'
    assert all('site-packages' not in p or Path(p).resolve().is_relative_to(ENV) for p in sys.path)
    for src in ['Gate_1','Gate_2','Gate_2B','Gate_3']:
        sys.path.insert(1,str(SRC/src))
    import runpy, time
    start=time.perf_counter()
    print('CPU isolated job:',name,flush=True)
    runpy.run_path(str(AUD/(name+'.py')),run_name='__main__')
    print(f'PASS {name}; elapsed {time.perf_counter()-start:.3f} seconds',flush=True)
