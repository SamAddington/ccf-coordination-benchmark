#!/usr/bin/env python3
"""Check published v28 admission-pricing source and empirical episode records.

Run modes: smoke (one world/one seed) or full (all 12 worlds and three seeds).
Output directory MUST be new; preserve raw logs and hashes. This test checks
repeatable synthetic computation, not physical machine identity or validity.
"""
from __future__ import annotations
from pathlib import Path
import argparse,csv,hashlib,json,math,os,platform,subprocess,sys,datetime
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def compare(known,observed,primary,full):
 with open(known,newline='') as f:old=list(csv.DictReader(f))
 with open(observed,newline='') as f:new=list(csv.DictReader(f))
 if primary=='admission_primary':keys=['world_seed','trial_seed','arm','loss','deadline']
 elif primary=='admission_priced_grid':keys=['world_seed','trial_seed','arm','loss','deadline','delay']
 else:keys=['world_seed','trial_seed','arm','loss','deadline']
 indexed={tuple(r[k] for k in keys):r for r in old}
 if len(indexed)!=len(old):raise RuntimeError('Reference keys not unique: '+primary)
 mismatch=[]; cells=0
 for v in new:
  key=tuple(v[k] for k in keys)
  if key not in indexed:
   mismatch.append(('new-key',key));continue
  prior=indexed[key]
  for fld,old_val in prior.items():
   cells+=1;cur=v.get(fld)
   if old_val==cur:continue
   try:
    if math.isclose(float(old_val),float(cur),rel_tol=1e-10,abs_tol=1e-9):continue
   except (ValueError,TypeError):pass
   if len(mismatch)<15:mismatch.append((key,fld,old_val,cur))
 if full and len(new)!=len(old):mismatch.append(('row-count',len(new),len(old)))
 matching=(sha(known)==sha(observed))
 if mismatch or (full and not matching):raise RuntimeError(f'{primary}: {mismatch[:5]}, equal_hash={matching}')
 return dict(pass_status=not mismatch,rows=len(new),cells=cells,reference_sha256=sha(known),rerun_sha256=sha(observed),full_hash_match=matching)

def call(cmd,log,env):
 with open(log,'w') as f:
  f.write('COMMAND: '+' '.join(cmd)+'\n');f.flush()
  p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
  f.write('\nEXIT: '+str(p.returncode)+'\n')
 if p.returncode:raise RuntimeError(f'Execution error {p.returncode}: {log}')

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['smoke','full'],default='smoke');p.add_argument('--out',required=True)
 p.add_argument('--operator',default='');p.add_argument('--machine-description',default='');args=p.parse_args()
 dest=Path(args.out).resolve()
 if dest.exists():p.error('Output path exists; choose a fresh empty path')
 dest.mkdir(parents=True);logs=dest/'logs';logs.mkdir()
 env=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1')
 res=dict(status='IN_PROGRESS',mode=args.mode,operator_self_reported=args.operator,machine_self_reported=args.machine_description,
          operator_and_machine_independently_verified=False,host_platform=platform.platform(),python=sys.version,
          started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(ROOT/'SHA256SUMS'),studies={})
 try:
  call([sys.executable,str(ROOT/'tools/verify_release.py')],logs/'manifest.log',env)
  experiments=[('admission_primary','symmetric/run_admission.py','symmetric/admission_primary/episodes.csv'),
               ('admission_priced_grid','symmetric/run_priced_grid.py','symmetric/admission_priced_grid/episodes.csv'),
               ('admission_no_settlement','symmetric/run_settlement_ablation.py','symmetric/admission_no_settlement/episodes.csv')]
  for name,script,stored in experiments:
   output=dest/name;cmd=[sys.executable,str(ROOT/script),'--out',str(output)]
   if args.mode=='smoke':
    if name=='admission_priced_grid':cmd+=['--world-start','0','--world-end','1']
    else:cmd+=['--smoke']
   call(cmd,logs/(name+'.log'),env)
   res['studies'][name]=compare(ROOT/stored,output/'episodes.csv',name,args.mode=='full')
  res['status']='MATCHED__OPERATOR_AND_MACHINE_SELF_REPORTED'
 except Exception as ex:
  res['status']='FAILED_OR_INCOMPLETE';res['error']=str(ex)
 res['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (dest/'reproduction_result.json').write_text(json.dumps(res,indent=2))
 print(json.dumps({'status':res['status'],'studies':{k:x['rows'] for k,x in res['studies'].items()},'result':str(dest/'reproduction_result.json')},indent=2))
 return 0 if res['status'].startswith('MATCHED') else 1
if __name__=='__main__':sys.exit(main())
