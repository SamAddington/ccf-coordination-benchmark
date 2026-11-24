#!/usr/bin/env python3
"""Refresh the SHA256SUMS file for a new uncommitted release candidate."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p != ROOT/'SHA256SUMS' and not any(x in {'.git','__pycache__'} for x in p.relative_to(ROOT).parts))
text=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files)
(ROOT/'SHA256SUMS').write_text(text)
print(f'Wrote manifest for {len(files)} files')
