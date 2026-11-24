#!/usr/bin/env python3
"""Post-review, exploratory, new-seed loss sweep of archived v15 engine.

No optimization or retuning after looking at results. All attempted episodes saved.
"""
import sys,os,random,statistics,csv,json,traceback,hashlib
from pathlib import Path
from collections import defaultdict
from itertools import product
SRC=Path(__file__).parent/'source'/'CCF_v15_Reproduction_Candidate_20261123'
sys.path.insert(0,str(SRC))
from ccf_eventlab.model import world_factory
from ccf_eventlab.engine import RunConfig
from v12.distributed_lease import AccountedDRA,DistributedLeaseEngine
from v14.distributed_capacity import DistributedCapacitySemaphoreEngine

ARMS=('dra','distributed_lease','distributed_capacity')
GUARDS=('formal_capacity','ncp')
LAWS=('reference','no_overcapacity_penalty')
LOSSES=(0.0,.05,.10,.20,.35)
HORIZONS=(16.0,54.0)
WIS=tuple(range(100,112))
TRIALS=(60100,60101,60102)
SCHEMA=('world_id','world_seed','scale','trial_seed','controller','shield','physics','horizon','loss','delay_min','delay_max','status','error',
 'completion_fraction','completed_tasks','task_total','disruptions','overcapacity_admissions','total_messages','delivery_losses','lease_requests','lease_request_retries','lease_denials','lease_stale_grants','permit_mean_acquisition_wait','permit_issued','censored_active_actions')

def simulate(w,seed,arm,guard,law,horizon,loss):
 cfg=RunConfig('dra' if arm=='dra' else 'independent', guard, horizon=horizon,delay_min=.35,delay_max=.95,message_loss=loss)
 cls={'dra':AccountedDRA,'distributed_lease':DistributedLeaseEngine,'distributed_capacity':DistributedCapacitySemaphoreEngine}[arm]
 return cls(w,cfg,seed,controller=arm,physics=law,release_profile='all_at_start').run()

def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 rows=[]
 # assertions and retry semantics are in the unchanged archived source; all results tagged exploratory
 for wi in WIS:
  w=world_factory(170123+wi*23,('small','medium','large')[wi%3]);fail=0
  for seed,loss,horizon,guard,law,arm in product(TRIALS,LOSSES,HORIZONS,GUARDS,LAWS,ARMS):
   r=dict(world_id=w.id,world_seed=w.seed,scale=w.id.split('-')[0],trial_seed=seed,controller=arm,shield=guard,physics=law,horizon=horizon,loss=loss,delay_min=.35,delay_max=.95)
   try:
    r.update(simulate(w,seed,arm,guard,law,horizon,loss));r.update(status='completed',error='')
   except Exception as ex:
    r.update(status='failed',error=f'{type(ex).__name__}:{ex}');fail+=1
   rows.append(r)
  print(f'world={wi} episodes={len(rows)} failures_in_world={fail}',flush=True)
 with open(out/'episodes.csv','w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=SCHEMA,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
 with open(out/'failures.json','w') as f:json.dump([r for r in rows if r['status']!='completed'],f,indent=2)
 conditions=defaultdict(dict)
 for r in rows:
  k=(r['world_seed'],r['trial_seed'],r['loss'],r['horizon'],r['shield'],r['physics'])
  assert r['controller'] not in conditions[k]
  conditions[k][r['controller']]=r
 assert len(rows)==4320 and len(conditions)==1440
 assert all(set(d)==set(ARMS) for d in conditions.values())
 def clboot(xs):
  xs=list(xs);b=random.Random(1227)
  values=sorted(statistics.mean([xs[b.randrange(len(xs))] for _ in xs]) for z in range(4000))
  return [round(values[99],5),round(values[3899],5)]
 summary=[]
 for loss,horizon,guard,law in product(LOSSES,HORIZONS,GUARDS,LAWS):
  matches=[(k,v) for k,v in conditions.items() if k[2:]==(loss,horizon,guard,law)]
  n_failed=sum(any(z['status']!='completed' for z in v.values()) for k,v in matches)
  d=dict(loss=loss,horizon=horizon,guard=guard,physics=law,blocks=len(matches),failed_blocks=n_failed)
  if n_failed==0:
   for a in ARMS:
    for field in ('completion_fraction','disruptions','overcapacity_admissions','total_messages','delivery_losses','lease_request_retries'):
     d[a+'_'+field]=round(statistics.mean(float(v[a].get(field,0) or 0) for k,v in matches),6)
   for a,b in [('dra','distributed_capacity'),('dra','distributed_lease'),('distributed_capacity','distributed_lease')]:
    byworld=defaultdict(list)
    for k,v in matches:
     byworld[k[0]].append(100*(float(v[a]['completion_fraction'])-float(v[b]['completion_fraction'])))
    means=[statistics.mean(z) for w,z in sorted(byworld.items())]
    d[a+'_minus_'+b+'_completion_pp']=round(statistics.mean(means),5)
    d[a+'_minus_'+b+'_world_cluster95_pp']=clboot(means)
  summary.append(d)
 with open(out/'summary.json','w') as f:json.dump(summary,f,indent=2)
 with open(out/'summary.csv','w',newline='') as f:
  cols=sorted(set().union(*(r.keys() for r in summary)))
  writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows({k:(json.dumps(v) if isinstance(v,list) else v) for k,v in r.items()} for r in summary)
 status={'planned_attempts':4320,'actual_attempts':len(rows),'matched_three_way_blocks':len(conditions),'new_worlds':len(WIS),'trials_per_world':3,'failed_executions':sum(r['status']!='completed' for r in rows),'design':'post-review exploratory, not public preregistration','source_sha256':{x:hashlib.sha256((SRC/x).read_bytes()).hexdigest() for x in ('v12/distributed_lease.py','v14/distributed_capacity.py','ccf_eventlab/model.py','ccf_eventlab/engine.py','experiment_common.py')},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 with open(out/'audit.json','w') as f:json.dump(status,f,indent=2)
 print('DONE',json.dumps(status,indent=2),flush=True)
 return summary
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else '/mnt/data/ccf_revision/results')
