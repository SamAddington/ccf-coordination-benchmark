#!/usr/bin/env python3
"""Separate same-host numerical recomputation and deterministic source replay of v26 data."""
import csv,json,sys,random,statistics,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from run_fair_comparison import simulate,WIS,SEEDS,ARMS,LOSSES,HORIZONS
from ccf_eventlab.model import world_factory

def read(path):return list(csv.DictReader(open(path,newline='')))

def verify():
 a=read(ROOT/'results'/'episodes.csv');b=read(ROOT/'sensitivity_results'/'episodes.csv')
 old=read(ROOT.parent/'v25'/'results'/'episodes.csv')
 assert len(a)==2592 and len(b)==1680 and len(old)==4320
 assert all(x['status']=='completed' for x in a+b+old)
 assert json.loads((ROOT/'results'/'failures.json').read_text()) == []
 keys={(x['world_seed'],x['trial_seed'],x['loss'],x['horizon'],x['arm']) for x in a}
 assert len(keys)==len(a)
 assert {x['world_seed'] for x in a}.isdisjoint({x['world_seed'] for x in old})
 assert all(float(x['overcapacity_admissions'])==0 for x in a+b)
 bycond=collections.defaultdict(list)
 for x in a:bycond[(x['horizon'],x['loss'],x['arm'])].append(x)
 assert len(bycond)==72 and all(len(v)==36 for v in bycond.values())
 s=json.loads((ROOT/'results'/'summary.json').read_text())
 for v in s:
  k=(str(v['horizon']),str(v['loss']),v['arm'])
  # JSON writes float, source strings use 16.0/0.0 etc
  rr=bycond[k]
  assert abs(statistics.mean(float(x['completion_fraction']) for x in rr)-float(v['completion_fraction']))<1e-12
  assert abs(statistics.mean(float(x['total_messages']) for x in rr)-float(v['total_messages']))<1e-9
 # Rerun a stratified deterministic sample from all nine configurations
 R=random.Random(26)
 sample=[]
 for arm in ARMS:
  pool=[x for x in a if x['arm']==arm]
  sample += R.sample(pool,3)
 for x in sample:
  # Original world index reconstruct from seed; all use i in 220..231
  wi=(int(x['world_seed'])-170123)//23
  w=world_factory(int(x['world_seed']),('small','medium','large')[wi%3])
  result=simulate(w,int(x['trial_seed']),x['arm'],float(x['loss']),float(x['horizon']))
  for field in ('completed_tasks','task_total','overcapacity_admissions','total_messages','delivery_losses','disruptions'):
   assert abs(float(result.get(field,0))-float(x.get(field,0) or 0))<1e-8,(field,x['arm'],x['world_seed'])
 # sensitivity indexes, tests and counts
 counts=collections.Counter(x['study'] for x in b)
 assert counts=={'low_loss':576,'ttl':288,'claim_timer':288,'scale_16agents':288,'bursty_loss':240},counts
 assert all(x['status']=='completed' for x in b)
 # Original set has 40 cells 108 rows each (3 arms per 36 matches)
 old_cells=collections.Counter((x['horizon'],x['loss'],x['shield'],x['physics']) for x in old)
 assert len(old_cells)==40 and set(old_cells.values())=={108}
 audit={'pass':True,'v25_original_episodes':len(old),'v25_factor_cells':len(old_cells),
        'v26_primary_episodes':len(a),'primary_condition_cells':len(bycond),
        'primary_repetitions_per_cell':36,'v26_sensitivity_episodes':len(b),
        'primary_source_replays':len(sample),'fields_per_replay':6,
        'cross_host_reproduction':False,'independent_human_reproduction':False}
 (ROOT/'verification.json').write_text(json.dumps(audit,indent=2))
 print(json.dumps(audit,indent=2))
 return audit
if __name__=='__main__':verify()
