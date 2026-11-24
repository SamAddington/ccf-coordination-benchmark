#!/usr/bin/env python3
"""Generate original figures from frozen summary tables without changing them.

Usage: python symmetric/build_figures.py --out ../figures_v27_check
Requires Matplotlib; core study requires only Python standard library.
"""
import argparse,csv
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parent

def read_rows(file):
    with open(file,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=read_rows(ROOT/'primary/summary.csv')
    arms=[('claim_redirect_free','Claims, free'),('permit_redirect_free','Permits, free'),
          ('claim_redirect_remote','Claims, remote'),('permit_redirect_remote','Permits, remote')]
    for h in (16,54):
        fig,ax=plt.subplots(figsize=(3.58,3.03),dpi=300)
        for arm,label in arms:
            rr=sorted([r for r in rows if float(r['deadline'])==h and r['arm']==arm],key=lambda x:float(x['loss']))
            x=[float(r['loss'])*100 for r in rr];y=[float(r['completion_fraction'])*100 for r in rr]
            line,=ax.plot(x,y,marker='o',markersize=3,linewidth=1.3,linestyle='--' if 'remote' in arm else '-',label=label)
            lo=[float(r['completion95lo'])*100 for r in rr];hi=[float(r['completion95hi'])*100 for r in rr]
            ax.fill_between(x,lo,hi,alpha=.11,color=line.get_color())
        ax.set_xlabel('Independent message loss (%)',fontsize=8.5);ax.set_ylabel('Task completion (%)',fontsize=8.5)
        ax.set_ylim(0,103);ax.set_xlim(-1,36);ax.grid(alpha=.2)
        ax.tick_params(labelsize=8)
        fig.legend(*ax.get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,.98),ncol=2,fontsize=7.4,frameon=False)
        fig.subplots_adjust(left=.16,right=.985,bottom=.15,top=.75)
        fig.savefig(out/f'completion_h{h}.png',dpi=300,facecolor='white');plt.close(fig)
    g=read_rows(ROOT/'latency/paired_gaps.csv')
    fig,ax=plt.subplots(figsize=(3.58,3.03),dpi=300)
    for loss,h in [(0,16),(.2,16),(0,54),(.2,54)]:
        rr=sorted((r for r in g if float(r['loss'])==loss and float(r['deadline'])==h),key=lambda r:float(r['delay']))
        x=[float(r['delay']) for r in rr];y=[float(r['gap_claim_minus_permit_pp']) for r in rr]
        label=f'{h:g} units, {loss*100:.0f}% loss'
        line,=ax.plot(x,y,marker='o',markersize=2.9,linewidth=1.3,linestyle='--' if loss else '-',label=label)
        ax.fill_between(x,[float(r['lo_pp']) for r in rr],[float(r['hi_pp']) for r in rr],alpha=.12,color=line.get_color())
    ax.axhline(0,linewidth=.7,color='black')
    ax.set_xlabel('Deterministic per-hop delay (model units)',fontsize=8.5)
    ax.set_ylabel('Claims minus permits (pp)',fontsize=8.5)
    ax.tick_params(labelsize=8);ax.grid(alpha=.2)
    fig.legend(*ax.get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,.99),ncol=2,fontsize=7.2,frameon=False)
    fig.subplots_adjust(left=.17,right=.99,bottom=.16,top=.75)
    fig.savefig(out/'gap_vs_latency.png',dpi=300,facecolor='white');plt.close(fig)
    print('Generated 3 original 300 DPI figures at',out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();main(a.out)
