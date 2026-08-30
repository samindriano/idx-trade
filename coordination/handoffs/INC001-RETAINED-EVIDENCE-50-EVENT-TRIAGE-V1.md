# Handoff: INC-001 retained-evidence 50-event triage V1

from: local Codex continuation  
to: ChatGPT review / next authorized INC-001 action  
task_id: `INC001-RETAINED-EVIDENCE-50-EVENT-TRIAGE-V1`  
lane: `data/ca-aware-feature-basis-remediation-v1`

## Review boundary

Review the single retained-evidence artifact for exactly these 50 V14 events:

```text
CAPITAL_RESTRUCTURING 19
BONUS_SHARES 11
STOCK_DIVIDEND 7
MERGER 5
TRUE_SECURITY_CONVERSION 4
UNKNOWN_TAXONOMY 4
```

Artifact:

```text
ROOT = D:\Documents\Project\idx-ca-retained-evidence-triage-20260830-v1
EVENT_TABLE = D:\Documents\Project\idx-ca-retained-evidence-triage-20260830-v1\event_triage.csv
MANIFEST = D:\Documents\Project\idx-ca-retained-evidence-triage-20260830-v1\MANIFEST.json
INPUT_RECONCILIATION_MANIFEST = c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b
```

The table has 50 unique IDs, 50/50 retained source-evidence hash matches,
and zero proven duplicate/linkage changes. The controlling V14 counts remain
412 source rows, 387 economic events, 160 resolved, 181 unresolved, 46
non-basis, and 27 proven linkages. No reconciliation successor was created.

## Findings

```text
NO_RETAINED_EVENT_SPECIFIC_OFFICIAL_DOCUMENT = 43
RETAINED_OFFICIAL_DOCUMENT_SEMANTIC_INSUFFICIENT = 3
TAXONOMY_ADJUDICATION_REQUIRED = 4
EXACT_TRANSITION_UNRESOLVED = 50
```

The 43 source-native rows have retained family evidence but no event-specific
official regular-market transition document or accepted attestation. MEJA,
CNMA's stock-dividend representation, and MFIN have retained official
document mechanics but no accepted regular-market transition semantic. Four
KSEI `Mixed Dividend` rows remain `UNKNOWN_TAXONOMY`; no force-map is made.
Candidate, record, distribution, listing, and issued-share dates are not
transition evidence.

Future action groups are recorded but not executed:

```text
TARGETED_EXACT_TRANSITION_ACQUISITION = 43
TARGETED_EVENT_DOCUMENT_ACQUISITION = 3
TAXONOMY_POLICY_REVIEW = 4
```

All 50 are parked pending separate authorization. Rights, operational labels,
stock split, and reverse split remain parked and were not retried.

## Scientific and operational state

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

No provider/network acquisition, source/runtime/science change, outcome/model
access, scoring/refit, counter/PaperState mutation, canonical rewrite,
production execution, merge, or backfill occurred. The smallest justified next
step is review of this single artifact; no next acquisition should be
executed until separately authorized.

