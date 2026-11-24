# CCF v28 — response to the fourth-round simulated Reviewer 2 assessment

24 November 2026 | Author-preparation record; not an official journal review

## Overall revision

The manuscript was rebuilt around the reviewer’s decisive point: the earlier comparison priced **control messages** symmetrically but placed an instantaneous, lossless **admission** check on claims while permits already paid a request/grant exchange. The revised title is *Admission Pricing, Client Policy, and Completion in Service-Claim and Capacity-Permit Coordination: A Synthetic Comparison*. No general performance ranking or real-service safety claim is made.

### B1 — Admission-cost asymmetry (critical)

**Addressed through new evidence and new limits.** A priced remote-claim condition now transmits a service-admission request and response, each exposed to the same per-hop loss and delay distribution. Claims first complete their declared settlement interval and then request a check; a permit is already reserved/admitted by its service-local grant authority and is not charged a second identical RPC. This **does not** constitute perfect cost equivalence: claims still broadcast and settle, and the remote check is a modeled receipt-time oracle rather than a production transactional service. Both details are explicit in Section III, the protocol document and the threats section.

A 12-world, three-seed × four-loss × two-deadline study records 3,456 complete episodes and 96 completed arm-condition means. At 16 units and 0% loss, unpriced remote claims complete 71.3% against remote permits at 46.1%; with priced admission, claims complete 49.3% (paired gap +3.2 pp, 95% descriptive interval −0.8 to +7.1). At 35% loss, the respective means are 57.3%, 25.9%, and 23.3% (priced gap −2.6 pp, interval −4.7 to −0.2). Thus the large unpriced ranking does not survive admission pricing. No general advantage is claimed.

A second **9,072-episode** grid evaluates 84 paired delay/deadline/loss conditions; four mean priced claim-minus-permit gaps are negative and only one is wholly below zero by the exploratory, unadjusted world bootstrap. The 84 cells and intervals are in *Supplementary Table S1* and the archive. A **288-episode no-settlement** sensitivity retains service RPCs but omits claim waiting; completion rises from 49.3% to 60.0% at 16 units and 0% loss while modeled capacity denials increase. This probes the deliberate sequential waiting assumption rather than assuming it is canonical.

### B2 — Refuting an uncited prior ranking (critical framing)

**Reframed.** The introduction treats the unpriced/one-sided comparison as an **internal constructed diagonal of the same experiment**, motivated by established benchmark-sensitivity scholarship [1], [2], [24], [25]. The text does not suggest that a published external protocol claim has been falsified. The contribution is an evaluation of layer accounting in an authored simulator.

### M1 — New artifact absent (major)

**Local package delivered; external gate remains.** The v28 candidate ZIP includes all new scripts, generated CSV records, summaries, 84-grid contrasts, timing ablation, figures, checksums, and a smoke/full reproduction wrapper. Frozen historical v26/v27 data remain unchanged. An internal manifest checked 117 archive files and the clean-extracted smoke replay succeeded. The studies have **not** been author-operated on a second machine, a new GitHub tag has **not** been published, and no new DOI exists. The public v1.0.0 DOI (`10.5281/zenodo.24511437`) **does not cover v28**. These remain submission gates; they are disclosed, not asserted as complete.

### M2 — Client policy semantics not identical across families (major)

**Clarified.** Section III distinguishes claim retention from permit same-nonce retry and the redirecting permit’s CANCEL/cooldown. The full protocol/arms table includes priced admission and independent local/network floors. The manuscript no longer interprets these as a mathematically clean cross-family factorial policy effect.

### M3 — Selective grid/mechanism reporting (major)

**Addressed.** All 84 priced paired cells and their intervals appear in Supplementary Table S1. The core manuscript prints a representative latency/deadline table and all 12 primary mechanism arms at 16 units/0% loss. The complete primary data, 96 summary cells, paired contrasts and timing ablation are shipped in CSV; no failed episodes have been discarded.

### Minor points / additional correction

- **DONE-channel mismatch caught during audit:** v27 inadvertently set DONE latency to zero when the control plane was free. v28 explicitly applies the same U(0.35, 0.95) lossy DONE channel to all families/planes. This changes free-plane permit completion at 16 units/0% from 91.8% (v27) to 83.3% (v28), and claims from 96.4% to 96.6%; it is flagged as a correction, not a third-party confirmation.
- The full 84-cell priced grid contains four negative mean results, not an unsupported “no reversals” statement.
- The title/abstract, RQ answers, discussion and conclusion were rewritten around priced admissions, not a general ranking.
- Fixed study counts: 3,456 main + 9,072 grid + 288 timing sensitivity = 12,816 **new** attempted synthetic episodes, all completed. An older 17,520-record archive remains separate; neither set supplies independent experimental worlds.
- Table V labels A−B and gives both signs with descriptive world bootstrap intervals; Table VI includes the ten protocol variants and both independent floors.
- The main document keeps the IEEE Access April 2024 Word template structure, with an abstract within 150–250 words, an Acknowledgment AI disclosure, 7 tables, 3 figures, and source references; [25] now has pp. 101–109.
- The public historical v1.0.0 DOI has not been misapplied to the unpublished v28 extension.

## Remaining acceptance and release risks (not claimed solved)

1. All studies are synthetic and model-derived, with reused generated worlds rather than new held-out service workloads. The client-side simulated remote guard checks global state upon receipt: no real server-side transaction, durable reservation, remote crash, or physical network is evaluated.
2. Claim settlement followed by service request/reply is sequential; pipelining could change the cost. The no-settlement ablation bounds one alternative but is not an implemented overlapping protocol.
3. The release needs an **author-operated fresh-machine reproduction of the v28 code**, including complete hashes/logs, before claiming a separate-machine validation. No identity-verifying or third-party replication has occurred for v28.
4. The new MIT code/data/figures candidate needs a real GitHub release and distinct Zenodo version DOI, followed by checking the anonymous public download path. No publication was performed here.
5. The comparison supports an applied synthetic-methods or negative-result framing. Whether that is sufficient novelty for IEEE Access remains a reviewer/editor judgment.

**Recommendation:** retain as a v28 working submission candidate until the author-run and public release gates are completed. Do not describe it as accepted, production validated or independently replicated.
