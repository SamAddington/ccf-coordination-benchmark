#!/usr/bin/env python3
"""Clean, opt-in v28+settlement-policy exact-data reproduction (stdlib only).

The script regenerates frozen v28 records via its existing verified runner,
then replays the *additional* 1,728 post-review episodes (288 pipelined,
1,152 fixed-delay controls, 288 fixed-delay/full-wait controls), compares every
record and checks source and analysis consistency. This does not authenticate
operator/machine or establish physical deployment validity.
"""
from __future__ import annotations
import argparse,datetime,hashlib,json,os,platform,subprocess,sys,math,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def call(cmd,log,env):
 with open(log,'w') as f:
  f.write('COMMAND: '+' '.join(cmd)+'\n');f.flush()
  p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
  f.write('\nEXIT: '+str(p.returncode)+'\n')
 if p.returncode:raise RuntimeError(f'Command failed, see {log}')

def compare(path,actual,mode,keys):
 a=list(csv.DictReader(open(path,newline='')));b=list(csv.DictReader(open(actual,newline='')))
 d={tuple(v[k] for k in keys):v for v in a}
 if len(d)!=len(a):raise RuntimeError('Duplicate keys in frozen data')
 err=[];checked=0
 for row in b:
  key=tuple(row[k] for k in keys)
  if key not in d:err.append(('unknown-key',key));continue
  old=d[key]
  for k,oldv in old.items():
   checked+=1;v=row.get(k)
   if v==oldv:continue
   try:
    if math.isclose(float(v),float(oldv),rel_tol=1e-10,abs_tol=1e-9):continue
   except (ValueError,TypeError):pass
   if len(err)<10:err.append((key,k,oldv,v))
 if mode=='full' and len(a)!=len(b):err.append(('wrong_count',len(a),len(b)))
 match=sha(path)==sha(actual)
 if err or (mode=='full' and not match):raise RuntimeError(f'Comparison failed {err[:3]}; hashes match: {match}')
 return dict(rows=len(b),values_checked=checked,hash_exact=match,reference_sha256=sha(path),new_sha256=sha(actual),status='MATCHED')

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['smoke','full'],default='smoke');p.add_argument('--out',required=True)
 p.add_argument('--operator',default='');p.add_argument('--machine-description',default='');a=p.parse_args()
 out=Path(a.out).resolve()
 if out.exists():p.error('Output path exists; choose a fresh output path')
 out.mkdir(parents=True);logs=out/'logs';logs.mkdir()
 env=dict(os.environ,PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
 result=dict(status='IN_PROGRESS',mode=a.mode,operator_self_reported=a.operator,
   machine_self_reported=a.machine_description,operator_identity_independently_attested=False,
   platform=platform.platform(),python=sys.version,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
   source_manifest_sha256=sha(ROOT/'SHA256SUMS'),studies={})
 try:
  call([sys.executable,str(ROOT/'tools/verify_release.py')],logs/'manifest.log',env)
  # Baseline contains 12,816 prior v28 records; do not overwrite.
  sub=out/'v28_full_baseline' if a.mode=='full' else out/'v28_smoke_baseline'
  call([sys.executable,str(ROOT/'tools/reproduce_v28.py'),'--mode',a.mode,'--out',str(sub)],logs/'v28_base.log',env)
  prior=json.loads((sub/'reproduction_result.json').read_text())
  if not prior['status'].startswith('MATCHED'):raise RuntimeError('Frozen v28 reproduction failed')
  result['studies']['prior_v28']=prior['studies']
  studies=[
    ('pipelined_overlap','symmetric/run_overlap_ablation.py','symmetric/settlement_overlap/episodes.csv',('world_seed','trial_seed','loss','deadline','arm')),
    ('delay_kernel','symmetric/run_delay_kernel_controls.py','symmetric/delay_kernel_controls/episodes.csv',('world_seed','trial_seed','loss','deadline','delay','arm')),
    ('fixed_mean_full_wait','symmetric/run_fixed_mean_settlement_control.py','symmetric/fixed_mean_settlement/episodes.csv',('world_seed','trial_seed','loss','deadline','arm')),
  ]
  for name,script,frozen,keys in studies:
   dest=out/name;cmd=[sys.executable,str(ROOT/script),'--out',str(dest)]
   if a.mode=='smoke':cmd.append('--smoke')
   call(cmd,logs/(name+'.log'),env)
   result['studies'][name]=compare(ROOT/frozen,dest/'episodes.csv',a.mode,keys)
  # Analytics reconstruct supplementary S1/S2/S3 from frozen primary and new results.
  call([sys.executable,str(ROOT/'symmetric/analyze_review_settlement.py'),'--out',str(out/'recomputed_supplement')],logs/'supplement.log',env)
  for name in ('S1_complete_84_delay_deadline_contrasts.csv','S2_full_8cell_settlement_and_sticky.csv','S3_delay_law_and_settlement_controls.csv'):
   if sha(out/'recomputed_supplement'/name)!=sha(ROOT/'symmetric/supplementary_review'/name):
    raise RuntimeError('Supplement mismatch: '+name)
  result['supplement_exact']=True
  result['status']='MATCHED__OPERATOR_AND_MACHINE_SELF_REPORTED'
 except Exception as ex:result['status']='FAILED_OR_INCOMPLETE';result['error']=str(ex)
 result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (out/'reproduction_result.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(dict(status=result['status'],mode=a.mode,result=str(out/'reproduction_result.json'))))
 return 0 if result['status'].startswith('MATCHED') else 1
if __name__=='__main__':sys.exit(main())
