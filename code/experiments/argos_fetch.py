"""HDF5-indexed HTTP range extraction. Only sample hashes, frame IDs and provenance are released."""
from argos_source import *
import time
private=root/'rice_private'/'argos';private.mkdir(exist_ok=True,parents=True)
def run(name):
    mfile=dest/f'{name}_metadata.json';meta=json.loads(mfile.read_text())
    # The original network-node labels are neither scientific inputs here nor release data.
    meta['schema']['/']['attrs'].pop('nodes_description',None);mfile.write_text(json.dumps(meta,indent=2))
    src=meta['source'];rr=Remote(src)
    try:
        with h5py.File(rr,'r') as f:
            raw=f['Pilot_Samples'];nf,nbs,slots2,iq=raw.shape
            assert nbs==8 and slots2==7*224 and iq==2 and raw.chunks==(64,8,1568,2) and raw.dtype.kind=='i' and raw.dtype.itemsize==2
            assert raw.id.get_create_plist().get_nfilters()==0
            assert int(np.asarray(f.attrs['num_mob_ant']).item())==6 and int(np.asarray(f.attrs['pilot_length']).item())==64 and int(np.asarray(f.attrs['samples_per_user']).item())==224
            dt=raw.dtype;stride=int(np.prod(raw.shape[1:]))*dt.itemsize
            selected=64+((2*np.arange(32)+1)*(nf-64))//64
            assert len(set(selected))==32 and selected[0]>63 and selected[-1]<nf
            rec=[]
            for start,count,why in [(0,64,'calibration')]+[(int(i),1,'evaluation') for i in selected]:
                origin=(start//64*64,0,0,0);ch=raw.id.get_chunk_info_by_coord(origin)
                assert ch.byte_offset is not None and ch.size==64*stride and ch.filter_mask==0 and ch.chunk_offset==origin,(name,start,origin,ch,stride)
                offset=ch.byte_offset+int(start%64)*stride
                assert start%64+count<=64 and offset+count*stride<=src['bytes'];rec.append(dict(start=start,count=count,purpose=why,offset=offset,length=count*stride))
            # One frame is reconstructed independently through h5py to validate byte order, channel order and chunk offsets.
            reference=hashlib.sha256(raw[0].tobytes()).hexdigest()
    finally:rr.session.close();rr.page.cache_clear()
    def read(v):
        start=v['offset'];end=start+v['length']-1
        for attempt in range(4):
            try:
                with requests.get(src['url'],headers={'Range':f'bytes={start}-{end}','If-Match':src['etag'],'Accept-Encoding':'identity'},timeout=(30,75)) as r:
                    r.raise_for_status()
                    if r.status_code!=206 or r.headers.get('Content-Range')!=f"bytes {start}-{end}/{src['bytes']}" or r.headers.get('ETag')!=src['etag']:raise IOError('unpinned or incorrect source range')
                    b=r.content
                if len(b)!=v['length']:raise IOError('incomplete source range')
                v['sha256']=hashlib.sha256(b).hexdigest()
                return np.frombuffer(b,dtype=dt).reshape(v['count'],8,1568,2)
            except (OSError,requests.RequestException):
                if attempt==3:raise
                time.sleep(1+attempt)
    with ThreadPoolExecutor(4) as pool:arrays=list(pool.map(read,rec))
    assert hashlib.sha256(arrays[0][0].tobytes()).hexdigest()==reference
    path=private/f'{name}.npz'
    with path.with_suffix('.partial').open('wb') as fp:np.savez_compressed(fp,cal=arrays[0],evaluation=np.concatenate(arrays[1:]),frame=selected)
    path.with_suffix('.partial').replace(path)
    manifest=dict(source=src,total_frames=nf,source_dtype=dt.str,initial_h5py_frame0_sha256=reference,policy_sha256=hashlib.sha256((root/'ARGOS_PROTOCOL.md').read_bytes()).hexdigest(),raw_ranges=rec)
    (dest/f'{name}_ranges.json').write_text(json.dumps(manifest,indent=2));print(name,len(rec),'pinned pilot ranges, bytes',sum(q['length'] for q in rec),flush=True)
if __name__=='__main__':
    with ThreadPoolExecutor(2) as pool:list(pool.map(run,['static','env','mob']))

