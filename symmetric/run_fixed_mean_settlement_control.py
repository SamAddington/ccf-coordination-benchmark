#!/usr/bin/env python3
"""Hold claim settlement to 1.08 while using fixed 0.65 one-hop delay.
The original main run uses U(.35,.95) with 1.08 settlement; the original grid
uses fixed d with (d+.13) settlement. This new control separates those choices
within the authored synthetic model, but does not isolate all event-order effects.
"""
from pathlib import Path
import argparse,csv,json,statistics
from itertools import product
from run_symmetric import WIS,SEEDS,LOSSES,DEADLINES,world
from run_admission import simulate,bootstrap
fields=['world_idx','world_seed','trial_seed','loss','deadline','delay','settlement','arm','completion_fraction','executed_actions','denied_formal_capacity','status','error']
def run(out,worlds=WIS,seeds=SEEDS):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[]
 for wi in worlds:
  w=world(wi)
  for seed,loss,dl in product(seeds,LOSSES,DEADLINES):
   r=dict(world_idx=wi,world_seed=w.seed,trial_seed=seed,loss=loss,deadline=dl,delay=.65,settlement=1.08,arm='claim_redirect_remote_priced_fixed_mean_full_settle')
   try:
    desc,rr=simulate(w,seed,'claim_redirect_remote_priced',loss,dl,delay=.65,settle_wait=1.08)
    r.update(rr);r.update(status='completed',error='')
   except Exception as e:r.update(status='failed',error=type(e).__name__+': '+str(e))
   rows.append(r)
 with (out/'episodes.csv').open('w',newline='') as f:
  wr=csv.DictWriter(f,fields,extrasaction='ignore');wr.writeheader();wr.writerows(rows)
 summ=[]
 for dl,loss in product(DEADLINES,LOSSES):
  rr=[r for r in rows if r['deadline']==dl and r['loss']==loss]
  wm=[statistics.mean(float(r['completion_fraction']) for r in rr if r['world_seed']==w) for w in sorted({r['world_seed'] for r in rr})]
  low,high=bootstrap(wm)
  summ.append(dict(deadline=dl,loss=loss,n=len(rr),mean=statistics.mean(wm),lo=low,hi=high))
 with (out/'summary.csv').open('w',newline='') as f:
  wr=csv.DictWriter(f,summ[0].keys());wr.writeheader();wr.writerows(summ)
 (out/'audit.json').write_text(json.dumps({'episodes':len(rows),'failures':sum(r['status']!='completed' for r in rows),'hop_delay':'fixed 0.65','settlement':'1.08 model units'},indent=2))
 print('DONE',len(rows),'failures',sum(r['status']!='completed' for r in rows))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args()
 run(a.out,WIS[:1] if a.smoke else WIS,SEEDS[:1] if a.smoke else SEEDS)
