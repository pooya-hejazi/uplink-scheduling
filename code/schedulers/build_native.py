"""Build an untrusted speed helper; every returned witness is checked in Python."""
from pathlib import Path
import sys,hashlib,tarfile,tempfile,zipfile,subprocess,json,requests,io
home=Path(__file__).resolve().parent; dst=Path(tempfile.gettempdir())/'gate2b-toolchain-v1';dst.mkdir(exist_ok=True)
def obtain(url,path,digest=None):
    if not path.exists():
        with requests.get(url,stream=True,timeout=(30,180)) as rr,path.with_suffix('.part').open('wb') as o:
            rr.raise_for_status()
            for data in rr.iter_content(2**20):o.write(data)
        path.with_suffix('.part').replace(path)
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest and digest!=actual:raise IOError('toolchain archive digest mismatch')
    return actual
def main():
    ver='zig-windows-x86_64-0.13.0';wp=dst/(ver+'.zip')
    zw=obtain('https://ziglang.org/download/0.13.0/'+wp.name,wp,'d859994725ef9402381e557c60bb57497215682e355204d754ee3df75ee3c158')
    exe=dst/ver/'zig.exe'
    if not exe.exists():
        with zipfile.ZipFile(wp) as z:z.extractall(dst)
    tar=dst/'lemon-1.3.1.tar.gz';base='https://lemon.cs.elte.hu/pub/sources/lemon-1.3.1.tar.gz'
    ls=obtain(base,tar)
    if not (dst/'lemon-1.3.1/lemon/matching.h').exists():
        with tarfile.open(tar) as f:
            for a in f.getmembers():
                if a.name.startswith('lemon-1.3.1/lemon/') or a.name=='lemon-1.3.1/LICENSE':
                    f.extract(a,dst,filter='data')
    inc=dst/'lemon-1.3.1'; (inc/'lemon/config.h').write_text('#define LEMON_VERSION "1.3.1"\n#define LEMON_HAVE_LONG_LONG 1\n')
    art=home/'native';art.mkdir(exist_ok=True)
    (art/'LEMON_LICENSE.txt').write_bytes((inc/'LICENSE').read_bytes())
    cmd=[str(exe),'c++','-std=c++14','-O3','-DNDEBUG','-DWIN32','-shared','-I'+str(inc),str(home/'exact_match.cpp'),str(inc/'lemon/base.cc'),'-o',str(art/'exact_match.dll')]
    print('sources acquired',zw,ls,flush=True);subprocess.run(cmd,check=True)
    (art/'build.json').write_text(json.dumps(dict(zig_zip_sha256=zw,zig_version='0.13.0',lemon_source=base,lemon_archive_sha256=ls,dll_sha256=hashlib.sha256((art/'exact_match.dll').read_bytes()).hexdigest(),flags='-std=c++14 -O3 -DNDEBUG -shared'),indent=2))
if __name__=='__main__':main()

