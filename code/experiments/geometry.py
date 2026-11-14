"""Publish per-site geometry, actual source scales and native-UMa unnormalized sensitivity."""
from grid import *
def main():
    guard();rr=[];positions=[];dest=root3/'results';sites=np.array([[0,0,25],[500,0,25],[0,500,25],[500,500,25]])
    for i in range(128):
        a=np.load(root3/'data'/f'pilot_UMa_{i:04d}.npz');xyz=a['xyz'];raw=a['h'];ids=a['perm'];assert xyz.shape==(64,3)
        for u in range(64):positions.append(dict(block=i,nested_user=u,source_user=int(ids[u]),x=xyz[u,0],y=xyz[u,1],z=xyz[u,2]))
        for k in (16,32,64):
            h=np.ascontiguousarray(raw[:k,:,::(64//(k//2))],dtype=complex);r,_,ti=solve(h);replay(h,r);p=np.abs(h.reshape(k,4,4,k//2))**2;site=np.log(np.maximum(1e-300,p.mean((2,3))));cc=np.corrcoef(site.T);norm=k//2*np.log(2);d=int(r['den'])*norm
            rr.append(dict(block=i,k=k,scale=1,model='native_pathloss_shadowing_unit_noise',median_antenna_SNR_dB=10*np.log10(.1*np.median(np.mean(abs(h)**2,axis=1))),G=r['G'],L=int(r['L'])/d,U=int(r['U'])/d,ms=ti['total_ns']/1e6,average_link_logpower_correlation=cc[np.triu_indices(4,1)].mean()))
    putcsv(dest/'uma_source_sensitivity.csv',rr);putcsv(dest/'uma_ue_positions.csv',positions)
    (dest/'geometry.json').write_text(json.dumps(dict(family='UMa',site_xyz_m=sites.tolist(),orientation_rad=[0,0,0],UT_height_m=1.5,frequency_Hz=3500000000,antennas_per_site=4,antenna='horizontal ULA, half wavelength',noise_convention='unchanged unit noise, raw native path loss; not a receiver noise calibration',distinct_topologies=128),indent=2))
if __name__=='__main__':main()

