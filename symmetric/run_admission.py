#!/usr/bin/env python3
"""Run explicit admission-placement controls on the published 12-world design.

Primary arms: 2 families x 2 client policies x 2 control planes, plus a
service-priced admission variant for the two remote claim arms. A permit grant
from its service authority already reserves admission; it pays no duplicate
service gate RPC. Free-plane admission variants coincide by construction.

12-world x 3 trial x 4 Bernoulli losses x 2 deadlines x 10 protocol arms =
2880 protocol episodes; plus two uncoordinated reference floors = 3456.
The independently coded v27 baseline is preserved in symmetric/primary.
"""
from __future__ import annotations
import sys,argparse,csv,json,hashlib,statistics,random,time
from pathlib import Path
from itertools import product
from collections import defaultdict
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_symmetric import WIS, SEEDS, LOSSES, DEADLINES, world
from ccf_eventlab.engine import RunConfig
from experiment_common import ExperimentEngine
from fair_engines import RemoteGuardIndependent
from admission_symmetric import ClaimWithCommonDone,ClaimServiceAdmission,PermitStickyWithCommonDone,PermitRedirectWithCommonDone

ARMS=('claim_redirect_free','claim_redirect_remote','claim_redirect_remote_priced',
      'claim_sticky_free','claim_sticky_remote','claim_sticky_remote_priced',
      'permit_redirect_free','permit_redirect_remote','permit_sticky_free','permit_sticky_remote',
      'independent_local','independent_remote_guard')
STATS=['completion_fraction','completed_tasks','task_total','total_messages','wire_payload_bytes','delivery_losses',
       'executed_actions','duplicate_starts','denied_formal_capacity','overcapacity_admissions','disruptions',
       'lease_requests','lease_request_retries','lease_denials','lease_stale_grants','permit_issued',
       'permit_mean_acquisition_wait','fallback_switches','fallback_busy_switches','fallback_timeout_switches',
       'claim_sticky_block_wakes','local_claim_deliveries','local_manager_deliveries',
       'remote_home_manager_messages','guard_wire_messages','guard_requests','guard_timeouts']
META=['study','world_idx','world_seed','world_id','world_scale','agents','trial_seed','loss','deadline','arm','family','policy','plane','admission','settle_wait','message_delay_min','message_delay_max','status','error']
FIELDS=META+STATS


def simulate(w,seed,arm,loss,deadline,*,delay=None,settle_wait=None):
    if arm.startswith(('claim_','permit_')):
        terms=arm.split('_');fam=terms[0];policy=terms[1];plane=terms[2];priced=terms[-1]=='priced'
    else:
        fam='independent';policy='none';plane='remote';priced=arm.endswith('remote_guard')
    free=plane=='free'
    if free and priced:raise ValueError('Free admission price is the same as the local guard by construction')
    if delay is None:lo,hi=(0.,0.) if free else (.35,.95)
    else:lo=hi=delay
    # Net claim wait = maximum claim propagation delay + 0.13 for remote,
    # zero for free; explicit settlement override enables no-settlement control.
    net_wait=0. if (free or hi==0) else hi+.13
    if settle_wait is not None:net_wait=float(settle_wait)
    # Core schedules pending_at=now+cfg.delay_max+cfg.settle_extra.
    settle_extra=net_wait-hi
    cfg=RunConfig('dra' if fam=='claim' else 'independent','formal_capacity',
                  horizon=float(deadline),message_loss=loss,delay_min=lo,delay_max=hi,
                  settle_extra=settle_extra)
    kw=dict(physics='reference',release_profile='all_at_start')
    if fam=='claim':
        cls=ClaimServiceAdmission if priced else ClaimWithCommonDone
        eng=cls(w,cfg,seed,free_plane=free,sticky=policy=='sticky',**kw)
    elif fam=='permit':
        cls=PermitRedirectWithCommonDone if policy=='redirect' else PermitStickyWithCommonDone
        eng=cls(w,cfg,seed,free_plane=free,**kw)
    elif arm=='independent_local':
        eng=ExperimentEngine(w,cfg,seed,controller='independent',**kw)
    elif arm=='independent_remote_guard':
        eng=RemoteGuardIndependent(w,cfg,seed,**kw)
    else:raise ValueError(arm)
    r=eng.run()
    return {'family':fam,'policy':policy,'plane':plane,
            'admission':'service_rpc' if priced and fam=='claim' else ('service_grant' if fam=='permit' else 'local_check'),
            'settle_wait':net_wait,'message_delay_min':lo,'message_delay_max':hi},r


def bootstrap(vals,draws=4000,seed=2602):
    rng=random.Random(seed);n=len(vals)
    x=sorted(sum(vals[rng.randrange(n)] for _ in range(n))/n for _ in range(draws))
    return x[int(.025*draws)],x[int(.975*draws)]


