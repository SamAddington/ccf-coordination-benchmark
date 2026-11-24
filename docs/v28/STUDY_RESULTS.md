# Admission-pricing experiment — bounded scientific interpretation

All data below come from the authored event-driven synthetic simulator; they are neither empirical deployed-system throughput nor independent simulation worlds. Full numerical records are in `symmetric/admission_*/`.

| Episode set | Records | Source runner | Frozen records |
|---|---:|---|---|
| Main admission comparison | 3,456 | `symmetric/run_admission.py` | `symmetric/admission_primary/episodes.csv` |
| Priced delay/deadline grid | 9,072 | `symmetric/run_priced_grid.py` | `symmetric/admission_priced_grid/episodes.csv` |
| Settlement-wait ablation | 288 | `symmetric/run_settlement_ablation.py` | `symmetric/admission_no_settlement/episodes.csv` |

At a 16-unit deadline, 0% loss, redirecting remote claims complete **71.3%** with free admission and **49.3%** with a separately modeled service-admission request/reply; remote permits complete **46.1%**. At 35% loss the corresponding figures are **57.3%**, **23.3%**, and **25.9%**. The priced claim-minus-permit gap is **+3.2 pp** (95% descriptive world-bootstrap interval −0.8 to +7.1) at zero loss and **−2.6 pp** (−4.7 to −0.2) at 35% loss.

The 84 priced-grid contrasts contain four negative mean estimates, of which only one descriptive interval is wholly below zero. In the separate no-settlement condition, priced claim completion increases from 49.3% to 60.0% (16 units; zero loss) with additional admission denials. This is a timing-policy sensitivity, not a new algorithmic claim.

**Important caveats:** same 12 reused generated worlds; descriptive unadjusted intervals; a model of the guard RPC (check upon applicant-side response, no real remote transaction); single non-crashing permit authority; unpriced local occupancy assertion for every arm; no external service or network measurements. A free control plane is an ideal upper bound and cannot establish comparable physical implementation cost.

**Reproduction:** local full/smoke tests passed; author-reported 860-episode *smoke only* uploaded and audited; no new public release DOI or full author-operated reproduction of v28 is asserted.
