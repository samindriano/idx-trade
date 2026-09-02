# INC-001 composite cash+share policy reconciliation — V1

Date: 2026-08-31 Asia/Jakarta  
Lane: `data/ca-aware-feature-basis-remediation-v1`  
Scope: exactly the four current V15 `UNKNOWN_TAXONOMY` `Mixed Dividend` events

## Controlling state

The authoritative predecessor is V15, not the stale lane-local coordination
copy:

```text
ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v15-distribution-wave
MANIFEST SHA-256 = d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025
SOURCE_EVIDENCE_ROWS = 412
ECONOMIC_EVENTS = 387
RESOLVED = 163
UNRESOLVED = 178
NON_BASIS = 46
PROVEN_LINKAGES = 27
```

The prior retained composite-evidence artifact is also verified:

```text
ROOT = D:\Documents\Project\idx-ca-unknown-taxonomy-adjudication-20260831-v1
MANIFEST SHA-256 = ee7ac86764f7edda8a5886e5697b128085b32eaf1b487a9d5eac1132413a88ca
```

## Policy decision

The four selected retained KSEI pages each contain same-date, `Active`,
same-issuer `Mixed Dividend` rows for a positive issuer-share entitlement and
an IDR cash entitlement. This is sufficient to classify the economic event as
`COMPOSITE_CASH_SHARE_DISTRIBUTION` with `BASIS_CHANGING` behavior. The cash
leg does not neutralize the positive share leg.

The composite economics are retained in provenance while the existing
`STOCK_DIVIDEND` basis contract is used for future basis handling. This is not
a new generic composite framework and does not add the family to the global
feature-basis coverage ontology. A label alone is insufficient; a positive
share leg is required.

| ticker | economic event | cash leg | share leg | retained evidence SHA-256 |
|---|---|---|---|---|
| CNMA | `DERIVED-4e2db5111bc0b70d5bd6b9e77cda6703dea8ff60d18a033787e75e04999e4d60` | `(50 CNMA : 7 IDR)` | `(50 CNMA : 1 CNMA)` | `e7656e6126b5be6091a805621de843b7f8bd2e72f500ecea5dac98ca86efc5d9` |
| KKGI | `DERIVED-893338349f1dc1ac85f83e9a5476f2a5967f5c28b0c4bdf26a20c28ae0264c92` | `(10000 KKGI : 15 IDR)` | `(10000 KKGI : 53 KKGI)` | `c674ef6469147656a057c09a617e5d95c9ea8e6761e4c75c4638f4d26ab55e78` |
| WINS | `DERIVED-7d3d4fb644bfac02abc1ff6f2aac5cb20c895eb1e0a571d42291759ea62a1ea8` | `(46 WINS : 2 IDR)` | `(46 WINS : 1 WINS)` | `d2269bfed3d9f14ba06160641904a75d4753db706a8946793359fbcc5302280f` |
| WINS | `DERIVED-ff06b7cd6b57d1c4d7a0b5b21a8d6e44bd0b493fc5e18aebc3960b26f3b6022f` | `(71 WINS : 2 IDR)` | `(71 WINS : 1 WINS)` | `d2269bfed3d9f14ba06160641904a75d4753db706a8946793359fbcc5302280f` |

No transition date is promoted. Candidate, record, distribution, publication,
or next-session dates remain insufficient for the accepted regular-market
transition contract. No new same-event linkage is created; the paired source
rows remain separately represented and are retained in the component ledger.

## Successor reconciliation

The one successor artifact was built by rerunning the existing reconciler from
the complete V15 ledgers plus exactly four source-bound proven adjudications.
The source rows, existing linkages, and transition attestations were not
rewritten.

```text
ARTIFACT_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260831-v16-composite-policy
ARTIFACT_MANIFEST SHA-256 = 3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030
BUILDER HEAD = ae63d9b9a9bf7f6a83a1758763da07624a6f0e78

BEFORE = 412 / 387 / 163 / 178 / 46 / 27
AFTER  = 412 / 387 / 163 / 178 / 46 / 27
UNKNOWN_TAXONOMY = 4 -> 0
COMPOSITE_CASH_SHARE_DISTRIBUTION = 0 -> 4
NEW_PROVEN_LINKAGES = 0
TRANSITIONS_PROMOTED = 0
```

Validation passed for all 412 source raw-byte hashes, all four target and
paired-share identities, same-date/active status, cash/share positivity,
collapse arithmetic, transition arithmetic, source conservation, and a
byte-identical deterministic replay. The artifact records
`basis_contract_family=STOCK_DIVIDEND` without changing the frozen feature
basis implementation.

## Scientific and operational boundary

```text
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
HISTORICAL_APPLICATION = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
PROVIDER_CALLS = FALSE
OUTCOMES_OR_TARGETS = FALSE
CANONICAL_HISTORICAL_REWRITE = FALSE
PRODUCTION_EXECUTION = FALSE
```

No outcome/model/refit/score work, provider call, production action, backfill,
counter or PaperState mutation, canonical historical rewrite, or merge occurred.

## Next bounded phase

Proceed to exactly the current `MERGER=5` retained-evidence review and, only
if retained evidence is insufficient, bounded event-specific official
acquisition. Merger semantics must not be treated as dividend Ex semantics.
After that, decompose the retained `CAPITAL_RESTRUCTURING=19` population. Do
not infer any market transition from dates, price movement, or unrelated
same-ticker evidence.
