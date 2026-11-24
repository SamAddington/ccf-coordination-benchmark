#!/usr/bin/env python3
"""Synthetic 2x2x2 family x client policy x control plane, plus two floors.

Exploratory: prepared following reviewer feedback; not preregistered.
No source modification to the v26 baseline and no field deployment.
"""
from __future__ import annotations
import argparse,csv,json,hashlib,random,statistics,sys,time
from pathlib import Path
from collections import defaultdict
from itertools import product
HERE=Path(__file__).resolve().parent
REPO=HERE.parent if HERE.name=='symmetric' else HERE/'baseline'
SRC=REPO/'v25/source/CCF_v15_Reproduction_Candidate_20261123'
sys.path[:0]=[str(SRC),str(REPO/'fairness'),str(HERE)]
from ccf_eventlab.engine import RunConfig
from ccf_eventlab.model import world_factory
from experiment_common import ExperimentEngine
from fair_engines import RemoteGuardIndependent
from symmetry_design import ClaimPlane,StickyPermit,RedirectPermit

WIS=tuple(range(220,232))
SEEDS=(71011,71012,71013)
LOSSES=(0.0,.05,.20,.35)
DEADLINES=(16.,54.)
CORE=('claim_redirect_free','claim_redirect_remote','claim_sticky_free','claim_sticky_remote',
      'permit_redirect_free','permit_redirect_remote','permit_sticky_free','permit_sticky_remote')
FLOORS=('independent_local','independent_remote_guard')
ARMS=CORE+FLOORS
STATS=['completion_fraction','completed_tasks','task_total','total_messages','delivery_losses',
       'executed_actions','duplicate_starts','denied_formal_capacity','overcapacity_admissions','disruptions',
       'lease_requests','lease_request_retries','lease_denials','lease_stale_grants','permit_issued',
       'permit_mean_acquisition_wait','fallback_switches','fallback_busy_switches',
       'fallback_timeout_switches','claim_sticky_block_wakes','local_claim_deliveries',
       'local_manager_deliveries','remote_home_manager_messages','guard_wire_messages']
METADATA=['study','world_idx','world_seed','world_id','world_scale','agents','trial_seed','loss','deadline','arm','family','policy','plane','settlement','message_delay_min','message_delay_max','status','error']
FIELDS=METADATA+STATS

def world(wi):
    return world_factory(170123+wi*23,('small','medium','large')[wi%3])

def simulate(w,seed,arm,loss,deadline,delay_min=None,delay_max=None,settlement=None):
    fam,policy,plane=arm.split('_',2) if arm.startswith(('claim_','permit_')) else ('independent','none',arm)
    is_free=plane=='free'
    mn=(0. if is_free else .35) if delay_min is None else delay_min
    mx=(0. if is_free else .95) if delay_max is None else delay_max
    settle=(0. if is_free else .13) if settlement is None else settlement
    # A free plane has no propagation delay and no settlement by definition.
    if is_free:mn=mx=settle=0.
    cfg=RunConfig('dra' if fam=='claim' else 'independent','formal_capacity',horizon=deadline,
                  delay_min=mn,delay_max=mx,message_loss=loss,settle_extra=settle)
    kw={'physics':'reference','release_profile':'all_at_start'}
    if fam=='claim':
        eng=ClaimPlane(w,cfg,seed,free_plane=is_free,sticky=policy=='sticky',**kw)
    elif fam=='permit':
        cls=RedirectPermit if policy=='redirect' else StickyPermit
        eng=cls(w,cfg,seed,free_plane=is_free,**kw)
    elif arm=='independent_local':
        eng=ExperimentEngine(w,cfg,seed,controller='independent',**kw)
    elif arm=='independent_remote_guard':
        # Floor uses original remote-guard model, not the free claim plane.
        eng=RemoteGuardIndependent(w,cfg,seed,**kw)
    else:raise ValueError(arm)
    r=eng.run()
    return {'family':fam,'policy':policy,'plane':plane,'settlement':settle,'message_delay_min':mn,
            'message_delay_max':mx},r

