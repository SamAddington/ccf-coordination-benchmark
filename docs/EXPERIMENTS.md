# Methods and scope

## Episode sets

| Dataset | Factors | Episodes | Interpretation |
|---|---|---:|---|
| Historical study (`v25/results/`) | 12 worlds × 3 trials × 5 loss levels × 2 horizons × 2 admission controls × 2 synthetic stress laws × 3 controllers | 4,320 | Historical exploratory sweep; different treatment design from primary study |
| Primary comparison (`fairness/results/`) | 12 worlds × 3 trials × 4 loss levels × 2 horizons × 9 arms | 2,592 | Comparative fallback and modeled communication-placement experiment |
| Sensitivity (`fairness/sensitivity_results/`) | Low-loss, TTL, claim timing, 16-agent scale, burst-loss probes | 1,680 | Separate sensitivity analyses; not a replacement for a deployed-network study |

All episode records and failed-attempt records are retained. `fairness/results/all_72_cells_with_intervals.csv` reports all 72 primary treatment conditions. `fairness/results/paired_world_contrasts.csv` provides 56 paired world-cluster contrasts.

## Main arms

| Key | Meaning |
|---|---|
| `claim_local` | Service-scoped claim coordinator, idealized local admission guard |
| `claim_remote` | Same claim coordinator, admission request/reply on lossy transport |
| `independent_local` | Independent task choice, idealized local guard |
| `independent_remote` | Independent choice, modeled remote admission |
| `permit_sticky` | Sharded multi-permit manager, sticky client, remote lossy handshake |
| `permit_fallback` | Same manager with bounded alternative-service fallback |
| `permit_fallback_retx` | Fallback plus specified release retransmissions |
| `permit_colocated` | Sharded manager co-located, modeled lossless/immediate manager communication |
| `permit_colocated_fallback` | Colocated manager and fallback client |

**The study changes more than protocol identity.** Differences between local and remote guard conditions, fallbacks, and co-location should be read as modeled design choices, not a head-to-head algorithm leaderboard. A protocol may require different numbers of transmissions and experience different loss opportunities. The local admission check is an idealized zero-message guard, not evidence that real capacity checks are free.

## Outcomes

Task completion, message publications, delivery losses, admission-related counters, and synthetic disruptions are stored per episode in the CSV. `overcapacity_admissions` is driven by the authored admission model and is **not** a measured external-service outage. In the primary experiment the guard controls modeled capacity; the result is useful as a check of this implementation, not a new safety theorem.

Confidence intervals are **descriptive world-cluster bootstrap intervals**, based on 12 generated worlds. Repeated trial seeds within one world are not 36 independent worlds. Sensitivity/early studies are not pooled as if exchangeable with the primary experiment.

## Source and reproducibility constraints

Read `fairness/run_fair_comparison.py`, `fairness/fair_engines.py`, and the archived `v12` and `v14` modules for exact retry/timer and authorization behavior. The synthetic event engine is included under the historically named `v25/source/CCF_v15_Reproduction_Candidate_20261123/` directory for unchanged imports and provenance; the name does **not** make it an independent operational validation.

The source includes no real cloud deployment, credentialed cyber assessment, multi-host etcd replication, physical service calibration, or human-subject data.
