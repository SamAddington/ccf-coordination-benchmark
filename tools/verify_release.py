#!/usr/bin/env python3
"""Validate the proposed v1.1.0 repository manifest and all frozen data counts (stdlib)."""
from pathlib import Path
import hashlib, json, sys, csv
ROOT=Path(__file__).resolve().parents[1]

def hashfile(path):
    h=hashlib.sha256()
    with path.open('rb') as inp:
        for chunk in iter(lambda: inp.read(1048576),b''):
            h.update(chunk)
    return h.hexdigest()

def run():
    root=ROOT.resolve()
    manifest=root/'SHA256SUMS'
    if not manifest.is_file(): raise RuntimeError('Missing SHA256SUMS')
    paths=set(); checked=0
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        h,rel=line.split(None,1)
        if len(h)!=64 or any(c not in '0123456789abcdef' for c in h.lower()):raise RuntimeError('Bad SHA256 entry')
        path=Path(rel.strip().lstrip('*'))
        if path.is_absolute() or '..' in path.parts or path.as_posix() in paths:
            raise RuntimeError(f'Invalid or duplicated relative manifest path: {path}')
        dest=root/path
        if not dest.is_file() or dest.is_symlink() or not dest.resolve().is_relative_to(root):
            raise RuntimeError(f'Missing or unsafe file: {path}')
        actual=hashfile(dest)
        if actual.lower()!=h.lower():raise RuntimeError(f'Checksum mismatch: {path}')
        paths.add(path.as_posix());checked+=1
    actual_files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and not p.is_symlink()
                  and p.relative_to(root).as_posix()!='SHA256SUMS'
                  and '.git' not in p.relative_to(root).parts
                  and '__pycache__' not in p.relative_to(root).parts
                  and not p.name.endswith(('.pyc','.pyo'))}
    if paths!=actual_files: raise RuntimeError(f'Manifest inventory mismatch: missing={sorted(actual_files-paths)} extra={sorted(paths-actual_files)}')
    expected={
       'v25/results/episodes.csv':4320,
       'fairness/results/episodes.csv':2592,
       'fairness/sensitivity_results/episodes.csv':1680,
       'symmetric/primary/episodes.csv':2880,
       'symmetric/latency/episodes.csv':6048,
       'symmetric/admission_primary/episodes.csv':3456,
       'symmetric/admission_priced_grid/episodes.csv':9072,
       'symmetric/admission_no_settlement/episodes.csv':288,
       'symmetric/settlement_overlap/episodes.csv':288,
       'symmetric/delay_kernel_controls/episodes.csv':1152,
       'symmetric/fixed_mean_settlement/episodes.csv':288,
    }
    for path,n in expected.items():
       with (root/path).open(encoding='utf-8',newline='') as f:
           rs=list(csv.DictReader(f))
       if len(rs)!=n:raise RuntimeError(f'Unexpected row count for {path}: {len(rs)} != {n}')
    report={'pass':True,'sha256_files_checked':checked,'episode_counts':expected,
            'total_episodes':sum(expected.values()),'release':'proposed v1.1.0 candidate (not published); MIT original code/data/figures; exploratory synthetic benchmark'}
    print(json.dumps(report,indent=2));return report
if __name__=='__main__':
    try:run()
    except Exception as e:
        print(f'RELEASE VERIFICATION FAILED: {e}',file=sys.stderr);sys.exit(1)
