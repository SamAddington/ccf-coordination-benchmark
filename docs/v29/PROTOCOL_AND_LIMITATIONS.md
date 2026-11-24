# Settlement-order and delay-kernel controls: methods and limits

**Research status:** Exploratory synthetic analysis conducted after feedback, using the same 12 generated worlds (indices 220–231), three trial seeds (71011–71013), previously defined protocol families and task outcomes. This is not an externally registered, independent-world or deployed-service experiment.

## Source code

- `symmetric/admission_symmetric.py`: frozen earlier sequential service-priced claim code; read without edits.
- `symmetric/pipelined_admission.py`: added claim/gate request pipelining; starts an admission request on claim publication, not after settlement; execution occurs only after BOTH settlement and a two-hop acknowledgment. It does not reserve capacity at request time; the simulated occupancy check occurs on action start. Lost replies/timeouts, preempted claims, and DONE notices cancel stale work. The code is a study-specific policy variation, not a service-side lock or safety proof.
- `symmetric/run_overlap_ablation.py`: full 288-episode pipelining factorial (12 worlds × 3 seeds × 4 Bernoulli loss rates × 2 deadlines).
- `symmetric/run_settlement_ablation.py`: frozen 288-episode no-settlement control.
- `symmetric/run_delay_kernel_controls.py`: new fixed hop delays d=0.65 (uniform mean) and 0.95 (uniform maximum), 2 arms × 2 delays × 12 worlds × 3 seeds × 4 losses × 2 deadlines = 1,152 episodes. Uses settle=d+0.13 for d>0.
- `symmetric/run_fixed_mean_settlement_control.py`: 288 new claim episodes at fixed d=0.65 but full original 1.08-unit claim settlement; separates changes in the delay law from changes in the nominal waiting interval.
- `symmetric/analyze_review_settlement.py`: emits tables S1 (all 84 deterministic-grid claim/permit comparisons), S2 (all eight sequential/no-settlement/pipelined/sticky cells, with paired world bootstrap intervals), and S3 (fixed/stochastic delay comparisons).

## Eight-cell outcomes and causal boundary

The primary sequential service-priced claim minus remote permit gap ranges **−3.0 to +4.4 percentage points**. Both 35%-loss cell means are negative: 16 units −2.6 (95% descriptive world-cluster bootstrap interval −4.7 to −0.2); 54 units −3.0 (−7.8 to +2.1). Only the first interval lies wholly below zero.

The family-specific sticky claim-minus-permit gap is **+3.1 to +17.2** points in the same eight cells. Pipelined redirecting claims versus the unchanged remote permit complete with a gap **0.0 to +21.0** points; no-settlement claims yield **0.0 to +13.9**. Pipelining therefore tests a consequence of overlap, not intrinsic superiority; it can change event ordering, message losses sampled, candidate selection, and capacity denials.

The deterministic delay grid is not the main experiment with one parameter replaced: the main uses per-attempt independent U(.35,.95) hops while settlement is fixed at 1.08; the grid sets fixed d and settlement=d+0.13. At 16 units and 0% loss the gap is +3.2 in the main; +6.7 for fixed d=.65 and full 1.08 wait; +9.8 for fixed d=.65 and shortened .78 wait; and +11.2 for fixed d=.95 and full 1.08 wait. Different message arrival/event ordering is a plausible additional influence, not uniquely estimated by these tests.

## Inference and integrity

- The world is the cluster, and 3 seeds are nested within each of 12 worlds.
- Reported intervals are 4,000 world bootstrap resamples (seed 2602); exploratory and not multiplicity-adjusted.
- All failures remain in the raw tables; none were observed in new episodes.
- Every modeled service starts with an artificial occupancy guard; this does not establish a novel or deployed safety mechanism.
- No real servers, independent traces, multi-host coordination, physical clock skew, external attack traffic, or validation of operational availability are included.

## Review-source and repository URLs

This is a **proposed** MIT-licensed v1.1.0 release extension; it is not yet public or assigned a new Zenodo DOI. The historical v1.0.0 GitHub release and DOI `10.5281/zenodo.24511437` do not include these added conditions.
