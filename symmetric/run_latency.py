#!/usr/bin/env python3
"""Exploratory crossover sensitivity: deterministic per-hop latency and deadline.

Use the same 12 worlds/3 trials as v26 to isolate one modeled parameter; no
claim of physical network timing or preregistration. For d>0 the claim family
adds 0.13 after one-hop maximum; permits wait for the request/grant exchange.
"""
import argparse,csv,json,statistics,random,time,sys
from pathlib import Path
from collections import defaultdict
from itertools import product
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_symmetric import WIS,SEEDS,world,simulate
DELAYS=(0.,.10,.25,.50,.95,1.30,1.80)
DEADLINES=(8.,12.,16.,24.,36.,54.)
LOSSES=(0.,.20)
ARMS=('claim_redirect_remote','permit_redirect_remote')
FIELDS=['world_idx','world_seed','trial_seed','loss','deadline','per_hop_delay','settlement_extra','arm','completion_fraction','completed_tasks','executed_actions','duplicate_starts','denied_formal_capacity','total_messages','delivery_losses','permit_mean_acquisition_wait','status','error']

def run(out,smoke=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    rows=[];t0=time.monotonic()
    for wi in (WIS[:1] if smoke else WIS):
        w=world(wi)
        for seed,loss,deadline,delay,arm in product(SEEDS[:1] if smoke else SEEDS,LOSSES,DEADLINES,DELAYS,ARMS):
            rec={'world_idx':wi,'world_seed':w.seed,'trial_seed':seed,'loss':loss,'deadline':deadline,'per_hop_delay':delay,
                 'settlement_extra':0. if delay==0 else .13,'arm':arm}
            try:
                _,result=simulate(w,seed,arm,loss,deadline,delay_min=delay,delay_max=delay,settlement=0. if delay==0 else .13)
                rec.update(result);rec.update(status='completed',error='')
            except Exception as e:rec.update(status='failed',error=f'{type(e).__name__}: {e}')
            rows.append(rec)
        print('delay sweep world',wi,'rows',len(rows),'secs',round(time.monotonic()-t0,1),flush=True)
    with open(out/'episodes.csv','w',newline='') as f:
        z=csv.DictWriter(f,FIELDS,extrasaction='ignore');z.writeheader();z.writerows(rows)
    fail=[z for z in rows if z['status']!='completed'];(out/'failures.json').write_text(json.dumps(fail,indent=2))
    from analyze_latency import analyze
    analyze(out)
    print('DONE',len(rows),'fails',len(fail),'secs',round(time.monotonic()-t0,1),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    run(a.out,a.smoke)
