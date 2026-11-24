#!/usr/bin/env python3
import csv,random,statistics,collections,math,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
rows=list(csv.DictReader(open(ROOT/'results'/'episodes.csv')))
output=ROOT/'figures';output.mkdir(exist_ok=True)
ARM_LABELS={
 'claim_local':'Claim/local','claim_remote':'Claim/guard RPC',
 'independent_local':'Independent/local','independent_remote':'Independent/guard RPC',
 'permit_sticky':'Permits/sticky','permit_fallback':'Permits/fallback',
 'permit_fallback_retx':'Permits/fallback+retrans.',
 'permit_colocated':'Permits/colocated','permit_colocated_fallback':'Permits/colocated+fallback'}
LOSS=[0,.05,.20,.35]

def subset(h,l,a):return [r for r in rows if abs(float(r['horizon'])-h)<1e-5 and abs(float(r['loss'])-l)<1e-7 and r['arm']==a]
def mean(h,l,a):return 100*statistics.mean(float(r['completion_fraction']) for r in subset(h,l,a))
def clboot(vals,n=4000):
 rr=random.Random(2602);m=len(vals)
 s=sorted(statistics.mean([vals[rr.randrange(m)] for _ in vals]) for _ in range(n))
 return [s[99],s[3899]]
def interval(h,l,a):
 by=collections.defaultdict(list)
 for r in subset(h,l,a):by[r['world_seed']].append(100*float(r['completion_fraction']))
 return clboot([statistics.mean(v) for _,v in sorted(by.items())])
def contrast(h,l,a,b):
 ai={(r['world_seed'],r['trial_seed']):float(r['completion_fraction']) for r in subset(h,l,a)}
 bi={(r['world_seed'],r['trial_seed']):float(r['completion_fraction']) for r in subset(h,l,b)}
 by=collections.defaultdict(list)
 for (w,s),val in ai.items():by[w].append(100*(val-bi[(w,s)]))
 wmeans=[statistics.mean(v) for _,v in sorted(by.items())]
 return (statistics.mean(wmeans),*clboot(wmeans))

contrasts=[]
for h in [16,54]:
 for l in LOSS:
  for a,b in [('claim_local','permit_sticky'),('claim_local','permit_fallback'),
              ('claim_local','permit_colocated_fallback'),('claim_remote','permit_fallback'),
              ('permit_fallback','permit_sticky'),('permit_colocated_fallback','permit_fallback'),
              ('claim_local','independent_local')]:
   m,lo,hi=contrast(h,l,a,b)
   contrasts.append(dict(horizon=h,loss=l,first=a,second=b,mean_pp=m,lo95_pp=lo,hi95_pp=hi))
with open(ROOT/'results'/'paired_world_contrasts.csv','w',newline='') as f:
 w=csv.DictWriter(f,list(contrasts[0]));w.writeheader();w.writerows(contrasts)
full=[]
for h in [16,54]:
 for l in LOSS:
  for a in ARM_LABELS:
   inter=interval(h,l,a)
   ss=subset(h,l,a)
   full.append(dict(horizon=h,loss=l,arm=a,mean_completion_pct=mean(h,l,a),lo95_pct=inter[0],hi95_pct=inter[1],
     mean_transmissions=statistics.mean(float(x['total_messages']) for x in ss),
     mean_delivered_losses=statistics.mean(float(x['delivery_losses']) for x in ss),
     overcapacity_total=sum(float(x['overcapacity_admissions']) for x in ss),worlds=12,episodes=len(ss)))
with open(ROOT/'results'/'all_72_cells_with_intervals.csv','w',newline='') as f:
 w=csv.DictWriter(f,list(full[0]));w.writeheader();w.writerows(full)

for h in [16,54]:
 fig,ax=plt.subplots(figsize=(4.8,3.7),dpi=200)
 selected=['claim_local','claim_remote','permit_sticky','permit_fallback','permit_colocated_fallback']
 marks=['o','s','^','D','x']
 for a,marker in zip(selected,marks):
  y=[mean(h,l,a) for l in LOSS]
  ci=[interval(h,l,a) for l in LOSS]
  line,=ax.plot([100*l for l in LOSS],y,linewidth=1.65,marker=marker,markersize=4,label=ARM_LABELS[a])
  ax.fill_between([100*l for l in LOSS],[z[0] for z in ci],[z[1] for z in ci],alpha=.10,color=line.get_color())
 ax.set(xlabel='Independent message loss (%)',ylabel='Tasks completed (%)',xticks=[0,5,20,35],ylim=(0,105))
 ax.grid(axis='y',alpha=.22)
 fig.legend(loc='upper center',bbox_to_anchor=(.5,.985),ncol=2,frameon=False,fontsize=7.7,
            handlelength=1.4,columnspacing=.7)
 fig.subplots_adjust(top=.68,bottom=.17,left=.15,right=.97)
 fig.savefig(output/f'completion_h{h}.png',dpi=240)
 plt.close(fig)

print('wrote full table',len(full),'contrasts',len(contrasts))
for h in [16,54]:
 print('H',h)
 for l in LOSS:
  print(l,', '.join(f'{ARM_LABELS[a]}: {mean(h,l,a):.1f}' for a in ['claim_local','claim_remote','permit_sticky','permit_fallback','permit_colocated_fallback']))
