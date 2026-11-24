# CCF Coordination Benchmark

**Admission and settlement timing in service-claim and capacity-permit coordination: a synthetic negative-result study**

Research software, generated synthetic datasets, and figures authored by Samuel Addington and distributed under the MIT License (2026).

> **Release state:** this snapshot is a **proposed v1.1.0 release candidate**. It has not been published as a new GitHub tag or archived under a new Zenodo DOI. The public [v1.0.0 release](https://github.com/SamAddington/ccf-coordination-benchmark/releases/tag/v1.0.0) and [its historical DOI](https://doi.org/10.5281/zenodo.24511437) remain unchanged and do **not** cover these later results.

## Research question and scope

This event-driven **synthetic** workload compares service-claim and capacity-permit coordination with redirecting/sticky clients and explicit modeled admission-message costs. An advisory claim that broadcasts then uses a free atomic guard may appear substantially better than a permit manager that pays to request capacity. Pricing claims' service-side admission request/reply removes most of that advantage in the tested workload; the resulting eight-cell completion gap is −3.0 to +4.4 percentage points. A pipelined claim request tests whether admission can overlap settlement, changing the modeled gap to 0.0 to +21.0 points. These results are a benchmark-sensitivity case study, not general protocol superiority, observed production throughput, a distributed lock theorem, or live autonomous cyber assessment.

The guard is an authored occupancy test, *not* a remotely transacting backend; the priced claim check takes effect upon reply at the applicant. The permit authority reserves capacity as part of its grant, so it is not charged a duplicate guard request. This is a declared architectural asymmetry whose sensitivity is studied, not a proof of perfect message equivalence.

## New admission-pricing extension (proposed v1.1.0)

| Frozen study | Records | Where |
|---|---:|---|
| Admission-pricing primary: 12 arms × 12 worlds × 3 trial seeds × 4 loss rates × 2 deadlines | 3,456 | `symmetric/admission_primary/` |
| Priced delay/deadline grid: 3 arms × 7 delays × 6 deadlines × 2 losses × 12 worlds × 3 trials | 9,072 | `symmetric/admission_priced_grid/` |
| Claim settlement ablation | 288 | `symmetric/admission_no_settlement/` |
| **Total new records** | **12,816** | `symmetric/` |

All 84 paired priced-grid contrasts and descriptive world-bootstrap intervals are in `symmetric/admission_priced_grid/paired_gaps.csv`.

**Added review-response timing/delay controls:** 288 pipelined claim episodes (`symmetric/settlement_overlap/`), 1,152 fixed-hop-delay comparisons (`symmetric/delay_kernel_controls/`), and 288 fixed-mean/full-settlement controls (`symmetric/fixed_mean_settlement/`). Full tables S1–S3 are in `symmetric/supplementary_review/` and `supplementary/`. See `docs/v29/PROTOCOL_AND_LIMITATIONS.md` for exact rules and boundaries. The three relevant figures are in `symmetric/admission_figures/`. Read [the protocol](docs/v28/ADMISSION_PRICING_PROTOCOL.md) and [experiment summary](docs/v28/STUDY_RESULTS.md) before interpreting the outcomes.

The preceding historical studies are retained *unchanged* in `v25/`, `fairness/`, `symmetric/primary/`, and `symmetric/latency/`; do not pool them as independent confirmations of the admission-pricing experiment. The repository name and directory version labels describe development provenance, not separately validated systems.

## Verify on Linux/macOS/WSL (Python 3.11+)

From this repository's root (core requires only the Python standard library):

```bash
python3 tools/verify_release.py
python3 tools/reproduce_v28.py --mode smoke --out ../ccf_v28_smoke_01
```

Choose an **unused** output directory. Neither command alters the frozen datasets. For the full 12,816-record exact-data replay:

```bash
python3 tools/reproduce_v28.py --mode full --out ../ccf_v28_full_01 \
  --operator "YOUR NAME" --machine-description "YOUR OS/HARDWARE"
```

The full run compares every CSV value and requires byte-identical dataset hashes. Logs and results are saved outside the repository. Optional plotting uses `matplotlib==3.10.8` from `requirements-figures.txt`; regenerate figures only in a throwaway clone, since that script writes figure paths. See [reproduction documentation](docs/REPRODUCIBILITY.md).

## Current reproduction evidence

- The source authoring environment completed a clean-extraction full run and manifest checks. These are **same-host** checks.
- The author submitted an Ubuntu/WSL2 **smoke-mode** evidence bundle on 24 November 2026. An audit found 860 of 860 sampled episodes and 18,144 field values matching their frozen references, with 21 internal evidence hashes verified. The operator and machine identity are **self-reported**; the full author-operated 12,816-episode run has **not** been submitted. See [scope-limited smoke evidence](docs/v28/AUTHOR_SMOKE_AUDIT.md).
- The earlier v1.0.0 study had its own full author-reported Ubuntu/WSL2 reproduction. It does not verify this added study.

## Full review-response reproduction

```bash
python3 tools/reproduce_v29.py --mode smoke --out ../ccf_v29_smoke_01
python3 tools/reproduce_v29.py --mode full --out ../ccf_v29_full_01 \
  --operator "YOUR NAME" --machine-description "YOUR REAL OS AND HARDWARE"
```

Choose a fresh output path for every run. Both modes verify the original admission data and the new timing/delay records; the full mode also reconstructs all supplementary tables and retains logs outside the repository. Local replay is **not** independent third-party replication. Read `docs/v29/AUTHOR_REPRODUCTION_AND_RELEASE.md`.

## Licensing and citation

Copyright © 2026 Samuel Addington. The MIT License covers original source, synthetic data, and author-generated figures. See `LICENSE`, `LICENSE_SCOPE.md`, `DATA_AND_FIGURES_MIT_NOTICE.md`, and `THIRD_PARTY_NOTICES.md`. No IEEE-branded publisher manuscript or third-party full-text paper is bundled.

Use `CITATION.cff` for software citation. **The new v1.1.0 version DOI is intentionally absent pending deposit.** Cite the historical v1.0.0 DOI only for that older artifact. See [publication steps](docs/GITHUB_PUBLISHING.md) and [release status](RELEASE_STATUS.md).