def analyze(rows,out):
    by=defaultdict(list)
    for r in rows:by[(r['deadline'],r['loss'],r['arm'])].append(r)
    summ=[]
    for (deadline,loss,arm),rs in sorted(by.items()):
        n_world=len({r['world_seed'] for r in rs});
        v={'deadline':deadline,'loss':loss,'arm':arm,'n':len(rs),'worlds':n_world,'failures':sum(r['status']!='completed' for r in rs)}
        if not v['failures']:
            for f in STATS:v[f]=statistics.mean(float(r.get(f) or 0) for r in rs)
            means=[statistics.mean(float(r['completion_fraction']) for r in rs if r['world_seed']==w) for w in sorted({r['world_seed'] for r in rs})]
            v['lo'],v['hi']=bootstrap(means)
        summ.append(v)
    pairs=[('claim_redirect_free','permit_redirect_free'),('claim_redirect_remote','permit_redirect_remote'),
           ('claim_redirect_remote_priced','permit_redirect_remote'),
           ('claim_sticky_free','permit_sticky_free'),('claim_sticky_remote','permit_sticky_remote'),
           ('claim_sticky_remote_priced','permit_sticky_remote'),
           ('claim_redirect_remote','claim_redirect_remote_priced'),
           ('claim_sticky_remote','claim_sticky_remote_priced'),
           ('claim_redirect_free','claim_redirect_remote'),('permit_redirect_free','permit_redirect_remote'),
           ('claim_redirect_remote_priced','independent_remote_guard'),
           ('claim_redirect_free','independent_local')]
    cont=[]
    for dl,loss in product(sorted({r['deadline'] for r in rows}),sorted({r['loss'] for r in rows})):
        for a,b in pairs:
            x=by.get((dl,loss,a),[]);y=by.get((dl,loss,b),[])
            ka={(r['world_seed'],r['trial_seed']):r for r in x}; kb={(r['world_seed'],r['trial_seed']):r for r in y}
            if not ka or not kb or set(ka)!=set(kb) or any(r['status']!='completed' for r in x+y):continue
            diffs=[statistics.mean(float(ka[k]['completion_fraction'])-float(kb[k]['completion_fraction']) for k in ka if k[0]==w) for w in sorted({k[0] for k in ka})]
            lo,hi=bootstrap(diffs)
            cont.append(dict(deadline=dl,loss=loss,A=a,B=b,worlds=len(diffs),gap_pp=100*statistics.mean(diffs),lo_pp=100*lo,hi_pp=100*hi,worlds_A_gt_B=sum(d>0 for d in diffs),worlds_A_lt_B=sum(d<0 for d in diffs)))
    def write(name,rs):
        with open(out/name,'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rs[0]),extrasaction='ignore');w.writeheader();w.writerows(rs)
    write('summary.csv',summ);write('contrasts.csv',cont)
    (out/'summary.json').write_text(json.dumps(summ,indent=2))
    return summ,cont


def run(out,wi=WIS,seeds=SEEDS,arms=ARMS,losses=LOSSES,deadlines=DEADLINES):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    rows=[];t0=time.monotonic()
    for idx in wi:
        w=world(idx)
        for seed,loss,dl,arm in product(seeds,losses,deadlines,arms):
            r=dict(study='admission_placement',world_idx=idx,world_seed=w.seed,world_id=w.id,world_scale=('small','medium','large')[idx%3],agents=w.num_agents,
                   trial_seed=seed,loss=loss,deadline=dl,arm=arm)
            try:
                desc,rr=simulate(w,seed,arm,loss,dl);r.update(desc);r.update(rr);r.update(status='completed',error='')
            except Exception as e:r.update(status='failed',error=type(e).__name__+': '+str(e))
            rows.append(r)
        print('world',idx,'records',len(rows),'sec',round(time.monotonic()-t0,1),flush=True)
    with open(out/'episodes.csv','w',newline='') as f:
        writer=csv.DictWriter(f,FIELDS,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    (out/'failures.json').write_text(json.dumps([r for r in rows if r['status']!='completed'],indent=2))
    ss,cc=analyze(rows,out)
    meta={'episodes':len(rows),'failures':len([r for r in rows if r['status']!='completed']),'complete_summary_cells':len(ss),'complete_contrasts':len(cc),
          'note':'Exploratory synthetic modeled service admission; same 12 generated worlds as v27; no remote host; not author-run',
          'design':'8 base protocol configurations + 2 priced remote claim variants + 2 contextual floor arms',
          'source_sha256':{p:hashlib.sha256((HERE/p).read_bytes()).hexdigest() for p in ('run_admission.py','admission_symmetric.py')}}
    (out/'audit.json').write_text(json.dumps(meta,indent=2))
    print('DONE',len(rows),'failures',meta['failures'],'seconds',round(time.monotonic()-t0,1),flush=True)
    return ss,cc

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    run(a.out,wi=WIS[:1] if a.smoke else WIS,seeds=SEEDS[:1] if a.smoke else SEEDS)