def analyze(rows,out,world_boots=4000,seed=2602):
    by=defaultdict(list)
    for r in rows:by[(r['deadline'],r['loss'],r['arm'])].append(r)
    summary=[]
    for (deadline,loss,arm),rs in sorted(by.items()):
        if len(rs)!=len(set((r['world_seed'],r['trial_seed']) for r in rs)):
            raise AssertionError('Duplicate world-seed keys')
        failed=sum(r['status']!='completed' for r in rs)
        rec={'deadline':deadline,'loss':loss,'arm':arm,'n':len(rs),'worlds':len({r['world_seed'] for r in rs}),'failures':failed}
        if failed==0:
            for field in STATS:rec[field]=statistics.mean(float(r.get(field) or 0) for r in rs)
            means=[]
            for k in sorted({r['world_seed'] for r in rs}):
                means.append(statistics.mean(float(r['completion_fraction']) for r in rs if r['world_seed']==k))
            rng=random.Random(seed)
            boots=sorted(statistics.mean(means[rng.randrange(len(means))] for _ in means) for _ in range(world_boots))
            rec['completion95lo']=boots[int(.025*world_boots)];rec['completion95hi']=boots[min(int(.975*world_boots),world_boots-1)]
        summary.append(rec)
    with open(out/'summary.csv','w',newline='') as f:
        keys=list(summary[0])
        cw=csv.DictWriter(f,keys,extrasaction='ignore');cw.writeheader();cw.writerows(summary)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    # World-cluster paired contrast for corresponding conditions only.
    contrasts=[]
    pairs=[('claim_redirect_free','permit_redirect_free'),('claim_redirect_remote','permit_redirect_remote'),
           ('claim_sticky_free','permit_sticky_free'),('claim_sticky_remote','permit_sticky_remote'),
           ('claim_redirect_remote','claim_sticky_remote'),('permit_redirect_remote','permit_sticky_remote'),
           ('claim_redirect_free','claim_redirect_remote'),('permit_redirect_free','permit_redirect_remote'),
           ('claim_redirect_remote','independent_local')]
    for deadline,loss in product(sorted(set(r['deadline'] for r in rows)),sorted(set(r['loss'] for r in rows))):
        for a,b in pairs:
            ar=by.get((deadline,loss,a),[]);br=by.get((deadline,loss,b),[])
            ka={(x['world_seed'],x['trial_seed']):x for x in ar};kb={(x['world_seed'],x['trial_seed']):x for x in br}
            if not ar or not br or set(ka)!=set(kb) or any(z['status']!='completed' for z in ar+br):continue
            means=[]
            for w in sorted({k[0] for k in ka}):
                means.append(statistics.mean(float(ka[k]['completion_fraction'])-float(kb[k]['completion_fraction']) for k in ka if k[0]==w))
            rng=random.Random(seed);boots=sorted(statistics.mean(means[rng.randrange(len(means))] for _ in means) for _ in range(world_boots))
            contrasts.append({'deadline':deadline,'loss':loss,'A':a,'B':b,'worlds':len(means),'gap_pp':100*statistics.mean(means),
                              'lo_pp':100*boots[int(.025*world_boots)],'hi_pp':100*boots[min(int(.975*world_boots),world_boots-1)],
                              'worlds_A_gt_B':sum(v>0 for v in means),'worlds_A_lt_B':sum(v<0 for v in means)})
    with open(out/'contrasts.csv','w',newline='') as f:
        w=csv.DictWriter(f,list(contrasts[0]));w.writeheader();w.writerows(contrasts)
    return summary,contrasts

def run(out,world_indices=WIS,seed_list=SEEDS,arms=ARMS,losses=LOSSES,deadlines=DEADLINES,verbose=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    rows=[];start=time.monotonic()
    for wi in world_indices:
        w=world(wi)
        for seed,loss,deadline,arm in product(seed_list,losses,deadlines,arms):
            r={'study':'symmetric_core','world_idx':wi,'world_seed':w.seed,'world_id':w.id,'world_scale':('small','medium','large')[wi%3],
               'agents':w.num_agents,'trial_seed':seed,'loss':loss,'deadline':deadline,'arm':arm}
            try:
                desc,res=simulate(w,seed,arm,loss,deadline);r.update(desc);r.update(res)
                r.update(status='completed',error='')
            except Exception as ex:r.update(status='failed',error=f'{type(ex).__name__}: {ex}')
            rows.append(r)
        if verbose:print('world',wi,'rows',len(rows),'elapsed',round(time.monotonic()-start,1),flush=True)
    with open(out/'episodes.csv','w',newline='') as f:
        cw=csv.DictWriter(f,FIELDS,extrasaction='ignore');cw.writeheader();cw.writerows(rows)
    fail=[r for r in rows if r['status']=='failed'];(out/'failures.json').write_text(json.dumps(fail,indent=2))
    summary,contrasts=analyze(rows,out)
    meta={'world_indices':world_indices,'seeds':seed_list,'losses':losses,'deadlines':deadlines,'arms':arms,
          'episodes':len(rows),'failures':len(fail),'comparison_conditions':len(summary),'contrasts':len(contrasts),
          'source_sha256':{x:hashlib.sha256((HERE/x).read_bytes()).hexdigest() for x in ['run_symmetric.py','symmetry_design.py']},
          'scope':'exploratory synthetic, no physical experiments; same generated worlds as prior release for paired contrasts'}
    (out/'audit.json').write_text(json.dumps(meta,indent=2,default=list))
    print('DONE',len(rows),'fails',len(fail),'secs',round(time.monotonic()-start,1),flush=True)
    return summary,contrasts

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--smoke',action='store_true')
    args=p.parse_args()
    run(args.out,world_indices=WIS[:1] if args.smoke else WIS,seed_list=SEEDS[:1] if args.smoke else SEEDS)
