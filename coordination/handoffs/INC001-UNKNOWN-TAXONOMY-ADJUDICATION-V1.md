# Handoff: INC-001 retained-evidence taxonomy adjudication V1

from: local Codex continuation  
to: ChatGPT review / next authorized INC-001 action  
task_id: `INC001-UNKNOWN-TAXONOMY-ADJUDICATION-V1`  
lane: `data/ca-aware-feature-basis-remediation-v1`

## Review boundary

Review exactly the four current V15 unresolved `UNKNOWN_TAXONOMY` events:

```text
CNMA, KKGI, WINS (2025), WINS (2026)
ARTIFACT_ROOT = D:\Documents\Project\idx-ca-unknown-taxonomy-adjudication-20260831-v1
ARTIFACT_MANIFEST_SHA256 = ee7ac86764f7edda8a5886e5697b128085b32eaf1b487a9d5eac1132413a88ca
CONTROLLING_V15_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v15-distribution-wave
CONTROLLING_V15_MANIFEST_SHA256 = d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025
```

Only retained KSEI HTML bytes and the V15 ledgers were read. No provider call,
web search, retry, crawl, or new acquisition occurred.

## Result

```text
PROVEN_COMPOSITE_SHARE_DISTRIBUTION_REQUIRES_POLICY = 4
PROVEN_NON_BASIS = 0
PROVEN_STOCK_DIVIDEND = 0
PROVEN_BONUS_SHARES = 0
PROVEN_EXISTING_ECONOMIC_FAMILY = 0
RETAINED_EVIDENCE_TAXONOMY_INSUFFICIENT = 0
```

Every retained page explicitly contains same-date active issuer-share and IDR
legs under `Mixed Dividend`. That proves composite mechanics, not a policy
mapping to one existing family. No basis effect or regular-market transition
is promoted.

The paired existing `STOCK_DIVIDEND` source rows remain separate. No linkage is
added because same page/date/issuer adjacency does not satisfy the source-bound
event-binding contract.

## Reconciliation and controls

```text
BEFORE = 412 / 387 / 163 / 178 / 46 / 27
AFTER  = 412 / 387 / 163 / 178 / 46 / 27
NEW_PROVEN_LINKAGES = 0
SUCCESSOR_CREATED = FALSE
UNKNOWN_TAXONOMY_AFTER_CANONICAL_V15 = 4
```

`IDX_HISTORICAL_NEGATIVE_AUTHORITY=UNSUPPORTED`,
`IDX_HISTORICAL_ASOF_AUTHORITY=UNKNOWN`,
`KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY=UNKNOWN`,
`DATA_ADMISSION=FAIL`, `RESEARCH_ADMISSION=FAIL`, `PHASE_E_AUTHORIZED=FALSE`,
`REFIT_AUTHORIZED=FALSE`, and `COUNTER_ACTION=NONE` remain unchanged.

No outcomes, targets, Phase-E, model/refit/score, counter, PaperState,
production, backfill, canonical rewrite, or merge occurred. No application,
runtime, or science source code changed.

## Review decision requested

Review the immutable four-event artifact. Keep V15 unchanged. A future family
or policy action requires separate authorization; do not force-map `Mixed
Dividend`, infer a transition, or use this pass as historical negative
authority.
