# Admission-pricing validation protocol (prospective to earlier v27 runs)

Status: exploratory study; **author-reported separate-machine smoke check passed (860 samples), complete 12,816-episode author rerun still pending**. The
repository retains the v1.0.0 historical and v27 records without overwriting
any dataset. New scripts derive from v27 under the MIT license.

## Workload / statistical design

- Main study: 12 previously generated worlds (indices 220–231), 3 trial seeds
  (71011–71013), 4 independent Bernoulli message-loss probabilities
  (0, 5, 20, 35 percent), 2 horizons (16, 54), and 12 arms = 3456 episodes.
- Eight legacy 2x2x2 family/policy/control-plane arms; two **new** priced
  service-admission remote claim arms, plus local and network-priced independent
  floors. A full 2x2x2x2 statistical factorial is not claimed: under free
  control every admission placement is instantaneous, and permit-manager grant
  itself admits the work, so an extra service-guard hop would charge twice.
- Primary remote one-hop delay uniform U(0.35,0.95); fixed message loss per
  attempted hop. Separate 3-arm × 7 delay × 6 deadline × 2 loss × 12 world ×
  3 seed grid = 9072 episodes (84 paired cells per contrast).
- Another 288 episodes remove claim settlement but retain the service RPC.
- Bootstrap: 4000 draws with seed 2602 over 12 *world*-means (three trial
  seeds within each world). All intervals are descriptive and exploratory.
- Scope: simulated, non-Byzantine, non-crashing single authorities; no real
  HTTP service, measured bandwidth, external latency trace, consensus, or
  empirical outage risk. The full study still requires an author-run
  separate-machine reproduction before public release.

## Distinct admission mechanisms

1. Claim local baseline: broadcast service claim; wait delay_max+0.13 on remote
   plane; perform free atomic occupancy check at action start.
2. **Priced remote claim**: broadcast; settle as above; send a service-side
   check request over the lossy channel, await a separately lossy response.
   The occupancy check is made *when that response reaches the applicant*;
   its result is not an advance remotely reserved slot. Timeout is
   2×delay_max+0.4 units. Failed message delivery defers the action.
3. Permits: request/grant from a **service-local authority** acts as its
   reservation/admission; the event engine still checks the global capacity
   bound as a fail-closed invariant. No second redundant guard RPC is charged.
4. Free controls: claims and permits have zero cost for their respective
   *control* messages. For both, task-completion notifications use the common
   U(0.35,0.95) lossy channel. A prior adapter accidentally made those
   notifications zero-delay on the free plane; the new code corrects it and
   reports the changed means rather than altering historical data.
5. No-settlement sensitivity: claims broadcast and request remote admission
   immediately, without waiting for convergence. This is a different model
   policy, not a normal claim implementation. It increases concurrency and
   potentially duplicate attempts/denials. This bound challenges the decision
   to serialize settlement and guard RPCs.

### Limitations and safety

The admission guard is a deterministic shared occupancy test; zero modeled
capacity violations are **by construction** and not a demonstrated network
safety guarantee. Claim peers may disagree. Permits have a static local
service authority, not Raft or a production transaction. All trials use
synthetic tasks and shared generator assumptions. Unmatched message
semantics remain: broadcast vs request/grant; these experiments isolate
where their modeled costs are charged, not a universal intrinsic ranking.

## Core reproduction

```bash
python3 tools/verify_release.py
python3 tools/reproduce_v28.py --mode smoke --out ../ccf_v28_smoke_1
python3 tools/reproduce_v28.py --mode full --out ../ccf_v28_full_1 --operator "<name>" --machine-description "<computer>"
```

All output paths must be unused. The full run regenerates 3456 + 9072 + 288
new episodes and compares all CSV cells to frozen datasets. Preserve the
original reproduction_result.json, log files and generated CSVs from the
separate computer. The script is not identity authentication.

Public v1.0.0 GitHub and DOI 10.5281/zenodo.24511437 cover the *older* study
only. v1.1.0 in this archive is a **local proposed release version** and has no
public DOI or GitHub tag yet.
