#!/usr/bin/env python3
"""Standard-library-only recalculation of all 72 CCF v26 interval cells and
56 paired world-cluster contrasts from the supplied complete primary CSV.
"""
import argparse,csv,collections,json,math,random,statistics
from pathlib import Path
ARMS=('claim_local','claim_remote','independent_local','independent_remote',
      'permit_sticky','permit_fallback','permit_fallback_retx','permit_colocated','permit_colocated_fallback')
LOSS=(0.,.05,.20,.35)
CONTRAST=(('claim_local','permit_sticky'),('claim_local','permit_fallback'),
          ('claim_local','permit_colocated_fallback'),('claim_remote','permit_fallback'),
          ('permit_fallback','permit_sticky'),('permit_colocated_fallback','permit_fallback'),
          ('claim_local','independent_local'))
def load(p):
 with open(p,newline='',encoding='utf8') as f:return list(csv.DictReader(f))
def bootstrap(v,n=4000):
 rng=random.Random(2602);m=len(v)
 z=sorted(statistics.mean([v[rng.randrange(m)] for _ in v]) for _ in range(n))
 return z[99],z[3899]
def close(a,b):
 return math.isclose(float(a),float(b),abs_tol=1e-8,rel_tol=1e-10)
def verify(episodes, refcells, refcontrasts):
 rows=load(episodes); assert len(rows)==2592,len(rows)
 bycond=collections.defaultdict(list)
 for r in rows:bycond[(float(r['horizon']),float(r['loss']),r['arm'])].append(r)
 assert len(bycond)==72 and all(len(v)==36 for v in bycond.values()),'Bad condition grid'
 expected_cells=load(refcells);assert len(expected_cells)==72
 compare_count=0
 for x in expected_cells:
  h=float(x['horizon']);l=float(x['loss']);a=x['arm'];rr=bycond[(h,l,a)]
  byworld=collections.defaultdict(list)
  for r in rr:byworld[r['world_seed']].append(100*float(r['completion_fraction']))
  means=[statistics.mean(v) for _,v in sorted(byworld.items())]
  lo,hi=bootstrap(means)
  calc={'mean_completion_pct':statistics.mean(100*float(r['completion_fraction']) for r in rr),
        'lo95_pct':lo,'hi95_pct':hi,
        'mean_transmissions':statistics.mean(float(r['total_messages']) for r in rr),
        'mean_delivered_losses':statistics.mean(float(r['delivery_losses']) for r in rr),
        'overcapacity_total':sum(float(r['overcapacity_admissions']) for r in rr),
        'worlds':12,'episodes':36}
  for k,v in calc.items():
   assert close(v,x[k]),(h,l,a,k,v,x[k]);compare_count+=1
 expected_c=load(refcontrasts);assert len(expected_c)==56
 for x in expected_c:
  h=float(x['horizon']);l=float(x['loss']);a=x['first'];b=x['second']
  ai={(r['world_seed'],r['trial_seed']):float(r['completion_fraction']) for r in bycond[(h,l,a)]}
  bi={(r['world_seed'],r['trial_seed']):float(r['completion_fraction']) for r in bycond[(h,l,b)]}
  assert ai.keys()==bi.keys()
  world=collections.defaultdict(list)
  for (w,s),v in ai.items():world[w].append(100*(v-bi[(w,s)]))
  vals=[statistics.mean(v) for _,v in sorted(world.items())]
  lo,hi=bootstrap(vals)
  for k,v in {'mean_pp':statistics.mean(vals),'lo95_pp':lo,'hi95_pp':hi}.items():
   assert close(v,x[k]),(h,l,a,b,k,v,x[k]);compare_count+=1
 return {'pass':True,'episodes':len(rows),'complete_cells':len(expected_cells),
         'paired_contrasts':len(expected_c),'statistic_values_checked':compare_count,
         'bootstrap_unit':'world','seed':2602,'draws':4000}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--episodes',type=Path,required=True)
 p.add_argument('--cells',type=Path,required=True)
 p.add_argument('--contrasts',type=Path,required=True)
 args=p.parse_args();print(json.dumps(verify(args.episodes,args.cells,args.contrasts),indent=2))
