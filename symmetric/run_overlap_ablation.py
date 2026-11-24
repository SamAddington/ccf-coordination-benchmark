#!/usr/bin/env python3
"""Replicate 8 published loss×deadline cells with concurrent settlement/RPC.
Exploratory, paired with frozen study worlds/seeds, no deployment claims.
"""
from __future__ import annotations
import argparse,csv,json,statistics,sys,time
from pathlib import Path
from itertools import product
from run_symmetric import WIS,SEEDS,LOSSES,DEADLINES,world
from run_admission import simulate,bootstrap
from ccf_eventlab.engine import RunConfig
from pipelined_admission import PipelinedClaimAdmission

FIELDS=['world_idx','world_seed','trial_seed','loss','deadline','arm','status','error',
        'completion_fraction','executed_actions','duplicate_starts','denied_formal_capacity',
        'overcapacity_admissions','total_messages','guard_wire_messages','guard_requests',
        'guard_timeouts','pipeline_completed','pipeline_early_replies','pipeline_timeouts',
        'pipeline_claim_preemptions','pipeline_cancelled','pipeline_done_cancel']

def simulate_overlap(w,seed,loss,deadline):
    cfg=RunConfig('dra','formal_capacity',horizon=float(deadline),message_loss=loss,
                  delay_min=.35,delay_max=.95,settle_extra=.13)
    eng=PipelinedClaimAdmission(w,cfg,seed,free_plane=False,sticky=False,
                               physics='reference',release_profile='all_at_start')
    return eng.run()

def run(out, indices=WIS, seeds=SEEDS):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    rr=[];t0=time.monotonic()
    for wi in indices:
        w=world(wi)
        for seed,loss,deadline in product(seeds,LOSSES,DEADLINES):
            x={'world_idx':wi,'world_seed':w.seed,'trial_seed':seed,'loss':loss,'deadline':deadline,
               'arm':'claim_redirect_remote_priced_pipelined'}
            try:
                x.update(simulate_overlap(w,seed,loss,deadline));x.update(status='completed',error='')
            except Exception as e:x.update(status='failed',error=type(e).__name__+': '+str(e))
            rr.append(x)
        print('world',wi,'rows',len(rr),'elapsed',round(time.monotonic()-t0,2),flush=True)
    with (out/'episodes.csv').open('w',newline='') as f:
        cw=csv.DictWriter(f,FIELDS,extrasaction='ignore');cw.writeheader();cw.writerows(rr)
    fail=[x for x in rr if x['status']!='completed']
    (out/'failures.json').write_text(json.dumps(fail,indent=2))
    ss=[]
    for dl,loss in product(DEADLINES,LOSSES):
        x=[r for r in rr if r['deadline']==dl and r['loss']==loss]
        wm=[statistics.mean(float(r['completion_fraction']) for r in x if r['world_seed']==v)
            for v in sorted({r['world_seed'] for r in x})]
        ci=bootstrap(wm)
        ss.append(dict(deadline=dl,loss=loss,episodes=len(x),failures=sum(r['status']!='completed' for r in x),
            mean=statistics.mean(float(r['completion_fraction']) for r in x),lo=ci[0],hi=ci[1],
            denials=statistics.mean(float(r.get('denied_formal_capacity') or 0) for r in x),
            timeouts=statistics.mean(float(r.get('pipeline_timeouts') or 0) for r in x)))
    with (out/'summary.csv').open('w',newline='') as f:
        cw=csv.DictWriter(f,ss[0].keys());cw.writeheader();cw.writerows(ss)
    (out/'audit.json').write_text(json.dumps({'episodes':len(rr),'failures':len(fail),'cells':len(ss),
       'method':'guard RPC overlaps settlement; actual start waits for both; capacity checked only at action start; same 12 previously used worlds'},indent=2))
    print('DONE',len(rr),'failures',len(fail),flush=True)
    return rr,ss

if __name__=='__main__':
    pa=argparse.ArgumentParser();pa.add_argument('--out',required=True);pa.add_argument('--smoke',action='store_true');args=pa.parse_args()
    run(args.out,WIS[:1] if args.smoke else WIS,SEEDS[:1] if args.smoke else SEEDS)
