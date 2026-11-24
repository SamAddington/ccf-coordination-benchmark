# CCF Coordination Benchmark

**Client Fallback and Control-Plane Placement Reverse Coordination Rankings Under Message Loss**  
Research software, synthetic evaluation records, and graphical analyses by Samuel Addington.

This repository holds a **simulation-based, exploratory** comparison of service-level claim protocols, remote permit managers, client fallback, and admission-guard placement under modeled message loss. The main finding is conditional: **the ranking of coordination approaches changes with client fallback and the communication location of the guard/manager.** It does not show that any approach is universally superior, nor does it measure a production service or autonomous penetration-testing agent.

> **Evidence limitations:** All experiments use author-defined synthetic tasks and service behavior. The original local-guard condition models an instantaneous, lossless capacity check; the remote-guard and colocated-manager arms change which messages are delayed or lost. Descriptive world-cluster intervals are not claims of cross-domain generalization. No production/independent distributed deployment was tested.

## Repository contents

| Path | Purpose |
|---|---|
| `v25/` | Earlier **4,320-episode** exploratory message-loss sweep; study source and original results |
| `fairness/run_fair_comparison.py` | **2,592-episode**, 72-cell primary fallback/placement comparison |
| `fairness/fair_engines.py` | Study-specific fallback and remote/colocated-control variants |
| `fairness/sensitivity.py` | **1,680-episode** timer, low-loss, burst-loss, and 16-agent sensitivity work |
| `fairness/results/` | Complete primary CSVs, summaries, descriptive intervals, and negative records |
| `fairness/sensitivity_results/` | Complete sensitivity records |
| `v25/results/` | Complete historical CSV and failure records |
| `fairness/figures/`, `v25/figures/` | Author-generated figures under MIT |
| `tools/` | Repository-integrity and independent-program consistency checks |
| `docs/` | Reproduction, methods, licensing, release instructions |
| `provenance/` | Preserved historical README, manifests, and packaging notes |
| `LICENSE`, `LICENSE_SCOPE.md` | MIT grant and explicit scope for code, data, and figures |

## Requirements

* CPython **3.11+**; no dependencies beyond Python's standard library for the core simulation, verification, and statistical checks.
* Optional figure recreation: `matplotlib==3.10.8` (recorded drawing environment). See `requirements-figures.txt`.
* No external services, network targets, cloud account, credentials, or secret tokens are needed.

## Quick verification (no experiment data overwritten)

From the repository root:

```bash
python3 tools/verify_release.py
python3 tools/reproduce.py --mode smoke --out ../ccf_smoke_run1
```

The verification checks repository file hashes and archived records. The smoke rerun checks a deterministic source sample against frozen results. **Choose a fresh output path for each attempt**; existing output directories are never overwritten.

## Full exact-data reproduction

```bash
python3 tools/reproduce.py --mode full --out ../ccf_full_run1
```

The full run regenerates **8,592 episodes** (4,320 historical + 2,592 primary + 1,680 sensitivity), compares every record and value to the frozen CSVs, and checks all **72** primary cells and **56** paired world contrasts. Logs, generated data, and a machine-readable verdict are saved *outside* the repository. The numerical checker does not authenticate the identity of the computer/operator or constitute independent third-party replication. More in [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## Figures

The PNG figures are distributed in the repository. Optional regeneration uses Matplotlib:

```bash
python3 -m pip install -r requirements-figures.txt
# This next script writes figures in the source tree; use a temporary clone if comparing against the frozen PNGs.
python3 fairness/build_analysis.py
```

## Research interpretation

The primary design crosses **9 controller/guard arrangements × 4 Bernoulli message-loss rates × 2 deadlines × 12 worlds × 3 trial seeds**, giving 2,592 episodes. Failure records are retained (zero recorded execution failures). The earlier 4,320 episodes and 1,680 sensitivity episodes have distinct purposes and **must not be pooled into a single independent-effect estimate**. See [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) for definitions and limitations.

**Author-reported reproduction:** A separately submitted Ubuntu/WSL2 run on an AMD 7945HX machine reported 8,592/8,592 matching episodes and zero failed executions. An audit verified the supplied runner fingerprint and logs; machine identity and operator control remain self-reported. The original raw operator logs are not included in this public source repository. This is not third-party replication.

## Licensing and citation

**Copyright © 2026 Samuel Addington.** MIT applies to the original code, author-generated synthetic CSV/JSON data, and author-generated PNG figures. See [LICENSE_SCOPE.md](LICENSE_SCOPE.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The publisher-formatted IEEE Access manuscript, IEEE logo/template, and third-party publications are **not included**. Use GitHub's **Cite this repository** control (from `CITATION.cff`) to cite the software. Update that file with a **real, verified version DOI only after** one is assigned.

Publication steps: [docs/GITHUB_PUBLISHING.md](docs/GITHUB_PUBLISHING.md) and [docs/ZENODO_ARCHIVING.md](docs/ZENODO_ARCHIVING.md). No repository URL, Zenodo DOI, third-party code license, or independent validation is invented here.

## Limitations

This is a research prototype and benchmark harness, not a production multi-agent controller. Results are model-specific and partially dependent on intentionally contrasted control-plane assumptions. The underlying simulation and script parameters, rather than an independently calibrated real-service workload, determine the performance outcomes. Please report the full experimental conditions when citing a number.
