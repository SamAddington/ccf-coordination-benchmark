# CCF v26 — source and synthetic evaluation records

*Client Fallback and Control-Plane Placement Reverse Coordination Rankings Under Message Loss*

This is a **candidate** release of project-authored research software. The original CCF software, **author-generated synthetic datasets, and author-generated figures** are copyright (c) 2026 Samuel Addington and are licensed under the **MIT License** (see `LICENSE`, `LICENSE_SCOPE.md`, and `DATA_AND_FIGURES_MIT_NOTICE.md`). The experiments are synthetic; their reported results are not production-system measurements. Publication status is documented in `RELEASE_STATUS.md`. No real production or independent network service is exercised.

## Layout
- `v25/`: unchanged historical generator, engine, manager adapters and 4,320 synthetic records.
- `fairness/`: v26 fallback, colocation and remote-guard experiment scripts, 2,592 primary records (72 cells), plus 1,680 sensitivity records.
- `provenance/`: original study readme and original complete-ZIP checksum list retained for reference. The original root manifest includes excluded manuscript files, and is **not** the manifest of this candidate. Use `SHA256SUMS` for this candidate.
- `THIRD_PARTY_NOTICES.md`: external references and dependency license status.
- `DATA_AND_FIGURES_MIT_NOTICE.md`: express MIT grant for synthetic datasets and generated figures.

## Reproduce from an extracted archive (no external services needed)

Requires Python 3.11 or newer. With the extracted repository as the current directory:

```bash
python3 fairness/verify_v26.py
python3 v25/analyze_postreview_loss_sweep.py v25/results
```

For a full source rerun into **new folders** (do not overwrite historical records):

```bash
python3 v25/run_postreview_loss_sweep.py v25_reproduced
python3 v25/analyze_postreview_loss_sweep.py v25_reproduced
python3 fairness/run_fair_comparison.py fairness/reproduced_primary
python3 fairness/sensitivity.py fairness/reproduced_sensitivity
```

Reproduce manuscript plots (optional, needs separately installed Matplotlib): `python3 fairness/build_analysis.py`. The script may regenerate tracked PNGs; retain the original ZIP as immutable evidence.

## Provenance and claims

On a separately reported WSL2 AMD 7945HX machine, the author-operated reproduction script reported identical episode hashes for **8,592** episodes, with no mismatches and all archived verifier checks passing. An independent audit of the submitted logs confirmed internal consistency and matching source hashes, **not** authentication of the user or host. This is not third-party reproduction, not a production network benchmark, and not a public DOI deposit.

## Third-party materials

The referenced Lott–Honary repository is MIT-licensed but its upstream ACBBA.py source is not bundled here; see `THIRD_PARTY_NOTICES.md`. The research manuscript formatted using the IEEE Access template is not part of this candidate software archive.
