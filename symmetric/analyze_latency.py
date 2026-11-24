#!/usr/bin/env python3
"""Fast, stdlib-only world-cluster analysis of recorded crossover episodes."""
import csv,json,random,argparse
from pathlib import Path
from collections import defaultdict

def mean(v):return sum(v)/len(v) if v else float('nan')

def boot_ci(means,n=4000,seed=2602):
    rng=random.Random(seed);k=len(means)
    x=sorted(sum(means[rng.randrange(k)] for _ in range(k))/k for _ in range(n))
    return x[100],x[3900]

def analyze(out):
    out=Path(out)
    with open(out/'episodes.csv',newline='') as f: rows=list(csv.DictReader(f))
    by=defaultdict(list)
    for r in rows:
        by[(float(r['loss']),float(r['deadline']),float(r['per_hop_delay']),r['arm'])].append(r)
    summary=[];gaps=[]
    for (loss,deadline,delay,arm),rr in sorted(by.items()):
        x={'loss':loss,'deadline':deadline,'delay':delay,'arm':arm,'episodes':len(rr),'failed':sum(v['status']!='completed' for v in rr)}
        if not x['failed']:
            for k in ['completion_fraction','executed_actions','duplicate_starts','total_messages','delivery_losses','permit_mean_acquisition_wait']:
                x[k]=mean([float(r.get(k) or 0) for r in rr])
        summary.append(x)
    combos=sorted(set(k[:3] for k in by))
    for loss,deadline,delay in combos:
        a=by[(loss,deadline,delay,'claim_redirect_remote')];b=by[(loss,deadline,delay,'permit_redirect_remote')]
        if any(x['status']!='completed' for x in a+b):continue
        akey={(int(x['world_seed']),int(x['trial_seed'])):x for x in a}
        bkey={(int(x['world_seed']),int(x['trial_seed'])):x for x in b}
        if set(akey)!=set(bkey):raise ValueError('unpaired world / trial keys')
        wm=[]
        for w in sorted({k[0] for k in akey}):
            wm.append(mean([float(akey[key]['completion_fraction'])-float(bkey[key]['completion_fraction']) for key in akey if key[0]==w]))
        lo,hi=boot_ci(wm)
        gaps.append({'loss':loss,'deadline':deadline,'delay':delay,'gap_claim_minus_permit_pp':100*mean(wm),'lo_pp':100*lo,'hi_pp':100*hi,
                     'claim_worlds_better':sum(x>0 for x in wm),'permit_worlds_better':sum(x<0 for x in wm)})
    for fn,dat in [('summary.csv',summary),('paired_gaps.csv',gaps)]:
        with open(out/fn,'w',newline='') as f:
            cw=csv.DictWriter(f,dat[0].keys());cw.writeheader();cw.writerows(dat)
    failures=[r for r in rows if r['status']!='completed']
    meta={'episodes':len(rows),'failures':len(failures),'condition_rows':len(summary),'paired_contrasts':len(gaps),
          'loss_levels':sorted(set(float(x['loss']) for x in rows)),'deadlines':sorted(set(float(x['deadline']) for x in rows)),
          'per_hop_delays':sorted(set(float(x['per_hop_delay']) for x in rows)),
          'worlds':len(set(x['world_seed'] for x in rows)),'trial_seeds':len(set(x['trial_seed'] for x in rows)),
          'bootstrap_draws':4000,'bootstrap_seed':2602,'bootstrap_unit':'generated world',
          'scope':'post-review exploratory synthetic per-hop fixed-delay crossover; no third-party independent validation'}
    (out/'audit.json').write_text(json.dumps(meta,indent=2))
    return summary,gaps

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args()
    s,g=analyze(a.out);print('SUMMARY',len(s),'GAPS',len(g),'DONE')
