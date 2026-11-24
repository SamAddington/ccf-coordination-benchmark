# Additional settlement/delay sensitivity (candidate, not published)

The v1.1.0 candidate now includes 288 pipelined-claim episodes, 1,152 fixed-hop-delay episodes, and 288 fixed-mean/full-settlement episodes, with complete S1–S3 supplementary tables. These are exploratory, reused-world synthetic comparisons; no physical-host verification or public DOI for this extension is asserted.

# Proposed GitHub Release: CCF Coordination Benchmark v1.1.0 — Admission Pricing and Client Policy

**Candidate only — do not publish until the full author-run evidence gate is satisfied.**

## What this version adds

- 3,456 synthetic episode records in a 12-arm admission-pricing study across 12 authored worlds, three trials, four message-loss rates, and two deadlines.
- 9,072 priced delay/deadline episodes across 84 matched grid settings per contrast, with all summaries and descriptive bootstrap intervals.
- 288 settlement-ablation episodes distinguishing serial claim waiting from the modeled service guard cost.
- A common delayed completion-notification channel for all ideal and remote control-plane treatments; older datasets were **not overwritten**.
- Full episode-level raw data, charts, methods documentation, and SHA-256 manifest (including hidden `.github` and `.gitignore` files).
- Updated GitHub Actions smoke verification and explicit self-reported smoke reproduction audit.

## Bounded finding

At a 16-unit synthetic deadline and no message loss, remote advisory claims completed 71.3% of tasks when admission was free, compared with 46.1% for remote capacity permits. Charging claims for a separately modeled lossy service-admission RPC decreased their completion to 49.3%; at 35% loss, the priced claim and permit completion rates were 23.3% and 25.9%. These conditions are not production measurements. Claimed capacity safety comes from an authored atomic guard, not from a distributed execution proof.

## Reproduction

```bash
python3 tools/verify_release.py
python3 tools/reproduce_v28.py --mode smoke --out ../ccf_v28_smoke_01
python3 tools/reproduce_v28.py --mode full --out ../ccf_v28_full_01
```

The author-reported external Ubuntu/WSL2 smoke bundle matched 860 sampled episodes (18,144 values); a full author-operated rerun of the 12,816 new records remains pending. No third-party scientific replication is claimed.

## Provenance, DOI, and rights

- Earlier studies remain in the repository for provenance; they are not new independent observations.
- Copyright © 2026 Samuel Addington; original source, synthetic data, and figures licensed under MIT; third-party notices retained.
- Historical public v1.0.0 DOI: `10.5281/zenodo.24511437` (does **not** cover v1.1.0).
- **No new DOI has been assigned.** After the GitHub release is publicly archived, verify the actual Zenodo version DOI before updating citation metadata and the manuscript.
