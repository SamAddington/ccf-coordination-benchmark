#!/usr/bin/env python3
"""Reproduce exploratory symmetric v27 records from a clean tree.

Never modifies the repository and does not certify the operator or host.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,platform,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def recs(path):
    with open(path,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def eq(a,b):
    if a==b:return True
    try:return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-9)
    except (TypeError,ValueError):return False

def verify_subset(old,new,smoke):
    expected=recs(old); actual=recs(new)
    cols=['world_seed','trial_seed','arm','loss','deadline'] if '/primary/' in str(old) else ['world_seed','trial_seed','arm','loss','deadline','per_hop_delay']
    index={tuple(z[k] for k in cols):z for z in expected}
    failures=[]; fields=0
    if len(index)!=len(expected):raise RuntimeError('duplicate reference keys')
    if not smoke and len(expected)!=len(actual):failures.append('different row count')
    for row in actual:
        k=tuple(row[q] for q in cols)
        if k not in index:failures.append(f'unknown record: {k}');continue
        prior=index[k]
        for col,value in prior.items():
            fields+=1
            if not eq(value,row.get(col)):
                if len(failures)<15:failures.append(f'{k} {col}: {value} != {row.get(col)}')
    return {'rows':len(actual),'fields_compared':fields,'csv_sha256_equal':sha(old)==sha(new),'mismatches':failures,'pass':not failures}

def call(label,command,log,env):
    with open(log,'w') as f:
        f.write('COMMAND: '+' '.join(command)+'\n');f.flush()
        p=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        f.write('EXIT: '+str(p.returncode)+'\n')
    if p.returncode:raise RuntimeError(f'{label} failed; see {log}')

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['smoke','full'],default='smoke')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--operator',default='');p.add_argument('--machine-description',default='')
    a=p.parse_args()
    if sys.version_info<(3,11):p.error('Python 3.11 or newer required')
    if a.out.exists():p.error('Output path exists; use a fresh empty path')
    dest=a.out.resolve();dest.mkdir(parents=True);logs=dest/'logs';logs.mkdir()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONNOUSERSITE='1')
    result={'status':'IN_PROGRESS','mode':a.mode,'operator_self_reported':a.operator,'machine_self_reported':a.machine_description,
            'operator_or_machine_independently_verified':False,'python':sys.version,'platform':platform.platform(),
            'start_utc':datetime.now(timezone.utc).isoformat(),'manifest_sha256':sha(ROOT/'SHA256SUMS'),'comparison':{}}
    try:
        call('manifest',[sys.executable,str(ROOT/'tools/verify_release.py')],logs/'verify_release.log',env)
        for label,script,old in [('primary','symmetric/run_symmetric.py','symmetric/primary/episodes.csv'),
                                 ('latency','symmetric/run_latency.py','symmetric/latency/episodes.csv')]:
            out=dest/label
            cmd=[sys.executable,str(ROOT/script),'--out',str(out)]
            if a.mode=='smoke':cmd.append('--smoke')
            call(label,cmd,logs/f'{label}.log',env)
            check=verify_subset(ROOT/old,out/'episodes.csv',a.mode=='smoke')
            if not check['pass'] or (a.mode=='full' and not check['csv_sha256_equal']):raise RuntimeError('Data mismatch: '+str(check))
            result['comparison'][label]=check
        result['status']='MATCHED__SELF_REPORTED_HOST'
    except Exception as e:
        result['status']='FAILED_OR_INCOMPLETE';result['error']=str(e)
    result['finish_utc']=datetime.now(timezone.utc).isoformat()
    (dest/'reproduction_result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'status':result['status'],'comparisons':{k:v['rows'] for k,v in result['comparison'].items()},'result':str(dest/'reproduction_result.json')},indent=2))
    return 0 if result['status']=='MATCHED__SELF_REPORTED_HOST' else 1

if __name__=='__main__':sys.exit(main())
