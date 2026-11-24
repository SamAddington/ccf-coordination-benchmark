#!/usr/bin/env python3
"""Generate complete review-response tables from frozen and new synthetic CSVs.
No new simulations; explicit world cluster unit, no p-value claims.
"""
from __future__ import annotations
import argparse,csv,statistics,json
from pathlib import Path
from itertools import product
from run_symmetric import LOSSES,DEADLINES
from run_admission import bootstrap
ROOT=Path(__file__).resolve().parent

def read(p):
 with open(p,newline='') as f:return list(csv.DictReader(f))
def num(x,k):return float(x[k])
def write(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def by_world(rows,dl,loss,arm):
 rr=[r for r in rows if num(r,'deadline')==dl and num(r,'loss')==loss and r.get('arm')==arm]
 worlds=sorted(set(r['world_seed'] for r in rr))
 assert len(worlds)==12,(arm,dl,loss,len(worlds))
 assert len(rr)==36,(arm,dl,loss,len(rr))
 return {w:statistics.mean(num(r,'completion_fraction') for r in rr if r['world_seed']==w) for w in worlds}
def paired(x,y):
 worlds=sorted(x);assert worlds==sorted(y)
 diffs=[x[w]-y[w] for w in worlds];lo,hi=bootstrap(diffs)
 return 100*statistics.mean(diffs),100*lo,100*hi

def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 original=read(ROOT/'admission_primary/episodes.csv')
 no_wait=read(ROOT/'admission_no_settlement/episodes.csv')
 piped=read(ROOT/'settlement_overlap/episodes.csv')
 delay=read(ROOT/'delay_kernel_controls/episodes.csv')
 maxwait=read(ROOT/'fixed_mean_settlement/episodes.csv')
 grid=read(ROOT/'admission_priced_grid/paired_gaps.csv')
 assert len(original)==3456 and len(no_wait)==288 and len(piped)==288 and len(delay)==1152 and len(maxwait)==288
 # S1: complete 84 pairs (all conditions); only 4 negative means.
 s1=[dict(delay=float(r['delay']),deadline=float(r['deadline']),loss=float(r['loss']),n_pairs=int(r['episodes']),
          world_clusters=int(r['worlds']),claim_minus_permit_pp=float(r['gap_pp']),ci_low_pp=float(r['lo_pp']),ci_high_pp=float(r['hi_pp']),
          claim_better_worlds=int(r['worlds_claim_better']),permit_better_worlds=int(r['worlds_permit_better']),
          negative_mean=float(r['gap_pp'])<0,ci_excludes_zero=float(r['lo_pp'])*float(r['hi_pp'])>0)
     for r in grid if r['A']=='claim_redirect_remote_priced' and r['B']=='permit_redirect_remote']
 assert len(s1)==84
 write(out/'S1_complete_84_delay_deadline_contrasts.csv',s1)
 s2=[]
 for dl,loss in product(DEADLINES,LOSSES):
  C=by_world(original,dl,loss,'claim_redirect_remote_priced');
  P=by_world(original,dl,loss,'permit_redirect_remote')
  S=by_world(original,dl,loss,'claim_sticky_remote_priced');
  SP=by_world(original,dl,loss,'permit_sticky_remote')
  NW=by_world(no_wait,dl,loss,'claim_redirect_remote_priced_no_settlement')
  O=by_world(piped,dl,loss,'claim_redirect_remote_priced_pipelined')
  def pct(x):return 100*statistics.mean(x.values())
  seqg=paired(C,P);ow=paired(O,P);ng=paired(NW,P);sticky=paired(S,SP)
  s2.append(dict(deadline=dl,loss=loss,n_per_arm=36,
     redirect_claim_seq_pct=pct(C),redirect_claim_no_settlement_pct=pct(NW),redirect_claim_pipelined_pct=pct(O),redirect_permit_pct=pct(P),
     seq_minus_permit_pp=seqg[0],seq_ci_low_pp=seqg[1],seq_ci_high_pp=seqg[2],
     overlap_minus_permit_pp=ow[0],overlap_ci_low_pp=ow[1],overlap_ci_high_pp=ow[2],
     no_wait_minus_permit_pp=ng[0],no_wait_ci_low_pp=ng[1],no_wait_ci_high_pp=ng[2],
     sticky_claim_pct=pct(S),sticky_permit_pct=pct(SP),sticky_gap_pp=sticky[0],sticky_ci_low_pp=sticky[1],sticky_ci_high_pp=sticky[2]))
 write(out/'S2_full_8cell_settlement_and_sticky.csv',s2)
 # S3: deterministic controls; separate settlement and delay-model changes.
 s3=[]
 for dl,loss in product(DEADLINES,LOSSES):
  U=by_world(original,dl,loss,'claim_redirect_remote_priced');UP=by_world(original,dl,loss,'permit_redirect_remote')
  M={a:by_world([r for r in delay if float(r['delay'])==.65],dl,loss,a) for a in ('claim_redirect_remote_priced','permit_redirect_remote')}
  X={a:by_world([r for r in delay if float(r['delay'])==.95],dl,loss,a) for a in ('claim_redirect_remote_priced','permit_redirect_remote')}
  FM=by_world(maxwait,dl,loss,'claim_redirect_remote_priced_fixed_mean_full_settle')
  s3.append(dict(deadline=dl,loss=loss,n_pairs=36,
     main_uniform_U35_95_settle108_gap_pp=paired(U,UP)[0],
     fixed_mean_d65_settle78_gap_pp=paired(M['claim_redirect_remote_priced'],M['permit_redirect_remote'])[0],
     fixed_mean_d65_settle108_gap_pp=paired(FM,M['permit_redirect_remote'])[0],
     fixed_max_d95_settle108_gap_pp=paired(X['claim_redirect_remote_priced'],X['permit_redirect_remote'])[0]))
 write(out/'S3_delay_law_and_settlement_controls.csv',s3)
 negative=[r for r in s1 if r['negative_mean']]
 audit=dict(primary_rows=len(original),no_wait_rows=len(no_wait),new_overlap_rows=len(piped),new_delay_rows=len(delay),
            new_full_wait_rows=len(maxwait),complete_s1_conditions=len(s1),negative_grid_mean_cells=len(negative),
            negative_cells_with_interval_below_zero=sum(r['ci_high_pp']<0 for r in negative),
            ablation_cells=len(s2),delay_law_cells=len(s3),new_episodes=len(piped)+len(delay)+len(maxwait),
            source_design='Post-review exploratory; 12 previously reused generated worlds, three common seeds',
            uncertainty='Descriptive 4000-resample world-cluster intervals, not multiplicity adjusted')
 (out/'audit.json').write_text(json.dumps(audit,indent=2))
 print(json.dumps(audit,indent=2))
 return audit
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args();run(args.out)
