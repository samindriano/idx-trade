# Handoff: INC-001 CA capability reconciliation V1.1

from: MAIN / Codex  
to: ChatGPT review  
task_id: `INC001-CA-CAPABILITY-RECONCILIATION-V11`  
branch: `data/ca-aware-feature-basis-remediation-v1`  
evidence input HEAD: `0e8d0ed8ae83da9753bbca44f43a49030d3d5d5e`

## Decision

`NO-GO for acquisition or scientific execution`: local reconciliation of the
already retained complete positive IDX result sets is complete. It closes only
the bounded exact-query positive-result-set capability; it does not establish
negative/no-event authority, historical as-of authority, KSEI completeness, or
transition semantics.

## Controlling artifact

```text
D:\Documents\Project\idx-ca-source-authority-reconciliation-20260829-v1
MANIFEST SHA-256: f8e4aac901cbf5e3a42adff073588aeefff8ef47469e623277605af3d4bedbaa
```

Important files are `idx_reconciliation.csv`, `live_scope_census.csv`,
`physical_event_census_after.csv`, `transition_reconciliation.csv`,
`source_authority_matrix_reconciled.csv`,
`revised_acquisition_requirements_v11.json`, and
`reconciliation_summary.json`.

## Required review values

```text
IDX_LIVE_QUERY_ROWS = 202
IDX_RETAINED_ROWS = 136
IDX_COMMON_IDENTICAL = 130
IDX_COMMON_CHANGED = 0
IDX_LIVE_ONLY = 72
IDX_RETAINED_ONLY = 6

PHYSICAL_EVENT_CENSUS_BEFORE = 412
PHYSICAL_EVENT_CENSUS_AFTER = 412

RESOLVED_TRANSITIONS_BEFORE = 121
RESOLVED_TRANSITIONS_AFTER = 121
UNRESOLVED_TRANSITIONS_BEFORE = 291
UNRESOLVED_TRANSITIONS_AFTER = 291

IDX_EXACT_QUERY_POSITIVE_COMPLETENESS = PROVEN_FOR_EXACT_QUERY_RESULT_SET_ONLY
IDX_NEGATIVE_COVERAGE_AUTHORITY = UNKNOWN
IDX_HISTORICAL_ASOF_AUTHORITY = UNKNOWN
KSEI_CAPABILITY_VERDICT = KSEI_CAPABILITY_NOT_PROVABLE_FROM_CURRENT_OFFICIAL_INTERFACE
SCHEDULE_EXPLICIT_TRANSITION_SEMANTICS = UNKNOWN

BULK_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

There are 130 payload-identical common rows and 130 provenance-only URL/SHA
differences. The six retained-only rows are preserved. The 72 live-only rows
are all outside the accepted 716 application and/or closure geometry, so no
new physical event or unresolved physical transition identity is added.

The 9 exact query statuses are recorded individually. Six are
`COMPLETE_POSITIVE_RESULT_SET_AS_RETURNED_FOR_EXACT_QUERY`; `reverseStock`,
`dividenSaham`, and `konversiSaham` are
`ZERO_ROWS_FOR_EXACT_IDX_QUERY`, never “no events existed.”

## Remaining authority gaps / next source requirements

1. Keep redundant IDX pagination disabled for these exact nine filters.
2. Identify a source-contract-bound negative/no-event and historical-as-of path
   for the full 716 application/closure scope; no such source is proven.
3. Obtain, only after approval, accepted transition evidence for the 291
   unresolved physical event identities; candidate dates do not qualify.
4. Keep KSEI bulk disabled while
   `KSEI_CAPABILITY_NOT_PROVABLE_FROM_CURRENT_OFFICIAL_INTERFACE` stands.
5. Resolve the three retained source conflicts and taxonomy policy separately.

The source-native `gabungUsaha` semantics remain separate from frozen families.
Five in-scope rows remain physical events; four outside-scope live-only rows
remain forensic-only. No new family is selected and no force-map is made.

## Boundaries and stop

No network/provider call, redundant refetch, KSEI bulk, schedule acquisition,
Phase-E, outcome access, target access, model fit/refit/scoring, counter
mutation, canonical rewrite, or PR #108/#103 merge occurred. Scientific state
is unchanged: `DATA_ADMISSION=FAIL`, `RESEARCH_ADMISSION=FAIL`,
`MODEL_PROMOTION=NOT_EVALUATED`, and `HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN`.

Return this handoff for ChatGPT review and stop.
