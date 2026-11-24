#!/usr/bin/env python3
"""New v26 exploratory fairness experiment. Full attempts retained, no pruning."""
import sys, os, csv, json, hashlib, random, statistics, time
from pathlib import Path
from itertools import product
from collections import defaultdict
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/'v25'/'source'/'CCF_v15_Reproduction_Candidate_20261123'
sys.path.insert(0,str(SRC));sys.path.insert(0,str(ROOT))
from ccf_eventlab.model import world_factory
from ccf_eventlab.engine import RunConfig
from experiment_common import ExperimentEngine
from v12.distributed_lease import AccountedDRA
from v14.distributed_capacity import DistributedCapacitySemaphoreEngine
from fair_engines import FallbackCapacity,ColocatedCapacity,ColocatedFallback,RemoteGuardDRA,RemoteGuardIndependent

ARMS=('claim_local','claim_remote','independent_local','independent_remote',
      'permit_sticky','permit_fallback','permit_fallback_retx','permit_colocated','permit_colocated_fallback')
WIS=tuple(range(220,232)) # no overlap with v25 worlds (100..111)
SEEDS=(71011,71012,71013)
LOSSES=(0.0,0.05,0.20,0.35)
HORIZONS=(16.0,54.0)
FIELDS=('world_id','world_seed','world_scale','agents','trial_seed','arm','loss','horizon','guard','physics',
 'status','error','completion_fraction','completed_tasks','task_total','total_messages','delivery_losses',
 'disruptions','overcapacity_admissions','duplicate_starts','executed_actions','lease_requests',
 'lease_request_retries','lease_denials','lease_stale_grants','lease_release_messages',
 'permit_issued','permit_mean_acquisition_wait','fallback_switches','fallback_busy_switches',
 'fallback_timeout_switches','fallback_cancel_messages','fallback_late_grant_releases',
 'release_retransmissions','guard_requests','guard_reply_sent','guard_timeouts',
 'guard_delivery_losses','guard_wire_messages','manager_colocated','censored_active_actions')

def simulate(world,seed,arm,loss,horizon):
    is_dra=arm.startswith('claim')
    cfg=RunConfig('dra' if is_dra else 'independent','formal_capacity',horizon=horizon,
            delay_min=.35,delay_max=.95,message_loss=loss)
    common={'physics':'reference','release_profile':'all_at_start'}
    if arm=='claim_local':return AccountedDRA(world,cfg,seed,controller='dra',**common).run()
    if arm=='claim_remote':return RemoteGuardDRA(world,cfg,seed,controller='dra',**common).run()
    if arm=='independent_local':return ExperimentEngine(world,cfg,seed,controller='independent',**common).run()
    if arm=='independent_remote':return RemoteGuardIndependent(world,cfg,seed,**common).run()
    if arm=='permit_sticky':return DistributedCapacitySemaphoreEngine(world,cfg,seed,controller='distributed_capacity',**common).run()
    if arm=='permit_fallback':return FallbackCapacity(world,cfg,seed,controller='distributed_capacity',fallback_after=1,**common).run()
    if arm=='permit_fallback_retx':return FallbackCapacity(world,cfg,seed,controller='distributed_capacity',fallback_after=1,release_replays=2,**common).run()
    if arm=='permit_colocated':return ColocatedCapacity(world,cfg,seed,controller='distributed_capacity',**common).run()
    if arm=='permit_colocated_fallback':return ColocatedFallback(world,cfg,seed,controller='distributed_capacity',fallback_after=1,**common).run()
    raise ValueError(arm)

def run(out, world_idx=WIS, arms=ARMS, seed_list=SEEDS):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=[];t0=time.time()
    for wi in world_idx:
        world=world_factory(170123+wi*23,('small','medium','large')[wi%3])
        failures=0
        for seed,loss,horizon,arm in product(seed_list,LOSSES,HORIZONS,arms):
            rec=dict(world_id=world.id,world_seed=world.seed,world_scale=('small','medium','large')[wi%3],agents=world.num_agents,
                     trial_seed=seed,arm=arm,loss=loss,horizon=horizon,guard='local_atomic',physics='reference')
            try:
                result=simulate(world,seed,arm,loss,horizon)
                rec.update(result);rec.update(status='completed',error='')
            except Exception as e:
                rec.update(status='failed',error=type(e).__name__+':'+str(e));failures+=1
            rows.append(rec)
        print('world',wi,'attempts',len(rows),'fails',failures,'elapsed',round(time.time()-t0,1),flush=True)
    with open(out/'episodes.csv','w',newline='') as f:
        w=csv.DictWriter(f,FIELDS,extrasaction='ignore');w.writeheader();w.writerows(rows)
    with open(out/'failures.json','w') as f:json.dump([r for r in rows if r['status']!='completed'],f,indent=2)
    bycond=defaultdict(list)
    for r in rows:bycond[(r['loss'],r['horizon'],r['arm'])].append(r)
    summary=[]
    for loss,horizon,arm in product(LOSSES,HORIZONS,arms):
        rr=bycond[(loss,horizon,arm)]
        sr=dict(loss=loss,horizon=horizon,arm=arm,attempts=len(rr),failed=sum(r['status']!='completed' for r in rr))
        complete=[r for r in rr if r['status']=='completed']
        if len(complete)==len(rr):
            for k in ('completion_fraction','overcapacity_admissions','total_messages','delivery_losses','lease_requests','lease_request_retries','fallback_switches','guard_wire_messages','guard_timeouts','disruptions'):
                sr[k]=statistics.mean(float(r.get(k) or 0) for r in complete)
            byworld=defaultdict(list)
            for r in complete:byworld[r['world_seed']].append(float(r['completion_fraction']))
            means=[statistics.mean(z) for _,z in sorted(byworld.items())]
            b=random.Random(90210);boots=sorted(statistics.mean([means[b.randrange(len(means))] for _ in means]) for _ in range(3000))
            sr['world_cluster95']=[boots[74],boots[2924]]
        summary.append(sr)
    with open(out/'summary.json','w') as f:json.dump(summary,f,indent=2)
    with open(out/'summary.csv','w',newline='') as f:
        keys=sorted(set().union(*(s.keys() for s in summary)))
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:json.dumps(v) if isinstance(v,list) else v for k,v in s.items()} for s in summary)
    meta={'actual_attempts':len(rows),'planned_attempts':len(world_idx)*len(seed_list)*len(LOSSES)*len(HORIZONS)*len(arms),
      'completed':sum(r['status']=='completed' for r in rows),'failure_count':sum(r['status']=='failed' for r in rows),
      'worlds':len(world_idx),'seeds':len(seed_list),'arms':list(arms),'losses':LOSSES,'horizons':HORIZONS,
      'source_sha256':{x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in [str(ROOT/'fair_engines.py'),str(__file__)]},
      'study':'post-review exploratory; not independently preregistered; same original generator; new seeds'}
    (out/'audit.json').write_text(json.dumps(meta,indent=2))
    print('DONE',json.dumps(meta,indent=2),flush=True)
    return summary

if __name__=='__main__':
    subset=os.getenv('SMOKE')
    if subset:run(sys.argv[1],world_idx=WIS[:1],seed_list=SEEDS[:1])
    else:run(sys.argv[1] if len(sys.argv)>1 else ROOT/'results')
