# Handoff: INC-001 retained-only IDX forensic V1.1

from: MAIN / Codex
to: ChatGPT review
task_id: `INC001-RETAINED-ONLY-FORENSIC-V11`
branch: `data/ca-aware-feature-basis-remediation-v1`
evidence input: pushed reconciliation HEAD `6d9e26a5b902d52c96487cad8a491596c3af4e2e`

## Result

The six retained-only rows were audited locally. Their old and current query
scopes are not semantically equivalent because the old capture used blank
`caType=` and the current capture uses category-specific filters. Therefore:

```text
RETAINED_ONLY_COUNT = 6
RETAINED_ONLY_QUERY_SCOPE_EQUIVALENT = 0/6 FALSE
RETAINED_ONLY_TRUE_DISAPPEARANCE_COUNT = 0
IDX_HISTORICAL_SNAPSHOT_MONOTONICITY = UNKNOWN_NOT_EQUIVALENT_QUERY_SCOPES
IDX_CURRENT_SNAPSHOT_NEGATIVE_AUTHORITY = UNSUPPORTED_BY_OBSERVED_SOURCE_BEHAVIOR
```

The five `Dividen Saham` rows face current `dividenSaham` zero rows. PACK
`82860` faces current `obligasiWajibKonversi` total 2, containing IDs `82055`
and `16622`, not `82860`. This is not evidence to delete or invalidate any
retained positive row.

## Accepted census and unresolved transitions

```text
LIVE_ONLY_COUNT = 72
LIVE_ONLY_IN_SCOPE_PHYSICAL_EVENT_COUNT = 0
PHYSICAL_EVENT_CENSUS = 412
RESOLVED_TRANSITIONS = 121
UNRESOLVED_TRANSITIONS = 291

UNRESOLVED_BY_FAMILY = BONUS_SHARES:11, CAPITAL_RESTRUCTURING:19,
MANDATORY_CONVERSION:39, MERGER:5, RIGHTS_HMETD:72, STOCK_DIVIDEND:7,
STOCK_SPLIT:41, UNKNOWN_TAXONOMY:4, VOLUNTARY_CONVERSION:93

UNRESOLVED_BY_SOURCE = IDX_GET_ISSUED_HISTORY:136,
KSEI_REGISTERED_SECURITY_HISTORY:155
```

All 291 have candidate-date evidence; zero have exact transition evidence.
The required semantic remains exact event-linked regular-market ex/first-new-
basis transition evidence or a fully source-bound transition lower bound.

## Controlling forensic artifact

```text
D:\Documents\Project\idx-ca-source-authority-retained-only-forensic-20260829-v1
MANIFEST SHA-256: 0e5c49e4f7ca443bc382cce9698c469ed68134dc365d2e6def24371bf8cd3019
```

Files: `retained_only_forensics.csv`, `unresolved_transition_decomposition.csv`,
`remaining_gap_decomposition.csv`, `forensic_summary.json`, and `MANIFEST.json`.

## Frozen evidence-union rule

New snapshots may append evidence but may not erase previously hash-bound
official rows. Conflicting/mutated evidence is surfaced, and positive evidence
is never treated as negative/no-event authority.

No authoritative source is identified for the unresolved portions of discovery,
negative/no-event, historical-as-of, exact transition, conflict, or taxonomy
requirements: `AUTHORITATIVE_SOURCE_NOT_YET_IDENTIFIED`.

```text
BULK_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED           = FALSE
REFIT_AUTHORIZED             = FALSE
COUNTER_ACTION               = NONE
```

Return for ChatGPT review and stop.
