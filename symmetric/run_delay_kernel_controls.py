#!/usr/bin/env python3
"""Controlled model-law comparison: uniform hop-delay versus fixed hop-delay.
The fixed-delay arms use the same world/seed/deadline/loss grid, with d=0.65
(uniform mean) or d=0.95 (uniform maximum). No physical network claim.
"""
from __future__ import annotations
import csv,json,statistics,argparse
from pathlib import Path
from itertools import product
from run_symmetric import WIS,SEEDS,LOSSES,DEADLINES,world
from run_admission import simulate,bootstrap

FIELDS=['world_idx','world_seed','trial_seed','loss','deadline','delay_model','delay','arm','completion_fraction',
        'executed_actions','denied_formal_capacity','guard_wire_messages','total_messages','status','error']

def run(out,worlds=WIS,seeds=SEEDS):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[]
 for wi in worlds:
  w=world(wi)
  for seed,lo,dl,d,arm in product(seeds,LOSSES,DEADLINES,(.65,.95),
                                   ('claim_redirect_remote_priced','permit_redirect_remote')):
   r=dict(world_idx=wi,world_seed=w.seed,trial_seed=seed,loss=lo,deadline=dl,delay_model='fixed',delay=d,arm=arm)
   try:
    desc,ans=simulate(w,seed,arm,lo,dl,delay=d)
    r.update(ans);r.update(status='completed',error='')
   except Exception as ex:r.update(status='failed',error=type(ex).__name__+': '+str(ex))
   rows.append(r)
  print('world',wi,flush=True)
 with (out/'episodes.csv').open('w',newline='') as f:
  wr=csv.DictWriter(f,FIELDS,extrasaction='ignore');wr.writeheader();wr.writerows(rows)
 summary=[]
 for dl,lo,d,arm in product(DEADLINES,LOSSES,(.65,.95),('claim_redirect_remote_priced','permit_redirect_remote')):
  rr=[r for r in rows if r['deadline']==dl and r['loss']==lo and r['delay']==d and r['arm']==arm]
  vals=[statistics.mean(float(r['completion_fraction']) for r in rr if r['world_seed']==w) for w in sorted({r['world_seed'] for r in rr})]
  low,high=bootstrap(vals)
  summary.append(dict(deadline=dl,loss=lo,delay=d,arm=arm,n=len(rr),completion=statistics.mean(vals),lo=low,hi=high))
 with (out/'summary.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,summary[0].keys());w.writeheader();w.writerows(summary)
 (out/'audit.json').write_text(json.dumps({'episodes':len(rows),'failures':sum(r['status']!='completed' for r in rows),
      'model':'fixed d 0.65 (uniform mean) vs fixed d 0.95 (uniform upper bound); synthetic only'},indent=2))
 print('DONE',len(rows),'failures',sum(r['status']!='completed' for r in rows),flush=True)
 return rows,summary
if __name__=='__main__':
 pa=argparse.ArgumentParser();pa.add_argument('--out',required=True);pa.add_argument('--smoke',action='store_true');args=pa.parse_args()
 run(args.out,WIS[:1] if args.smoke else WIS,SEEDS[:1] if args.smoke else SEEDS)
