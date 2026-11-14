"""Recreate the confirmatory estimands and manuscript evidence from hashed numerical records."""
import hashlib, itertools, json, math, statistics
from collections import Counter,defaultdict
from fractions import Fraction
import numpy as np
from scipy import stats
from prepare import archive,OUT,dump,read_rows,write_rows,zipfile
def near(x,y,eps=2e-12):
    assert math.isclose(float(x),float(y),rel_tol=eps,abs_tol=eps),(x,y)
def groups(seq,keys):
    d=defaultdict(list)
    for r in seq:d[tuple(r[k] for k in keys)].append(r)
    return d
def main():
    with zipfile.ZipFile(archive('Gate_3')) as z:
        R='Gate_3/results/';sources={}
        def data(path,blob=False):
            b=z.read(path);sources[path]=hashlib.sha256(b).hexdigest();return b if blob else read_rows(b)
        def rows(n):return data(R+n+'.csv')
        def js(n):return json.loads(data(R+n+'.json',True))
        official=js('native_primary'); decisions=read_rows((OUT/'rebuilt_block_decisions.csv').read_bytes())
        d={(v['family'],int(v['block']),int(v['k']),v['method']):v for v in decisions};assert len(d)==4096
        fam=['A','B','C','UMa'];methods=['legacy','det','standalone','hybrid'];table=[];pairs=[];rng=np.random.default_rng(19073)
        for k in [32,64]:
            mats={}
            for m in methods:
                a=[[d[f,i,k,m] for i in range(128)] for f in fam];flat=sum(a,[])
                mats[m]=np.array([[int(v['ok']) for v in row] for row in a])
                table.append(dict(k=k,method=m,passed=int(mats[m].sum()),n=512,fraction=float(mats[m].mean()),median_G=statistics.median(float(v['G']) for v in flat),median_ms=statistics.median(float(v['ms']) for v in flat)))
            d0=mats['det'];d1=mats['hybrid'];dif=d1-d0;tr=Counter(zip(d0.ravel(),d1.ravel()))
            b,c=tr[0,1],tr[1,0];tot=b+c
            one=Fraction(sum(math.comb(tot,i) for i in range(b,tot+1)),2**tot);two=min(1,2*min(one,Fraction(sum(math.comb(tot,i) for i in range(b+1)),2**tot)))
            ix=rng.integers(128,size=(10000,4,128));axis=np.arange(4)[None,:,None];draw=d0[axis,ix].mean((1,2));diff=dif[axis,ix].mean((1,2))
            lcl=float(np.quantile(draw,.025));ci=np.quantile(diff,[.025,.975]).tolist()
            assert int(d0.sum())==official['passages'][str(k)] and lcl==official['bootstrap_lower'][str(k)] and [float(dif.mean()),*ci]==official['paired_learning_difference_and_ci'][str(k)]
            pairs.append(dict(k=k,both_pass=tr[1,1],det_only=c,warm_only=b,neither=tr[0,0],headroom=(512-int(d0.sum()))/512,rescued_fraction=float(b/(512-int(d0.sum()))),difference=float(dif.mean()),bootstrap_low=ci[0],bootstrap_high=ci[1],deterministic_lower_975=lcl,exact_mcnemar_two_sided=float(two),exact_mcnemar_warm_better_one_sided=float(one)))
        write_rows('primary_table.csv',table);write_rows('paired_transitions.csv',pairs)
        sens=rows('sensitivity_grid');native=[q for q in sens if q['campaign']=='native' and float(q['k'])==16 and float(q['db'])==10]
        native.sort(key=lambda r:(r['family'],int(r['block'])));assert len(native)==512 and len(sens)==13824
        pop=[int(float(r['R']))-int(float(r['dp_H'])) for r in native]
        po=[int(float(r['R']))-int(float(r['matched_A'])) for r in native]
        for l,p,r in zip(pop,po,native):near(l/(2**40*8*math.log(2)),r['loss']);near(p/(2**40*8*math.log(2)),r['posterior'])
        # Use the native per-topology exports for full precision in ranks; the combined CSV passed through pandas formatting.
        cells=[]
        for f in fam:
            for i in range(128):
                rr=data(R+f'grid_native/{f}_{i:03d}.csv');cells.append(next(r for r in rr if r['k']=='16' and r['db']=='10'))
        diag=js('structure_summary');rng=np.random.default_rng(19073)
        tr=rows('transition');fractions=[]
        for v in sorted(set(float(r['t']) for r in tr)):
            sub=[r for r in tr if float(r['t'])==v];assert len(sub)==128
            for r in sub:
                near(sum(float(r[f'term{k}']) for k in range(1,5)),r['total'])
                assert (float(r['total'])>0 and 2*float(r['dc'])>float(r['total']))==bool(int(r['dominant']))
            fractions.append(sum(int(r['dominant']) for r in sub)/len(sub))
        assert fractions==js('transition_summary')['fraction']==[0.]*9
        _=rng.integers(0,128,(10000,128))
        result={}
        loss=np.array([float(r['loss']) for r in cells]).reshape(4,128)
        for var in ['posterior','prior']:
            x=np.array([float(r[var]) for r in cells]).reshape(4,128)
            val=float(stats.spearmanr(x.ravel(),loss.ravel()).statistic);vals=[]
            for j in range(100):
                idx=rng.integers(128,size=(100,4,128))
                def rank(M):
                    a=stats.rankdata(M[np.arange(4)[None,:,None],idx].reshape(100,512),axis=1);a-=a.mean(1)[:,None];return a
                ra,rb=rank(x),rank(loss);vals.extend(np.sum(ra*rb,axis=1)/np.sqrt(np.sum(ra*ra,axis=1)*np.sum(rb*rb,axis=1)))
            ci=list(map(float,np.quantile(vals,[.025,.975])))
            near(val,diag[var]['rho']);near(ci[0],diag[var]['ci'][0]);near(ci[1],diag[var]['ci'][1])
            result[var]=dict(rho=val,ci=ci,valid_bootstrap=len(vals))
        valid_unc=rows('uncertainty');cal=groups(data('Gate_2/results/calibration_scores.csv'),['family','db','arm'])
        unc=[];ref_unc={(r['family'],r['db'],r['arm']):r for r in rows('uncertainty_summary')}
        for key,grp in sorted(groups(valid_unc,['family','db','arm']).items()):
            f,db,arm=key;cc=cal[key];assert len(cc)==256 and len(grp)==128
            q1,q2=[sorted(float(r[col]) for r in cc)[250] for col in ['T_F','T_P']]
            metrics=Counter()
            for v in grp:
                F=float(v['T_F'])<=q1;P=float(v['T_P'])<=q2
                assert F==bool(int(v['hitF'])) and P==bool(int(v['hitP'])) and F*P==int(v['joint'])
                G=float(v['U_F'])-float(v['LP']);ret=float(v['LP'])/float(v['U_F']);near(G,v['G_P']);near(ret,v['retention'])
                ok=float(v['LP'])>0 and G<=.5 and ret>=.95 and float(v['ms'])<=1000
                assert int(v['ok'])==ok
                if F:assert float(v['LF'])<=float(v['true_rate'])<=float(v['U_F'])
                if P:assert float(v['LP'])<=float(v['true_rate'])<=float(v['fixed_action_upper'])
                metrics.update(dict(joint=F*P,useful=ok,F=F,P=P))
            p=stats.binomtest(metrics['joint'],128,.95,alternative='less').pvalue
            for k0 in metrics:assert metrics[k0]==int(ref_unc[key][k0])
            near(p,ref_unc[key]['pvalue']);assert int(p<.025)==int(ref_unc[key]['coverage_flag'])
            unc.append(dict(family=f,db=db,arm=arm,n=128,**metrics,p=float(p),coverage_flag=int(p<.025),median_G=statistics.median(float(r['G_P']) for r in grp)))
        write_rows('uncertainty_cells.csv',unc)
        ablations=[]
        for i in range(128):ablations+=data(R+f'ablations/{i:03d}.csv')
        ab=[];grouped=groups(ablations,['mode','family'])
        for r in rows('ablation_summary'):
            subset=grouped[r['mode'],r['family']];vs=[float(x['G']) for x in subset];assert len(vs)==int(r['n']);near(statistics.median(vs),r['median_G'])
        for (mode,),subset in groups(ablations,['mode']).items():ab.append(dict(mode=mode,n=len(subset),median_gap=statistics.median(float(x['G']) for x in subset)))
        write_rows('ablation_pooled.csv',ab)
        phase=rows('phase_mse');pg=groups(phase,['m1','law','M','policy']);ps=[]
        for v in phase:
            m,c,a=[float(v[k]) for k in ['m1','true_c','assumed_c']]
            var=1-m*m
            def mse(z):
                errs=[]
                for sign in (1,-1):
                    true_var=(var+sign*c)/2;assumed=(var+sign*z)/2;coef=assumed/(assumed+.25)
                    errs.append((1-coef)**2*true_var+coef**2*.25)
                return sum(errs)
            near(mse(a),v['MSE']);near(mse(c),v['oracle_mse']);near(mse(0),v['ordinary_mse'])
            if v['retained_gain']:near((mse(0)-mse(a))/(mse(0)-mse(c)),v['retained_gain'])
        for r in rows('phase_summary'):
            sub=pg[tuple(r[k] for k in ['m1','law','M','policy'])];near(statistics.mean(float(v['MSE']) for v in sub),r['MSE'])
            if r['gain']:near(statistics.mean(float(v['retained_gain']) for v in sub),r['gain'])
            if r['law']=='von_mises' and r['M']=='16' and r['policy']=='binary_assumed':ps.append(dict(m1=r['m1'],mse=float(r['MSE']),retained_gain=float(r['gain'])))
        bands={(r['family'],r['arm'],r['block']):r for r in rows('policy_rate_bands')};nr=rows('net_benefit');ng=groups(nr,['family','arm','H','M'])
        for v in nr:
            b=bands[v['family'],v['arm'],v['block']];h,m=int(v['H']),int(v['M']);a=.875;t=max(0,a-m/(8*h))
            avail=int(32*m+32*h<=256*h);lo=t*float(b['warm_lo'])-a*float(b['cold_hi']);hi=t*float(b['warm_hi'])-a*float(b['cold_lo'])
            near(lo,v['gain_lower']);near(hi,v['gain_upper']);assert (avail,avail*(lo>1e-5),avail*(hi< -1e-5),avail*(lo<=1e-5 and hi>=-1e-5))==tuple(int(v[k]) for k in ['affordable','win','loss','indeterminate'])
        for r in rows('net_summary'):
            sub=ng[tuple(r[k] for k in ['family','arm','H','M'])]
            for field,orig in [('mean_lower','gain_lower'),('mean_upper','gain_upper'),('win','win'),('loss','loss'),('indeterminate','indeterminate'),('affordable','affordable')]:near(statistics.mean(float(t[orig]) for t in sub),r[field])
        # Rebuild the two ray-scene median curves from individual held-out tiles.
        ray=[]
        for key,group in sorted(groups([r for r in sens if r['campaign']=='ray'],['family','k','db']).items()):
            assert len(group)==64
            ray.append(dict(family=key[0],k=int(float(key[1])),db=float(key[2]),n=64,median_gap=statistics.median(float(r['G']) for r in group),median_ms=statistics.median(float(r['total_ns']) for r in group)/1e6))
        write_rows('deepmimo_cells.csv',ray)
        rice=[];official_rice={r['mode']:r for r in rows('rice_descriptive')}
        for mode in ['HUB','LO']:
            raw=data('Gate_2/results/rice_replay_'+mode+'.csv');meta=json.loads(data('Gate_2/results/rice_replay_'+mode+'.json',True));alln=meta['frames']-128
            g=sum(float(x['G'])<=.1 and float(x['ms'])<=250 for x in raw);change=statistics.median(float(x['later_LTS_fixed_action_rate'])-float(x['L_proxy']) for x in raw)
            assert (len(raw),g,alln)==tuple(int(official_rice[mode][k]) for k in ['eligible','success','postprefix_frames']);near(change,official_rice[mode]['median_later_change'])
            rice.append(dict(mode=mode,denominator=alln,retained=len(raw),useful=g,fraction=g/alln,median_ms=statistics.median(float(x['ms']) for x in raw),median_later_change=change))
        write_rows('renew_capture_totals.csv',rice)
        # A minimalist independently regenerated vector figure, source table alongside it.
        labels={'det':'Conflict-polished','hybrid':'Learned warm start','standalone':'One-shot','legacy':'Legacy subgradient'}
        from xml.sax.saxutils import escape
        parts=['<svg xmlns="http://www.w3.org/2000/svg" width="700" height="390" viewBox="0 0 700 390"><rect width="700" height="390" fill="white"/><g font-family="Arial" fill="#162f3b"><text x="18" y="26" font-size="17">Gate 4 • primary usefulness reconstructed from verified receipts</text>']
        for j,r in enumerate(table):
            y=55+37*j;length=350*r['fraction'];parts.append(f'<text x="18" y="{y+13}" font-size="13">K={r["k"]} · {escape(labels[r["method"]])}</text><rect x="195" y="{y}" width="350" height="17" fill="#e9edef"/><rect x="195" y="{y}" width="{length:.2f}" height="17" fill="#176a72"/><text x="559" y="{y+13}" font-size="13">{r["passed"]}/512</text>')
        parts.append('<text x="18" y="370" font-size="12">All three gaps ≤ 0.15 bit/s/Hz; median time ≤ 250 ms (32 users) or 1,000 ms (64 users).</text></g></svg>')
        (OUT/'primary_reconstruction.svg').write_text(''.join(parts),encoding='utf-8')
        dump('figure_numerics.json',dict(native_structure=result,transition_fractions=fractions,phase_mismatch_von_mises=ps,phase_rows=len(phase),base_action_bands=len(bands),net_cells_recomputed=len(nr),net_win_count=sum(int(r['win']) for r in nr),ablations=len(ablations),uncertainty_cells=len(unc),deepmimo_tiles_per_scene=64,rice=rice))
        write_rows('numerical_source_hashes.csv',[dict(member=k,sha256=v) for k,v in sorted(sources.items())])
if __name__=='__main__':main()
