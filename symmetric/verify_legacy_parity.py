#!/usr/bin/env python3
"""Verify the new remote redirecting claim arm reproduces the v26 baseline.

This is a regression parity check, not an independent test of model validity.
"""
from pathlib import Path
import csv,json,math
ROOT=Path(__file__).resolve().parents[1]

def load(path):
    with open(path,newline='') as f:return list(csv.DictReader(f))

def key(row,older=False):
    return (row['world_seed'],row['trial_seed'],row['loss'],row['horizon' if older else 'deadline'])
old=[r for r in load(ROOT/'fairness/results/episodes.csv') if r['arm']=='claim_local']
new=[r for r in load(ROOT/'symmetric/primary/episodes.csv') if r['arm']=='claim_redirect_remote']
a={key(r,True):r for r in old};b={key(r):r for r in new}
if len(a)!=len(old) or len(b)!=len(new) or a.keys()!=b.keys():raise RuntimeError('Different or duplicate episode keys')
cols=['completion_fraction','completed_tasks','executed_actions','duplicate_starts','overcapacity_admissions','total_messages','delivery_losses']
checked=0;bad=[]
for k,r in a.items():
    rr=b[k]
    for c in cols:
        checked+=1
        if not math.isclose(float(r.get(c) or 0),float(rr.get(c) or 0),rel_tol=1e-10,abs_tol=1e-9):
            if len(bad)<10:bad.append((k,c,r.get(c),rr.get(c)))
report={'pass':not bad,'episodes':len(a),'fields_compared':checked,'failures':bad,'interpretation':'Remote redirecting claims match frozen v26 claim-local source behavior'}
print(json.dumps(report,indent=2))
if bad:raise SystemExit(1)
