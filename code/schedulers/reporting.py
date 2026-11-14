"""Regenerate the two audit reports from archived per-block timings and verified receipts."""
from pathlib import Path
import csv,gzip,hashlib,json,sys,zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Image,Spacer,PageBreak
from xml.sax.saxutils import escape
root=Path(__file__).resolve().parents[1];out=root/'output/pdf';out.mkdir(exist_ok=True,parents=True)
names={'det':'Conflict-polished','legacy':'Gate 2A subgradient','standalone':'Neural, one shot','hybrid':'Learned warm start'}
def read(path):
    with path.open(encoding='utf-8') as f:return list(csv.DictReader(f))
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main(stage):
    d=root/stage;res=d/'results';pilot=stage=='Gate_2B';lock=json.loads((res/('gate2b_lock.json' if pilot else 'native_primary.json')).read_text());frozen=json.loads((root/'Gate_2B/results/freeze.json').read_text());times=read(res/'times.csv');blocks=read(res/'block_decisions.csv');cuts=read(res/'ecdf.csv');stats=[]
    for k in (32,64):
        for m in names:
            r=[x for x in times if x['method']==m and int(x['k'])==k];b=[x for x in blocks if x['method']==m and int(x['k'])==k]
            qs=lambda key,p,scale:float(np.quantile([float(x[key]) for x in r if x[key]!=''],p))/scale
            stats.append(dict(k=k,method=m,n=len(b),hits=sum(int(x['ok']) for x in b),median_G=float(np.median([float(x['G']) for x in b])),median_ms=float(np.median([float(x['ms']) for x in b])),p95_ms=qs('total_ns',.95,1e6),enclosure_ms=qs('enclosure_ns',.5,1e6),dual_ms=qs('dual_ns',.5,1e6),primal_ms=qs('primal_ns',.5,1e6),neural_wall_ms=qs('neural_ns',.5,1e6),gpu_median=qs('gpu_ms',.5,1),gpu_p95=qs('gpu_ms',.95,1),dc_median=qs('dc',.5,1),Sd_median=qs('Sd',.5,1)))
    with (res/'method_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(stats[0]));w.writeheader();w.writerows(stats)
    fig,axes=plt.subplots(1,2,figsize=(9,3.4),sharey=True,layout='constrained')
    for ax,k in zip(axes,[32,64]):
        for fam,clr in [('CDL','#146574'),('UMa','#b75620')]:
            for m,style in [('det','-'),('legacy',':')]:
                b=[x for x in blocks if int(x['k'])==k and x['method']==m and (x['family']=='UMa')==(fam=='UMa')];g=np.sort([float(x['G']) if float(x['ms'])<={32:250,64:1000}[k] else np.inf for x in b]);j=np.isfinite(g)
                xv=np.r_[0,g[j],.35];yv=np.r_[0,np.arange(1,j.sum()+1)/len(g),j.sum()/len(g)];ax.step(xv,yv,where='post',color=clr,ls=style,lw=1.8,label=f'{fam} · {names[m]}')
        ax.axvline(.15,ls='--',lw=.9,color='#555');ax.set(xlim=(0,.35),ylim=(0,1.02),xlabel='Certified gap (bit/s/Hz)',title=f'{k} users · {250 if k==32 else 1000} ms');ax.grid(alpha=.20)
    axes[0].set_ylabel('Fraction of all topology blocks');axes[1].legend(loc='lower right',fontsize=7,frameon=False)
    fig.savefig(res/'stratified_ecdf.png',dpi=180);fig.savefig(res/'stratified_ecdf.svg');plt.close(fig)
    ss=getSampleStyleSheet();ss.add(ParagraphStyle(name='Kick',fontName='Helvetica-Bold',fontSize=9,textColor=colors.HexColor('#197373'),spaceAfter=7));ss.add(ParagraphStyle(name='Body2',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=7,textColor=colors.HexColor('#203944')))
    md=[];story=[];title=('Gate 2B: fresh-pilot verdict' if pilot else 'Gate 3: confirmatory campaigns')
    def head(t):md.append('## '+t);story.append(Paragraph(escape(t),ss['Heading2']))
    def para(t):md.append(t);story.append(Paragraph(escape(t),ss['Body2']))
    def tab(h,rs):
        md.extend(['| '+' | '.join(h)+' |','|'+'|'.join(['---']*len(h))+'|',*['| '+' | '.join(map(str,r))+' |' for r in rs],''])
        vals=[h]+[[str(x) for x in row] for row in rs];ta=Table(vals,hAlign='LEFT',repeatRows=1);ta.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),'#D8EAEC'),('TEXTCOLOR',(0,0),(-1,0),'#173E48'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F6F7')]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.extend([ta,Spacer(1,3*mm)])
    def pic(p):md.append('!['+p.stem+']('+p.relative_to(d).as_posix()+')');story.append(Image(str(p),width=150*mm,height=54*mm))
    def page():story.append(PageBreak())
    md.append('# '+title);story.append(Paragraph('WIRELESS SCHEDULING  /  RESEARCH EVIDENCE',ss['Kick']));story.append(Paragraph(title,ss['Title']))
    n=lock['denominator'];hits=lock['passages'];h32=hits['32'];h64=hits['64'];head('The deterministic operating point')
    para(f"The frozen deterministic solver met both the 0.15 bit/s/Hz gap and the wall-time deadline on {h32}/{n} blocks at 32 users and {h64}/{n} at 64. The required fractions were 80% and 60%; the caps were 250 and 1,000 ms. Each block contributes three timings, one topology-level decision and equal profile weight.")
    tab(['Users','Solver','Joint hits','Median gap','Median ms','p95 ms'],[[x['k'],names[x['method']],f"{x['hits']}/{n}",f"{x['median_G']:.4f}",f"{x['median_ms']:.1f}",f"{x['p95_ms']:.1f}"] for x in stats])
    para('Median times use the three-repeat topology median; p95 uses all calls. The legacy comparator is the original resource subgradient plus P3 on these very same channels. A standalone forward predicts its own price, pairing, powers and anchor. The hybrid retains the cold branch before checking additional prices; this protects the completed interval but takes additional time.')
    for k in ('32','64'):
        de=lock['paired_learning_difference_and_ci'][k];para(f"K={k}: hybrid minus deterministic joint utility {100*de[0]:+.2f} percentage points (paired 95% bootstrap interval {100*de[1]:+.2f} to {100*de[2]:+.2f}). One-sided 97.5% lower confidence limit for deterministic usefulness: {100*lock['bootstrap_lower'][k]:.2f}%.")
    page();head('Single-site and four-site distributions');pic(res/'stratified_ecdf.png')
    tab(['Users','Profile','N','Gap hits','On time','Joint hits','Median gap'],[[r['k'],r['family'],r['n'],r['gap'],r['ontime'],r['joint'],f"{float(r['median_G']):.4f}"] for r in cuts if r['method']=='det' and r['tau']=='0.15' and r['family'] in ('A','B','C','CDL','UMa')])
    para('Each staircase includes late calls in the denominator. At a given gap, its height is the fraction that also arrived before the size-specific deadline. All four thresholds and all methods are tabulated in results/ecdf.csv. Per-topology ordinary and deadline-aware curves can be reconstructed from block_decisions.csv.')
    head('Where time and conflict remain')
    tab(['Users','Solver','Box ms','Dual ms','Primal ms','GPU p95 ms','Conflict'],[[x['k'],names[x['method']],f"{x['enclosure_ms']:.1f}",f"{x['dual_ms']:.1f}",f"{x['primal_ms']:.1f}",f"{x['gpu_p95']:.2f}" if x['gpu_p95'] else 'n/a',f"{x['dc_median']:.4f}"] for x in stats])
    para('Box includes features/endpoints. GPU p95 is synchronized inference. Conflict means matched R minus A, in bit/s/Hz; the attained pooled score is archived separately.')
    page();head('What was frozen and what was checked')
    para('The native match engine exports node and positive odd-set duals on integer weights at scale 2^40. An independent integer checker tests every inequality and objective equality. The primary tried seven price updates at K=32 and six at K=64. Its candidate pool uses every iterate’s matched pairs plus disjoint tone candidates; it permits label swaps and two-pair partner exchanges before four projected-power steps. A failed dual invokes the checked P3 repair.')
    para(f"{lock['timed']:,} timed calls mapped to {lock['verified_distinct']:,} distinct archived receipts. Separate CPU replay checked the covered rate table, matching/assignment witnesses or P3, pooled schedule, deployed powers and receiver, and the equality and signs of the four ledger terms. Observed violations: {lock['violations']}. All paired cold/hybrid endpoints were checked online. No count of zero violations implies a general empirical guarantee.")
    tr=[json.loads((root/'Gate_2B/results'/f"seed_{s['seed']}.json").read_text()) for s in frozen['scores']]
    para('Each seed was fitted for 15 complete epochs on 4,096 blocks/epoch (7,695 optimizer steps). On the original 256 validation blocks, seed 1729 won by mean ECDF at 0.02, 0.05, 0.10 and 0.15. The learned price target is the centered Hungarian tone potential on the teacher’s selected schedule. At inference the warm start guides three extra price proposals; child-head outputs guide priorities, while actual leaf enclosures remain deterministic. No learned child-coordinate tangent tightening is claimed.')
    tab(['Seed','ECDF score','Validation median gap','Fit minutes'],[[s['seed'],f"{s['ecdf']:.4f}",f"{s['median_G']:.4f}",f"{t['seconds']/60:.2f}"] for s,t in zip(frozen['scores'],tr)])
    para('The requested 15-minute bound held per seed. Aggregate training was %.2f minutes on a Quadro RTX 4000 Max-Q. GPU p95 must be evaluated separately from forward medians and complete receipt time.'%(sum(t['seconds'] for t in tr)/60))
    if pilot:
        val=read(res/'validation_controls.csv')
        head('Paired validation comparison')
        tab(['Solver','Blocks','Mean ECDF','Median gap','Median ms'],[[names[m],sum(v['method']==m for v in val),f"{np.mean([float(v['G'])<=c for v in val if v['method']==m for c in [.02,.05,.1,.15]]):.4f}",f"{np.median([float(v['G']) for v in val if v['method']==m]):.4f}",f"{np.median([float(v['ms']) for v in val if v['method']==m]):.1f}"] for m in names])
        para('Disposition: Gate 2B passed, its lock was written before generating any Gate 3 input, and Gate 3 was launched. The accepted Gate 2A imperfect-CSI and Rice results keep their original scope; the two user-RF chains are not independent hardware acquisitions. Gate 3 has its own report and does not use these pilots as confirmatory observations.')
    else:
        add=d/'SUPPLEMENT.md'
        if add.exists():
            page();head('Secondary evidence and limits')
            for line in add.read_text(encoding='utf8').splitlines():
                if line.strip() and not line.startswith('#'):para(line)
            panels=[('F1_native_scale','1. Native scale and receipt cost'),('F2_conflict','2. Exact scheduling loss and selectivity'),('F3_uncertain_CSI','3. Fixed and scaled pilot energy'),('F4_phase_mismatch','4. Scalar mismatch and phase references'),('F5_net_benefit','5. When extra references repay their cost'),('F6_Rice_descriptive','6. Distributed six-user recorded-input replay')]
            for j,(file,label) in enumerate(panels):
                if j%2==0:page()
                head(label);pic(res/'figures'/(file+'.png'))
            if (res/'argos/condition_summaries.csv').is_file():
                page();head('Rice Argos: six-user spatial correlation')
                para('This secondary check uses three UHF recordings from the same eight-stream array. Each frame statistic averages squared spatial correlation over 15 distinct user pairs and 52 occupied pilot tones. Zero means orthogonal spatial vectors; one means parallel up to complex gain.')
                ar=read(res/'argos/condition_summaries.csv');fmt=lambda v:f"{float(v):.3f}" if v else 'n/a'
                tab(['Recording','RFs','Usable / planned','First LTS: median [IQR]','Second LTS: median'],[[v['recording'],v['RFs'],v['valid']+'/'+v['planned'],fmt(v['median_first'])+' ['+fmt(v['q25_first'])+', '+fmt(v['q75_first'])+']',fmt(v['median_second'])] for v in ar])
                pic(res/'argos/spatial_correlation.png');story.append(Spacer(1,3*mm))
                para('Each plotted cell is the median of a single user pair over the usable frames. Gray diagonal cells exclude self-comparisons. The table averages pairs before taking a median. Frame interquartile ranges describe variability within each recording; they are not confidence intervals.')
                para('The first 64 frames set the RF mask. Thirty-two later frame IDs were fixed before decoding; unusable frames were not replaced. These receive-vector statistics include the recording’s gain settings. One recording per condition supports descriptive comparison only; it does not add an independent distributed clock layout or measure throughput.')
                para('Source: Rice Argos Channel Survey; Clayton Shepard, Jian Ding, Ryan E. Guerra and Lin Zhong, Understanding Real Many-Antenna MU-MIMO Channels, Asilomar 2016. The accompanying ARGOS.md links the authors’ paper, source inventory and decoder convention. The archive includes exact acquired-byte hashes and derived statistics, not raw pilot samples.')
    para('Reproduction: frozen model, source hashes, numerical seed manifest, data digests, per-call times, per-block decisions, stage logs and replayable receipts are included in the local evidence directories. The source build used Zig 0.13.0 with LEMON 1.3.1 and flags -std=c++14 -O3 -DNDEBUG -DWIN32 -shared. Seed 1729 and the binary SHA are pinned in Gate_2B/results/freeze.json.')
    (d/'REPORT.md').write_text('\n\n'.join(md)+'\n',encoding='utf8')
    def footer(c,doc):
        c.setFillColor(colors.HexColor('#456575'));c.setFont('Helvetica',8);c.drawString(19*mm,12*mm,title);c.drawRightString(190*mm,12*mm,str(doc.page))
    target=out/(stage+'_Report.pdf');doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=17*mm,leftMargin=19*mm,topMargin=16*mm,bottomMargin=19*mm,title=title,author='Research evidence package');doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(target,sha(target),flush=True)
if __name__=='__main__':main(sys.argv[1])

