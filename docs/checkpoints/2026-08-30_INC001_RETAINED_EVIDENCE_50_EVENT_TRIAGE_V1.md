# INC-001 retained-evidence 50-event triage — V1

Date: 2026-08-30 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
Scope: exactly the 50 remaining events selected from controlling V14

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

This pass used only the retained V14 economic/source ledgers, retained raw
IDX/KSEI evidence, retained official references, and existing linkage and
transition ledgers. No provider call, network acquisition, URL guessing,
outcome/target access, Phase-E, model work, refit/scoring, counter mutation,
canonical rewrite, or production execution occurred.

## Exact scope and result

```text
CAPITAL_RESTRUCTURING = 19
BONUS_SHARES          = 11
STOCK_DIVIDEND        = 7
MERGER                = 5
TRUE_SECURITY_CONVERSION = 4
UNKNOWN_TAXONOMY      = 4
TOTAL                 = 50
```

All 50 event IDs are unique and exactly match the selected V14 unresolved
rows. The event-level table preserves source representation, retained
mechanics, official reference and evidence hash, family certainty, exact
transition state, linkage state, classification, reason, and bounded next
action:

```text
ARTIFACT_ROOT = D:\Documents\Project\idx-ca-retained-evidence-triage-20260830-v1
EVENT_TABLE = D:\Documents\Project\idx-ca-retained-evidence-triage-20260830-v1\event_triage.csv
MANIFEST SHA-256 = see MANIFEST.json in ARTIFACT_ROOT
```

Normalized triage classifications are:

```text
NO_RETAINED_EVENT_SPECIFIC_OFFICIAL_DOCUMENT = 43
RETAINED_OFFICIAL_DOCUMENT_SEMANTIC_INSUFFICIENT = 3
TAXONOMY_ADJUDICATION_REQUIRED = 4
```

The 43 source-native family rows are family-proven but have no retained
event-specific official regular-market transition document or accepted
transition attestation. The three retained KSEI document rows (MEJA, CNMA
stock-dividend representation, and MFIN) contain event/date mechanics but do
not provide an accepted regular-market transition semantic. The four retained
KSEI `Mixed Dividend` rows remain taxonomy blockers; no family is force-mapped.
Candidate, record, distribution, listing, and issued-share dates are not
promoted to transition dates.

## Family, linkage, and reconciliation state

```text
FAMILY_CERTAINTY_PROVEN = 46
FAMILY_CERTAINTY_UNRESOLVED_TAXONOMY = 4
EXACT_TRANSITION_UNRESOLVED = 50
PROVEN_DUPLICATE_OR_LINKAGE_CHANGE = 0
LINKAGE_REVIEW_REQUIRED = 0
```

No retained evidence proves a permitted family change, exact transition, or
duplicate linkage. V14 therefore remains the controlling reconciliation; no
successor was created:

```text
BEFORE = 412 source / 387 economic / 160 resolved / 181 unresolved / 46 non-basis / 27 linkages
AFTER  = 412 source / 387 economic / 160 resolved / 181 unresolved / 46 non-basis / 27 linkages
RECONCILIATION_CHANGE = FALSE
```

Previously parked families remain parked: RIGHTS (68), operational labels
(47), STOCK_SPLIT (15), and REVERSE_SPLIT (1). This triage does not reopen or
retry them.

## Bounded future plan

The artifact records only these future action groups; none was executed:

```text
TARGETED_EXACT_TRANSITION_ACQUISITION = 43
TARGETED_EVENT_DOCUMENT_ACQUISITION   = 3
TAXONOMY_POLICY_REVIEW                 = 4
```

The immediate recommendation is to park all 50 until separately authorized
event-specific transition evidence or taxonomy policy review is available.
No external acquisition is implied by this checkpoint.

## Validation and admission state

```text
EVENT_TABLE_PARSE = PASS (50 rows, 18 fields)
SELECTED_V14_ID_SET = PASS (50/50; no duplicates or omissions)
RETAINED_SOURCE_HASH_AUDIT = PASS (50/50)
DETERMINISTIC_COMPARISON = PASS (same V14 input set, stable family/classification/action counts)
RECONCILIATION_INVARIANTS = PASS (no reconciliation change)
```

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

The lane changed documentation/provenance only. No IDX-Trade application,
runtime, science, source ledger, or canonical reconciliation file changed.
The existing MAIN-owned coordination row was already `ACTIVE`; its final
triage pointer remains a separate MAIN-owned coordination update after review.
