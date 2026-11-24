# Reproducibility guide

The original source and frozen records are committed in `v25/` and `fairness/`. **Do not edit them for verification.** Python 3.11+ is required. The core uses the Python standard library; Matplotlib is only for plotting.

## Basic verification

```bash
python3 tools/verify_release.py
python3 tools/reproduce.py --mode smoke --out ../ccf_smoke_01
```

## Full reproduction

```bash
python3 tools/reproduce.py --mode full --out ../ccf_full_01 \
    --operator "YOUR NAME" --machine-description "MACHINE AND OS"
```

The full-mode script regenerates 4,320 historical, 2,592 primary and 1,680 sensitivity episodes and compares each CSV field to the archived reference using a strict numeric tolerance (relative `1e-10`, absolute `1e-9`). It also checks 72 primary cells and 56 world-cluster contrast summaries, including 744 statistical values. The resulting `reproduction_result.json` includes numerical results, runtime version, platform, file hashes, and individual logs. It cannot independently certify user or hardware identity.

All runs use **new output paths** and refuse to overwrite existing directories, including the frozen source records. If rerunning on your own machine, preserve the unmodified output and the source commit hash for any publication audit.

An author-reported Ubuntu WSL2 run under AMD 7945HX and CPython 3.14.4 regenerated all 8,592 episodes and submitted logs; a subsequent consistency audit compared script and source hashes to the frozen package. Operator/hardware identity remains self-reported. Third-party replication remains an open activity.

## Plot replication

Figures provided are original author-generated PNGs under the project's MIT license. If you choose to regenerate them, use Matplotlib 3.10.8 (when available) and a **temporary clone**; the original plotting script may overwrite the tracked PNGs:

```bash
python3 -m pip install -r requirements-figures.txt
python3 fairness/build_analysis.py
```

## Expected checks

- Historical: 4,320 records
- Primary: 2,592 records and 72 treatment cells
- Sensitivity: 1,680 records
- Total: **8,592** records
- 56 paired world-cluster contrasts and 744 derived quantities
- Exact source/dataset fingerprints in `SHA256SUMS` and the new run report

The files are **synthetic**, not traces collected from an operational organization. Local/remote losses and delays are simulator settings.


## Proposed v1.1.0 admission-pricing extension (not the historical v1.0.0 DOI)

The new experiment keeps the frozen historical source and adds **3,456 primary + 9,072 priced-grid + 288 settlement = 12,816** synthetic episodes. Run:

```bash
python3 tools/verify_release.py
python3 tools/reproduce_v28.py --mode smoke --out ../ccf_v28_smoke_01
python3 tools/reproduce_v28.py --mode full --out ../ccf_v28_full_01 \
  --operator "YOUR NAME" --machine-description "YOUR OS/HARDWARE"
```

Use a fresh output directory for each run. Smoke mode checks **860 samples** rather than the whole dataset and therefore does not produce matching full CSV SHA-256 values. The full mode checks 12,816 records and requires identical dataset hashes.

**Evidence as of 24 November 2026:** A submitted author-reported AMD 7945HX Ubuntu/WSL2 smoke run was audited against the frozen source: 860 records, 18,144 values, 21 internal evidence hashes, and five exit-zero logs matched. Operator and hardware identity are self-reported. The new full author-run and an independently operated third-party reproduction are not completed; see `docs/v28/AUTHOR_SMOKE_AUDIT.md`.

The baseline repository tag `v1.0.0` / Zenodo `10.5281/zenodo.24511437` refers only to the earlier datasets, not to these newly added experiments. Do not cite a new DOI until a new tag has been deposited and its version DOI has been verified.
