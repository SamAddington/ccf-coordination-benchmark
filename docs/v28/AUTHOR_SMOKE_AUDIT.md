# Author-reported Ubuntu/WSL2 smoke audit — 24 November 2026

**Evidence level:** independently examined *uploaded records*, not independently authenticated hardware or operator. This is a source/reproduction consistency check, not physical service validation.

| Check | Observed |
|---|---:|
| Primary sampled episodes | 96 / 96 matched |
| Priced-grid sampled episodes | 756 / 756 matched |
| Settlement sampled episodes | 8 / 8 matched |
| **Total sampled episodes** | **860 / 860 matched** |
| Individual field values | **18,144 matched** |
| Internal evidence SHA-256 entries | 21 / 21 verified |
| Execution logs | Five exit-zero logs |
| Mode | `smoke` |
| Operator / machine | Author self-report; not independently authenticated |

The frozen reference archive SHA-256 recorded in the audit is `35e21cfe2e47127f1760c208bbf22a87e7c64a9adc2cd4887663fc396851e529`. The evidence TAR digest was `743340f01fe153b15dc8948365068127b32f0635fa9522177b7c97b8bd1672e0`.

Smoke mode produces subset CSVs; their SHA-256 values **must not** equal the complete reference CSV hashes. Each sampled row and field matched its frozen reference. No anomalous execution errors were observed in the uploaded five logs. The raw operator TAR and unsigned attestation are not bundled in this public source snapshot.

**Unfinished:** a full author-run reproduction of 3,456 + 9,072 + 288 = **12,816** episodes, uploaded with untouched full logs and a completed author attestation. Neither successful smoke testing nor earlier v1.0.0 full reruns satisfy this gate.
