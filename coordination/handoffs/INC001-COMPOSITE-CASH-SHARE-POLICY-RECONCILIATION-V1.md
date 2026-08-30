# Handoff: INC-001 composite cash+share policy reconciliation V1

from: local Codex continuation  
to: ChatGPT review / next authorized INC-001 action  
task_id: `INC001-COMPOSITE-CASH-SHARE-POLICY-RECONCILIATION-V1`  
lane: `data/ca-aware-feature-basis-remediation-v1`

## Result

Phase A is complete for exactly four retained KSEI `Mixed Dividend` events.
The authoritative successor artifact is:

```text
ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260831-v16-composite-policy
MANIFEST SHA-256 = 3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030
BUILDER HEAD = ae63d9b9a9bf7f6a83a1758763da07624a6f0e78
PREDECESSOR V15 MANIFEST = d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025
```

The policy classification is:

```text
COMPOSITE_CASH_SHARE_DISTRIBUTION = 4
BASIS_EFFECT = BASIS_CHANGING
BASIS_CONTRACT_FAMILY = STOCK_DIVIDEND
TRANSITION_STATUS = UNRESOLVED for all 4
UNKNOWN_TAXONOMY = 4 -> 0
NEW_LINKAGES = 0
```

All source and paired-share raw bytes are hash-matched. Cash and share ratios,
source identity, date set, and active status are preserved in
`composite_component_ledger.csv`. A positive share leg is required; cash does
not neutralize the basis effect; the source label alone is insufficient. No
transition date is inferred.

## Reconciliation controls

```text
BEFORE = 412 / 387 / 163 / 178 / 46 / 27
AFTER  = 412 / 387 / 163 / 178 / 46 / 27
SOURCE_ROWS_PRESERVED = PASS
ALL_412_RAW_HASHES = PASS
TARGET_COMPONENT_PROVENANCE = PASS
SOURCE_CONSERVATION = PASS
COLLAPSE_ARITHMETIC = PASS
TRANSITION_ARITHMETIC = PASS
DETERMINISTIC_REPLAY = PASS
```

The existing feature-basis family coverage ontology and frozen science files
were not changed. The reconciler gained only the explicit composite family in
its basis-changing classification set; the existing basis contract remains
`STOCK_DIVIDEND` and no generic composite algebra was introduced.

## Guardrails and next phase

`DATA_ADMISSION=FAIL`, `RESEARCH_ADMISSION=FAIL`,
`HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN`, `REFIT_AUTHORIZED=FALSE`,
and `COUNTER_ACTION=NONE` remain in force. No provider/network request,
outcome/model access, production action, canonical history rewrite, backfill,
counter/PaperState mutation, or merge occurred.

Next bounded scope is exactly `MERGER=5`: review retained official evidence,
then acquire only event-specific official evidence if retained material is
insufficient. After that, decompose `CAPITAL_RESTRUCTURING=19`. A future final
read-only closure-feasibility audit remains separate from model Phase-E.
