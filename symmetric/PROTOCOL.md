# Symmetric synthetic coordination study (post-review extension)

This extension was specified and run **after critical feedback**. It is exploratory,
not externally preregistered, not independently validated on a second host,
and not a multi-host deployment. It preserves the original v1.0.0 code/data
under the unchanged `v25/` and `fairness/` directories.

## Primary design

- Generated worlds: indices 220–231, with 4, 6, or 8 agents and services;
  three paired trial seeds (71011–71013) per world. These worlds are reused
  from the v26 study, so new arms are paired on known synthetic settings,
  **not a new independent holdout**.
- Factors: family (service-level advisory claim, capacity permit),
  contention policy (redirect/fallback, sticky) and control plane
  (ideal zero-cost, modeled delayed/lossy); eight primary arms.
- Floors: independent task choice with local atomic guard, and independent
  task choice with a modeled two-hop guard. Both are contextual and **not**
  members of the 2x2x2 factorial.
- Loss: independent Bernoulli 0, 0.05, 0.20, 0.35 per attempted remote message;
  uniform remote one-hop delay U[0.35,0.95]; deadlines 16 or 54 model units.
- All arms use a local, instantaneous atomic capacity guard as a **shared
  control**, not a newly discovered safety theorem.
- Delayed claims wait `delay_max + 0.13` model units before the action attempt;
  ideal claims have no publication delay and zero settlement. Ideal manager
  request/grant/busy/cancel/release delivery is also lossless and instantaneous.
  In both families task-completion broadcasts retain the ordinary network model.
- Remote manager requests **including those addressed to a manager assigned
  to the same agent** are charged a remote hop and Bernoulli loss. This
  removes v1.0.0's hidden same-agent direct delivery for the new treatment.
  Authority assignment remains static; there is no Raft or remote host.
- Redirecting permit policy: after a BUSY or first retry timeout, best-effort
  CANCEL, temporarily exclude the contested service for 2.5 units, and
  choose another locally ranked task; cancellation can be delayed or lost.
- Sticky permit: resend the SAME nonce for the same service after timeout;
  BUSY backoff as in frozen v26. Stale-release handling and 8-unit permit TTL
  remain unchanged. Permit release messages are not guaranteed delivered.
- Redirecting claim: when a superior live service claim exists, reconsider
  all eligible tasks, including other services. A claim blocks the entire
  service irrespective of free multi-slot capacity and is not explicitly
  withdrawn. Claim TTL is 5 units; denied capacity attempts cool down the
  service for 0.48 units and wake after 0.22.
- Sticky claim (NEW modeled policy): retain the currently selected service
  for a 2.5-unit interval after claiming it, including when another claimant
  is superior; do not redirect to another service until the hold expires.
  This is an **experimental policy construction**, not canonical DRA.
- The claim scoring formula and all generated task values, durations,
  success draws and failure rules match the original CCF event engine.

**Important interpretation:** an ideal lossless broadcast to all claim peers
and an ideal service-local manager are *two optimistic bounds*, not equivalent
physical deployments. In particular, a free claim broadcast to multiple peers
would generally incur nonzero physical cost. The study compares model
assumptions, not algorithm-intrinsic throughput.

Primary episodes: 12 worlds x 3 seeds x 4 losses x 2 deadlines x 10 arms
= **2,880**, including the two contextual floors. No episodes discarded.
The full 10-arm condition grid contains 80 rows; there are 72 declared
paired contrasts, all evaluated using generated world clusters.

## Deterministic latency/deadline sensitivity

The second study holds the client policy to redirect for both families, and
uses a **fixed per-hop** remote delay of d in {0, 0.10, 0.25, 0.50, 0.95,
1.30, 1.80} time units. When d=0 the claim settlement increment is 0; when
it is positive the extra settlement is 0.13. Manager round trip is 2*d;
claim publication is one hop plus the settlement, so these are physically
*different message patterns under the same per-hop price*, not equalized
numbers of messages. The loss rate is 0 or 0.20 and horizon is 8, 12, 16,
24, 36, or 54. These are 12 worlds x 3 seeds x 2 losses x 6 horizons x
7 delays x 2 families = **6,048** episodes and 84 paired cells. This is
an experimental parameter sweep, not calibrated network latency.

## Inference and reproducibility

Complete-condition averages are episode means within the matched world set.
Descriptive intervals resample world-level means with replacement using 4,000
bootstrap replicates (seed 2602). World, rather than repetition/episode,
is the independent clustering unit. These intervals are not causal claims
or inferential evidence about real deployments. Missing/failing runs must
remain in the denominator and block comparisons for incomplete strata.

From the repository root:

```bash
python3 tools/verify_release.py
python3 tools/reproduce_v27.py --mode smoke --out ../ccf_v27_smoke_run1
python3 tools/reproduce_v27.py --mode full --out ../ccf_v27_full_run1
```

The old v26 data can still be reproduced separately with
`python3 tools/reproduce.py --mode full --out ../ccf_v26_full_run1`.
Never overwrite the archive's frozen results. The v1.0.0 release is at
https://github.com/SamAddington/ccf-coordination-benchmark/releases/tag/v1.0.0
and its historical Zenodo DOI is 10.5281/zenodo.24511437. No new v1.0.1 DOI
has been minted or verified as of package creation.
