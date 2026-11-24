#!/usr/bin/env python3
"""Exploratory deterministic-delay × deadline × loss grid, admitted at service.

Unlike the frozen v27 grid, this explicitly charges claim admission over the
same per-hop loss/delay law used by the service permit authority. The comparator
and unpriced-claim control are retained for matched context. File is a new
study, not a replacement for historical records.
"""
from __future__ import annotations
import argparse,csv,json,time,statistics,random
from pathlib import Path
from itertools import product
from collections import defaultdict
from run_symmetric import WIS,SEEDS,world
from run_admission import simulate,bootstrap
DELAYS=(0.,.10,.25,.50,.95,1.30,1.80)
DEADLINES=(8.,12.,16.,24.,36.,54.)
LOSSES=(0.,.20)
ARMS=('claim_redirect_remote','claim_redirect_remote_priced','permit_redirect_remote')
FIELDS=['world_idx','world_seed','trial_seed','loss','deadline','delay','arm','settle_wait','admission','completion_fraction',
        'executed_actions','duplicate_starts','denied_formal_capacity','total_messages','guard_wire_messages',
        'permit_mean_acquisition_wait','status','error']

def run_part(out,worlds):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    rows=[];t0=time.monotonic()
    for wi in worlds:
        w=world(wi)
        for seed,loss,deadline,d,arm in product(SEEDS,LOSSES,DEADLINES,DELAYS,ARMS):
            rec=dict(world_idx=wi,world_seed=w.seed,trial_seed=seed,loss=loss,deadline=deadline,delay=d,arm=arm)
            try:
                desc,r=simulate(w,seed,arm,loss,deadline,delay=d)
                rec.update(desc);rec.update(r);rec.update(status='completed',error='')
            except Exception as ex:rec.update(status='failed',error=str(ex))
            rows.append(rec)
        print('world',wi,'records',len(rows),'elapsed',round(time.monotonic()-t0,1),flush=True)
    with open(out/'episodes.csv','w',newline='') as f:
        writer=csv.DictWriter(f,FIELDS,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    (out/'failures.json').write_text(json.dumps([r for r in rows if r['status']!='completed'],indent=2))
    return rows

def analyze(rows,out):
    out=Path(out);by=defaultdict(list)
    for r in rows:by[(float(r['loss']),float(r['deadline']),float(r['delay']),r['arm'])].append(r)
    summary=[];gaps=[]
    for (loss,dl,d,arm),rr in sorted(by.items()):
        rec=dict(loss=loss,deadline=dl,delay=d,arm=arm,episodes=len(rr),worlds=len({r['world_seed'] for r in rr}),failures=sum(x['status']!='completed' for x in rr))
        if not rec['failures']:
            for k in ['completion_fraction','executed_actions','duplicate_starts','denied_formal_capacity','total_messages','guard_wire_messages','permit_mean_acquisition_wait']:
                rec[k]=statistics.mean(float(x.get(k) or 0) for x in rr)
            wm=[statistics.mean(float(x['completion_fraction']) for x in rr if x['world_seed']==w) for w in sorted({x['world_seed'] for x in rr})]
            rec['lo'],rec['hi']=bootstrap(wm)
        summary.append(rec)
    pairs=[('claim_redirect_remote_priced','permit_redirect_remote'),('claim_redirect_remote','permit_redirect_remote'),('claim_redirect_remote','claim_redirect_remote_priced')]
    for loss,dl,d in sorted({k[:3] for k in by}):
        for a,b in pairs:
            aa=by[(loss,dl,d,a)]; bb=by[(loss,dl,d,b)]
            ka={(r['world_seed'],r['trial_seed']):r for r in aa};kb={(r['world_seed'],r['trial_seed']):r for r in bb}
            if set(ka)!=set(kb) or any(x['status']!='completed' for x in aa+bb):continue
            wm=[statistics.mean(float(ka[key]['completion_fraction'])-float(kb[key]['completion_fraction']) for key in ka if key[0]==w) for w in sorted({k[0] for k in ka})]
            lo,hi=bootstrap(wm)
            gaps.append(dict(loss=loss,deadline=dl,delay=d,A=a,B=b,episodes=len(ka),worlds=len(wm),gap_pp=100*statistics.mean(wm),lo_pp=100*lo,hi_pp=100*hi,worlds_claim_better=sum(x>0 for x in wm),worlds_permit_better=sum(x<0 for x in wm)))
    def write(name,rs):
        with open(out/name,'w',newline='') as f:
            ww=csv.DictWriter(f,list(rs[0]));ww.writeheader();ww.writerows(rs)
    write('summary.csv',summary);write('paired_gaps.csv',gaps)
    (out/'audit.json').write_text(json.dumps({'episodes':len(rows),'failures':sum(x['status']!='completed' for x in rows),
               'summary_cells':len(summary),'paired_contrasts':len(gaps),
               'worlds':len({x['world_seed'] for x in rows}),'design':'3 arms × 7 delays × 6 deadlines × 2 loss × 12 worlds × 3 trials',
               'bootstrap':'world-cluster resamples 4000 seed 2602',
               'source':'Exploratory simulator; not independent multi-host evaluation'},indent=2))
    return summary,gaps

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--world-start',type=int,default=0);p.add_argument('--world-end',type=int,default=12);a=p.parse_args()
    rows=run_part(a.out,WIS[a.world_start:a.world_end])
    if a.world_start==0 and a.world_end==12:
        summ,gaps=analyze(rows,Path(a.out))
        print("ANALYZED",len(summ),"cells and",len(gaps),"paired contrasts",flush=True)
