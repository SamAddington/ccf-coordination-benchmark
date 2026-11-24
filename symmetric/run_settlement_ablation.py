#!/usr/bin/env python3
"""Exploratory no-settlement claim test: keeps service-side two-hop admission.
A simulated advisory claim may attempt service admission immediately; this
changes coordination behavior and is NOT the primary delayed-settlement claim.
"""
from __future__ import annotations
import csv,json,statistics,sys,argparse
from pathlib import Path
from itertools import product
from collections import defaultdict
from run_symmetric import WIS,SEEDS,LOSSES,DEADLINES,world
from run_admission import simulate,bootstrap
FIELDS=['world_idx','world_seed','trial_seed','loss','deadline','arm','net_settlement_wait',
        'completion_fraction','denied_formal_capacity','duplicate_starts','guard_wire_messages','total_messages',
        'overcapacity_admissions','status','error']

def run(out,world_indices=WIS,seed_list=SEEDS):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for wi in world_indices:
        w=world(wi)
        for seed,loss,deadline in product(seed_list,LOSSES,DEADLINES):
            r=dict(world_idx=wi,world_seed=w.seed,trial_seed=seed,loss=loss,deadline=deadline,arm='claim_redirect_remote_priced_no_settlement',net_settlement_wait=0.)
            try:
                desc,ans=simulate(w,seed,'claim_redirect_remote_priced',loss,deadline,settle_wait=0.)
                r.update(ans);r.update(status='completed',error='')
            except Exception as e:r.update(status='failed',error=str(e))
            rows.append(r)
    with open(out/'episodes.csv','w',newline='') as f:
        wr=csv.DictWriter(f,FIELDS,extrasaction='ignore');wr.writeheader();wr.writerows(rows)
    (out/'failures.json').write_text(json.dumps([r for r in rows if r['status']!='completed'],indent=2))
    result=[]
    for dl,lo in product(DEADLINES,LOSSES):
        rr=[r for r in rows if r['deadline']==dl and r['loss']==lo]
        means=[statistics.mean(float(r['completion_fraction']) for r in rr if r['world_seed']==w) for w in sorted({r['world_seed'] for r in rr})]
        ci=bootstrap(means)
        result.append(dict(deadline=dl,loss=lo,episodes=len(rr),completion_fraction=statistics.mean(float(r['completion_fraction']) for r in rr),lo=ci[0],hi=ci[1],
                           denials=statistics.mean(float(r.get('denied_formal_capacity') or 0) for r in rr)))
    with open(out/'summary.csv','w',newline='') as f:
        wr=csv.DictWriter(f,result[0].keys());wr.writeheader();wr.writerows(result)
    (out/'audit.json').write_text(json.dumps({'episodes':len(rows),'failures':sum(r['status']!='completed' for r in rows),
                              'method':'No wait after remote claim publication, followed by remote service guard RPC; sensitivity only'},indent=2))
    print('DONE',len(rows),'failures',sum(r['status']!='completed' for r in rows))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    s=run(a.out,WIS[:1] if a.smoke else WIS,SEEDS[:1] if a.smoke else SEEDS)
    for r in s:print(r)
