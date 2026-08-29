# INC-001 CA capability reconciliation — V1.1 continuation

Date: 2026-08-29  
Lane: `data/ca-aware-feature-basis-remediation-v1`

This is a bounded local reconciliation of the already retained 2026-08-29
IDX exact-query capture against the retained V1.1 IDX rows. It is not a new
audit phase. No provider call, redundant IDX refetch, KSEI bulk request,
schedule acquisition, Phase-E run, outcome/target access, model work, counter
mutation, canonical historical rewrite, taxonomy expansion, or merge occurred.

## Current controlling inputs

The artifact input checkout was clean and pinned to:

```text
repository: https://github.com/samindriano/idx-trade.git
branch:     data/ca-aware-feature-basis-remediation-v1
HEAD:       0e8d0ed8ae83da9753bbca44f43a49030d3d5d5e
```

The new immutable reconciliation root is controlling for this continuation:

```text
D:\Documents\Project\idx-ca-source-authority-reconciliation-20260829-v1
MANIFEST SHA-256: f8e4aac901cbf5e3a42adff073588aeefff8ef47469e623277605af3d4bedbaa
```

The prior V1.1 event census and capability recovery roots remain immutable
inputs, not competing authorities:

```text
D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8
MANIFEST SHA-256: 556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71

D:\Documents\Project\idx-ca-source-authority-capability-recovery-20260829-v1
MANIFEST SHA-256: dd3331c960bf710c045cc2d77fe649eb8e438e1ace3eb291af4250e672e62819
```

## Reconciliation result — current artifact facts

Stable source identity is the IDX source-native `id`. Payload comparison uses
issuer, source-native action, candidate date, and share-count fields. URL and
response SHA changes are reported separately as provenance-only changes.

```text
IDX_LIVE_QUERY_ROWS       = 202
IDX_RETAINED_ROWS         = 136
IDX_COMMON_IDENTICAL      = 130
IDX_COMMON_CHANGED        = 0
IDX_LIVE_ONLY             = 72
IDX_RETAINED_ONLY         = 6
DUPLICATE_SOURCE_ROWS     = 0
INVALID_UNLINKABLE_ROWS   = 0
COMMON_PROVENANCE_ONLY_CHANGED = 130
```

All 130 common payloads are identical. Their 130 provenance-only differences
are expected: the new evidence is bound to exact category URLs, while the old
rows were retained from `caType=` captures. The six retained-only identities
are `19811`, `22961`, `45220`, `82369`, `82782`, and `82860`; they are
preserved because zero rows from an exact category query are not no-event
authority.

Each of the nine exact queries satisfied
`recordsTotal == recordsFiltered == returned_rows <= 250`. The six non-empty
categories are certified only as
`COMPLETE_POSITIVE_RESULT_SET_AS_RETURNED_FOR_EXACT_QUERY`; the three empty
categories are explicitly `ZERO_ROWS_FOR_EXACT_IDX_QUERY`:

```text
stockSplit                 73  COMPLETE_POSITIVE_RESULT_SET_AS_RETURNED_FOR_EXACT_QUERY
reverseStock                0  ZERO_ROWS_FOR_EXACT_IDX_QUERY
hmetd                     81  COMPLETE_POSITIVE_RESULT_SET_AS_RETURNED_FOR_EXACT_QUERY
dividenSaham                0  ZERO_ROWS_FOR_EXACT_IDX_QUERY
sahamBonus                 15  COMPLETE_POSITIVE_RESULT_SET_AS_RETURNED_FOR_EXACT_QUERY
obligasiWajibKonversi       2  COMPLETE_POSITIVE_RESULT_SET_AS_RETURNED_FOR_EXACT_QUERY
konversiSaham               0  ZERO_ROWS_FOR_EXACT_IDX_QUERY
kurangModal                22  COMPLETE_POSITIVE_RESULT_SET_AS_RETURNED_FOR_EXACT_QUERY
gabungUsaha                 9  COMPLETE_POSITIVE_RESULT_SET_AS_RETURNED_FOR_EXACT_QUERY
```

The exact identity-level reconciliation is in `idx_reconciliation.csv`; all
72 live-only identities and their source refs/SHA are retained there and in
`live_scope_census.csv`.

## Physical census and transition result

```text
PHYSICAL_EVENT_CENSUS_BEFORE = 412
PHYSICAL_EVENT_CENSUS_AFTER  = 412

RESOLVED_TRANSITIONS_BEFORE   = 121
RESOLVED_TRANSITIONS_AFTER    = 121
UNRESOLVED_TRANSITIONS_BEFORE = 291
UNRESOLVED_TRANSITIONS_AFTER  = 291
NEWLY_DISCOVERED_UNRESOLVED_PHYSICAL_EVENT_IDS = []
```

The 72 live-only rows have no intersection with the accepted 716 application
and closure geometry: 14 are outside both, 34 are outside application scope,
and 24 are outside closure geometry. They are forensic/capability evidence
only and do not inflate the physical-event census. The 130 common rows were
already present in the 412-row census. No deterministic cross-source linkage
was inferred between IDX and KSEI rows.

The live rows contain 193 frozen-family mappings and nine taxonomy-unknown
`gabungUsaha` rows. The five in-scope `gabungUsaha` rows remain physical events
already counted in the baseline; the four live-only `gabungUsaha` rows are
outside accepted scope and remain forensic-only. No listing-only rows were
found. Candidate dates remain candidate dates, never inferred transitions.

## Authority and acquisition state

```text
IDX_EXACT_QUERY_POSITIVE_COMPLETENESS = PROVEN_FOR_EXACT_QUERY_RESULT_SET_ONLY
IDX_NEGATIVE_COVERAGE_AUTHORITY        = UNKNOWN
IDX_HISTORICAL_ASOF_AUTHORITY          = UNKNOWN
KSEI_CAPABILITY_VERDICT                = KSEI_CAPABILITY_NOT_PROVABLE_FROM_CURRENT_OFFICIAL_INTERFACE
SCHEDULE_EXPLICIT_TRANSITION_SEMANTICS = UNKNOWN
```

The revised acquisition plan disables redundant pagination/bulk units for the
same nine exact IDX filters. It does not authorize any new acquisition. The
remaining gaps are full 716 source-family/no-event certification, negative
semantics, historical as-of provenance, 291 exact transition identities, KSEI
interval capability, three retained source conflicts, and unresolved taxonomy
policy. No authoritative source has yet been identified for those gaps.

## Scientific and authorization invariants

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
BULK_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED          = FALSE
COUNTER_ACTION              = NONE
```

Candidate date is not transition evidence; exact query zero is not negative
authority; parsed KSEI pages are not certified complete intervals; and
cross-source rows are not deduplicated without deterministic linkage.

## Validation and stop condition

The reconciler verified all nine retained raw response-byte hashes, all exact
query count invariants, the identity/count assertions above, and a deterministic
rerun comparison: 21/21 non-manifest output files were byte-identical. The
existing exact-head CI for input HEAD `0e8d0ed8` remains successful (run
`33236522287`; one non-blocking Node.js 20 action warning). No new CI-triggering
production code was required for this artifact.

This checkpoint is complete and is returned for ChatGPT review. Stop here;
do not execute providers, acquire the 291 schedules, run Phase-E, access
outcomes, fit/refit/score, mutate counters, rewrite canonical history, or merge
PR #108/#103.
