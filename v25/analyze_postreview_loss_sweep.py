"""Independent (separately written) reanalysis of complete post-review sweep CSV.
Uses only the frozen attempted-episode CSV, not the simulation execution classes.
"""
import csv,json,statistics,random,sys
from pathlib import Path
from collections import defaultdict
from itertools import product
ARMS=('dra','distributed_lease','distributed_capacity');FIELDS=['completion_fraction','disruptions','overcapacity_admissions','total_messages','delivery_losses','lease_request_retries']
LOSSES=(0.,.05,.10,.20,.35);HORIZONS=(16.,54.);GUARDS=('formal_capacity','ncp');PHYSICS=('reference','no_overcapacity_penalty')

def main(dir):
 d=Path(dir)
 with open(d/'episodes.csv') as f:rows=list(csv.DictReader(f))
 assert len(rows)==4320,len(rows)
 assert not [r for r in rows if r['status']!='completed']
 groups=defaultdict(dict)
 for r in rows:
  key=(r['world_seed'],r['trial_seed'],float(r['loss']),float(r['horizon']),r['shield'],r['physics'])
  assert r['controller'] not in groups[key]
  groups[key][r['controller']]=r
 assert len(groups)==1440
 assert all(set(v)==set(ARMS) for v in groups.values())
 assert len({k[0] for k in groups})==12
 def boot(means):
  rng=random.Random(1723)
  arr=sorted(statistics.mean(rng.choices(means,k=len(means))) for j in range(4000))
  return [round(arr[99],4),round(arr[3899],4)]
 summaries=[]
 for loss,horizon,guard,physics in product(LOSSES,HORIZONS,GUARDS,PHYSICS):
  pairs=[(k,v) for k,v in groups.items() if k[2:]==(loss,horizon,guard,physics)]
  assert len(pairs)==36
  o={'loss':loss,'horizon':horizon,'guard':guard,'physics':physics,'blocks':len(pairs),'worlds':12}
  for arm in ARMS:
   for field in FIELDS:
    vals=[float(v[arm].get(field,0) or 0) for _,v in pairs]
    o[f'{arm}_{field}']=round(statistics.mean(vals),6)
  for arm in ('distributed_lease','distributed_capacity'):
   for field in ('completion_fraction','total_messages'):
    byworld=defaultdict(list)
    for k,v in pairs:
     byworld[k[0]].append((float(v['dra'][field])-float(v[arm][field]))*(100 if field=='completion_fraction' else 1))
    means=[statistics.mean(z) for z in byworld.values()]
    o[f'dra_minus_{arm}_{field}']=round(statistics.mean(means),4)
    o[f'dra_minus_{arm}_{field}_world95']=boot(means)
  summaries.append(o)
 with open(d/'summary_by_cell.json','w') as f:json.dump(summaries,f,indent=2)
 with open(d/'summary_by_cell.csv','w',newline='') as f:
  cols=sorted(set().union(*(r.keys() for r in summaries)))
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()} for row in summaries)
 s={'source':'only episodes.csv','planned_attempts':4320,'actual_attempts':len(rows),'matched_threeway_blocks':len(groups),'world_count':12,'trial_seeds_per_world':3,'failed_executions':0,'condition_cells':len(summaries),'analysis_status':'pass','external_research_pre_registration':False,'guard':'shared local atomic (unpriced) or reactive NCP; no remote guard cost'}
 (d/'audit.json').write_text(json.dumps(s,indent=2))
 for loss in LOSSES:
  r=next(x for x in summaries if x['loss']==loss and x['horizon']==54 and x['guard']=='formal_capacity' and x['physics']=='reference')
  print('loss',loss,'DRA',round(100*r['dra_completion_fraction'],2),'sem',round(100*r['distributed_capacity_completion_fraction'],2),'lease',round(100*r['distributed_lease_completion_fraction'],2),'DRA-sem diff',r['dra_minus_distributed_capacity_completion_fraction'],'95% world',r['dra_minus_distributed_capacity_completion_fraction_world95'])
 print('AUDIT',s)
if __name__=='__main__':main(sys.argv[1])
