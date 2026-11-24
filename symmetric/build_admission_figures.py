#!/usr/bin/env python3
"""Generate v28 research figures from frozen v28 CSV; run in a disposable clone."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
DEST=ROOT/'admission_figures';DEST.mkdir(exist_ok=True)
rs=list(csv.DictReader(open(ROOT/'admission_primary/summary.csv',newline='')))
cts=list(csv.DictReader(open(ROOT/'admission_primary/contrasts.csv',newline='')))
gr=list(csv.DictReader(open(ROOT/'admission_priced_grid/paired_gaps.csv',newline='')))
plt.rcParams.update({'font.size':9, 'axes.titlesize':10,'legend.fontsize':8,'savefig.dpi':280})

def r(arm,h,loss):
 return next(x for x in rs if x['arm']==arm and float(x['deadline'])==h and float(x['loss'])==loss)
xs=[0,5,20,35]
fig,ax=plt.subplots(figsize=(7.1,3.75))
for arm,label in [('claim_redirect_free','Claims, free control and guard'),('permit_redirect_free','Permits, free manager'),
                  ('claim_redirect_remote','Claims, remote messages + local guard'),
                  ('claim_redirect_remote_priced','Claims, remote messages + service guard'),
                  ('permit_redirect_remote','Permits, remote service authority')]:
 rr=[r(arm,16.,x/100) for x in xs]
 y=[100*float(a['completion_fraction']) for a in rr]
 ln=ax.plot(xs,y,marker='o',linewidth=1.6,label=label)[0]
 ax.fill_between(xs,[100*float(a['lo']) for a in rr],[100*float(a['hi']) for a in rr],alpha=.10,color=ln.get_color())
ax.set(xlabel='Independent message loss (%)',ylabel='Authorized tasks completed (%)',ylim=(15,105),xticks=xs)
ax.grid(alpha=.25)
fig.legend(*ax.get_legend_handles_labels(),ncol=2,loc='upper center',bbox_to_anchor=(.5,1.01),frameon=False)
fig.subplots_adjust(top=.68,left=.09,right=.98,bottom=.17)
fig.savefig(DEST/'admission_completion_h16.png');plt.close(fig)

fig,ax=plt.subplots(figsize=(7.1,3.45))
for a,b,label in [('claim_redirect_remote','permit_redirect_remote','Unpriced claim admission minus permits'),
                   ('claim_redirect_remote_priced','permit_redirect_remote','Priced claim admission minus permits')]:
 rr=[next(z for z in cts if z['A']==a and z['B']==b and float(z['deadline'])==16. and float(z['loss'])==x/100) for x in xs]
 y=[float(z['gap_pp']) for z in rr]
 lower=[float(z['gap_pp'])-float(z['lo_pp']) for z in rr]
 upper=[float(z['hi_pp'])-float(z['gap_pp']) for z in rr]
 ax.errorbar(xs,y,yerr=[lower,upper],marker='o',capsize=3,linewidth=1.5,label=label)
ax.axhline(0,linestyle='--',linewidth=1,color='gray')
ax.set(xlabel='Independent message loss (%)',ylabel='Claims minus permits (percentage points)',xticks=xs)
ax.grid(alpha=.23)
fig.legend(*ax.get_legend_handles_labels(),ncol=1,loc='upper center',bbox_to_anchor=(.5,1.00),frameon=False)
fig.subplots_adjust(top=.77,left=.11,right=.97,bottom=.17)
fig.savefig(DEST/'admission_paired_gap_h16.png');plt.close(fig)

fig,ax=plt.subplots(figsize=(7.1,3.55))
for loss,h,label in [(0.,16.,'16-unit deadline, 0% loss'),(.2,16.,'16-unit deadline, 20% loss'),
                     (0.,54.,'54-unit deadline, 0% loss'),(.2,54.,'54-unit deadline, 20% loss')]:
 ss=[z for z in gr if z['A']=='claim_redirect_remote_priced' and z['loss']==str(loss) and z['deadline']==str(h)]
 ss=sorted(ss,key=lambda z:float(z['delay']))
 xx=[float(z['delay']) for z in ss]; yy=[float(z['gap_pp']) for z in ss]
 ln=ax.plot(xx,yy,marker='o',markersize=3,linewidth=1.4,label=label)[0]
 ax.fill_between(xx,[float(z['lo_pp']) for z in ss],[float(z['hi_pp']) for z in ss],alpha=.1,color=ln.get_color())
ax.axhline(0,linestyle='--',linewidth=1,color='gray')
ax.set(xlabel='Deterministic modeled one-hop delay (time units)',ylabel='Priced claims minus permits (pp)',xticks=[0,.25,.5,.95,1.3,1.8])
ax.grid(alpha=.23)
fig.legend(*ax.get_legend_handles_labels(),ncol=2,loc='upper center',bbox_to_anchor=(.5,1.02),frameon=False)
fig.subplots_adjust(top=.72,left=.115,right=.98,bottom=.16)
fig.savefig(DEST/'priced_gap_latency_deadline.png');plt.close(fig)
print('Created',len(list(DEST.glob('*.png'))),'figures')
