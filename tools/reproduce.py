#!/usr/bin/env python3
"""Run and compare frozen v26 episodes from a repository clone (stdlib)."""
import argparse, csv, hashlib, json, math, os, platform, random, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 'v25':(4320,'v25/results/episodes.csv',('world_seed','trial_seed','controller','shield','physics','loss','horizon')),
 'primary':(2592,'fairness/results/episodes.csv',('world_seed','trial_seed','arm','loss','horizon')),
 'sensitivity':(1680,'fairness/sensitivity_results/episodes.csv',('world_seed','seed','study','arm','loss','horizon','ttl','settle_extra','claim_ttl','burst')),
}

def hashfile(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def rows(path):
    with Path(path).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def key(r,cols):return tuple(r.get(k,'') for k in cols)

def almost(a,b):
    if a==b:return True
    if a=='' or b=='':return False
    try:
        a=float(a);b=float(b)
        return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-9)
    except (ValueError,TypeError):return False

def compare(reference,actual,cols):
    old=rows(reference);new=rows(actual)
    oi={key(r,cols):r for r in old};ni={key(r,cols):r for r in new}
    if len(oi)!=len(old) or len(ni)!=len(new) or oi.keys()!=ni.keys():
        raise RuntimeError(f'Duplicate/mismatched episode keys: {reference} {actual}')
    bad=[];values=0
    for k,x in oi.items():
        y=ni[k]
        if set(x)!=set(y):raise RuntimeError(f'Columns differ for episode {k}')
        for f,v in x.items():
            values+=1
            if not almost(v,y[f]) and len(bad)<20:
                bad.append({'episode':k,'column':f,'expected':v,'actual':y[f]})
    return {'rows_expected':len(old),'rows_actual':len(new),'fields_checked':values,'mismatches':bad,
        'match':not bad,'bytes_identical':hashfile(reference)==hashfile(actual),
        'reference_sha256':hashfile(reference),'rerun_sha256':hashfile(actual)}

def execute(label,cmd,cwd,logs,env):
    path=logs/(label+'.log');start=time.monotonic()
    with path.open('w',encoding='utf-8') as f:
        f.write('COMMAND: '+' '.join(cmd)+'\n');f.flush()
        r=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,check=False)
        f.write('\nEXIT CODE: '+str(r.returncode)+'\n')
    if r.returncode:raise RuntimeError(f'{label} failed with code {r.returncode}; inspect {path}')
    return {'path':str(path),'exit_code':0,'duration_seconds':round(time.monotonic()-start,2)}

def run():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['smoke','full'],default='smoke')
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--operator',default='',help='Self-reported name; not authenticated')
    parser.add_argument('--machine-description',default='',help='Self-reported machine; not authenticated')
    a=parser.parse_args()
    if sys.version_info<(3,11):parser.error('Python >=3.11 required')
    out=a.out.resolve()
    if out.exists():parser.error('Output path exists; choose a fresh empty path')
    out.mkdir(parents=True);logs=out/'logs';logs.mkdir()
    env=dict(os.environ);env.update({'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','PYTHONNOUSERSITE':'1'});env.pop('SMOKE',None)
    report={'status':'IN_PROGRESS','mode':a.mode,'source':'git-clone local files',
        'operator':a.operator,'machine_description':a.machine_description,
        'independent_identity_certified':False,'platform':platform.platform(),
        'python':sys.version,'utc_start':datetime.now(timezone.utc).isoformat(),
        'repository_manifest_sha256':hashfile(ROOT/'SHA256SUMS'),
        'runner_sha256':hashfile(Path(__file__)),
        'runs':{},'comparison':{}}
    try:
        report['runs']['manifest']=execute('manifest',[sys.executable,str(ROOT/'tools/verify_release.py')],ROOT,logs,env)
        report['runs']['existing_verifier']=execute('existing_verifier',[sys.executable,str(ROOT/'fairness/verify_v26.py')],ROOT,logs,env)
        if a.mode=='smoke':
            env['SMOKE']='1';target=out/'smoke_primary'
            report['runs']['primary_sample']=execute('primary_sample',[sys.executable,str(ROOT/'fairness/run_fair_comparison.py'),str(target)],ROOT,logs,env)
            new=rows(target/'episodes.csv');ref=rows(ROOT/'fairness/results/episodes.csv')
            keys=EXPECTED['primary'][2];d={key(r,keys):r for r in ref}
            with (out/'smoke_reference.csv').open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=list(ref[0]));w.writeheader();w.writerows(d[key(x,keys)] for x in new)
            report['comparison']['primary_sample']=compare(out/'smoke_reference.csv',target/'episodes.csv',keys)
        else:
            for name,script in [('v25','v25/run_postreview_loss_sweep.py'),('primary','fairness/run_fair_comparison.py'),('sensitivity','fairness/sensitivity.py')]:
                target=out/('rerun_'+name)
                report['runs'][name]=execute('full_'+name,[sys.executable,str(ROOT/script),str(target)],ROOT,logs,env)
                size,ref,cols=EXPECTED[name]
                cmp=compare(ROOT/ref,target/'episodes.csv',cols)
                if cmp['rows_actual']!=size or not cmp['match']:raise RuntimeError('Mismatch in '+name+': '+str(cmp))
                report['comparison'][name]=cmp
            report['total_episodes']=sum(v[0] for v in EXPECTED.values())
            report['runs']['statistical_tables']=execute('statistical_tables',[sys.executable,str(ROOT/'tools/verify_tables.py'),
                '--episodes',str(out/'rerun_primary/episodes.csv'),
                '--cells',str(ROOT/'fairness/results/all_72_cells_with_intervals.csv'),
                '--contrasts',str(ROOT/'fairness/results/paired_world_contrasts.csv')],ROOT,logs,env)
        if not all(x['match'] for x in report['comparison'].values()):raise RuntimeError('One or more CSV mismatch')
        report['status']='RERUN_MATCHED__OPERATOR_AND_MACHINE_NOT_VERIFIED'
    except Exception as e:
        report['status']='FAILED_OR_INCOMPLETE';report['error']=f'{type(e).__name__}: {e}'
    report['utc_finish']=datetime.now(timezone.utc).isoformat()
    path=out/'reproduction_result.json';path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'mode':a.mode,'result':str(path),
                     'comparisons':{k:v.get('rows_actual') for k,v in report['comparison'].items()}},indent=2))
    return 0 if report['status']=='RERUN_MATCHED__OPERATOR_AND_MACHINE_NOT_VERIFIED' else 1
if __name__=='__main__':sys.exit(run())
