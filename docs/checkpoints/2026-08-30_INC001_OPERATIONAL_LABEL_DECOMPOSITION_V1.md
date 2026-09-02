# INC-001 retained operational-label decomposition — V1

Date: 2026-08-30 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
Scope: exactly the 47 unresolved operational-label economic events in V14

## Authority and evidence boundary

The controlling reconciliation is unchanged:

```text
ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact
MANIFEST SHA-256 = c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b
SOURCE_EVIDENCE_ROWS = 412
ECONOMIC_EVENTS = 387
RESOLVED = 160
UNRESOLVED = 181
NON_BASIS = 46
PROVEN_LINKAGES = 27
```

This pass used only the retained V14 economic/source ledgers and the
hash-bound raw KSEI HTML paths referenced by those ledgers. No web, live
IDX/KSEI request, issuer search, provider retry, URL guessing, outcome/target
access, Phase-E, model work, counter mutation, canonical rewrite, or
production execution occurred.

## Exact result

All 47 selected events are single-source KSEI
`KSEI_REGISTERED_SECURITY_HISTORY` rows whose native label is exactly
`Voluntary Conversion`. Every retained raw path exists and its SHA-256 matches
the source-ledger evidence hash. The retained rows expose no ratio, left/right
security, or left/right value fields. Two rows also carry a record date and all
47 carry a distribution date; neither date is promoted to economic semantics
or an accepted regular-market transition.

```text
OPERATIONAL_LABEL_BEFORE = 47
PROVEN_NON_BASIS = 0
PROVEN_STOCK_SPLIT = 0
PROVEN_REVERSE_SPLIT = 0
PROVEN_RIGHTS_HMETD = 0
PROVEN_TRUE_SECURITY_CONVERSION = 0
PROVEN_CAPITAL_RESTRUCTURING = 0
PROVEN_OTHER_EXISTING_FAMILY = 0
SEMANTIC_INSUFFICIENT = 47
OPERATIONAL_LABEL_AFTER = 47
```

The event-level retained-evidence table is:

```text
D:\Documents\Project\idx-ca-operational-label-decomposition-20260830-v1\operational_label_decomposition.csv
```

Each row preserves the economic-event ID, ticker, original operation label,
source reference, evidence SHA-256, raw path/row index, retained dates and
ratio fields, current/provisional family, adjudicated basis state, exact
transition state, raw-hash checks, reason/evidence, and final classification.
The correct adjudication is not an economic family: `SEMANTIC_INSUFFICIENT`.
The V14 `UNRESOLVED_OPERATIONAL_LABEL` family and `UNRESOLVED` transition
state remain unchanged.

## Linkages and unresolved geometry

```text
PRIOR_PROVEN_LINKAGES = 27
RECOMPUTED_PROVEN_LINKAGES = 27
NEW_PROVEN_LINKAGES = 0
REMOVED_OR_CONFLICTING = 0
```

Unresolved family counts after the pass remain:

```text
RIGHTS_HMETD 68
UNRESOLVED_OPERATIONAL_LABEL 47
CAPITAL_RESTRUCTURING 19
STOCK_SPLIT 15
BONUS_SHARES 11
STOCK_DIVIDEND 7
MERGER 5
TRUE_SECURITY_CONVERSION 4
UNKNOWN_TAXONOMY 4
REVERSE_SPLIT 1
```

No reconciliation successor was created because the retained evidence did not
prove any permitted economic family, basis transition, or linkage change.

## Validation and verdict

```text
ARTIFACT_ROOT = D:\Documents\Project\idx-ca-operational-label-decomposition-20260830-v1
MANIFEST SHA-256 = 4a540a73816817ba714c1e13e644d1e6938cb7b57bd4677e94c6dac68b0ba2d1
DETERMINISTIC_COMPARISON = PASS (5/5 output files, zero differences)
V14_OUTPUT_HASH_AUDIT = PASS
RAW_PATH_AND_SHA_AUDIT = PASS (47/47)
RAW_LABEL_AND_DATE_PRESENCE = PASS (47/47)
RATIO_AND_RECEIVING_SECURITY_FIELDS_BLANK = PASS (47/47)
```

```text
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
NEXT_ACTION_RECOMMENDATION = PARK_REMAINING_OPERATIONAL_LABELS
```

This checkpoint stops the operational-label lane. No external acquisition or
other CA-family research is authorized by this result.
