# INC-001 V1.1 — complete unfiltered IDX pagination

Date: 2026-08-29  
Lane: `data/ca-aware-feature-basis-remediation-v1`

## Scope and authorization

This is the authorized completion of the already captured exact unfiltered
query. Page 1 was not refetched. Exactly two additional provider requests
were made: `start=250&length=250` and `start=500&length=250`, with the same
endpoint, empty `caType`, date range, and length. No category query, KSEI,
schedule, Phase-E, outcome, model, counter, or canonical-data operation was
performed.

## Paginated result

```text
IDX_PAGE2_HTTP  = 200
IDX_PAGE2_ROWS  = 250
IDX_PAGE2_TOTAL = 700

IDX_PAGE3_HTTP  = 200
IDX_PAGE3_ROWS  = 200
IDX_PAGE3_TOTAL = 700

IDX_UNFILTERED_PAGINATION_STABILITY = PASS_ALL_PAGES_TOTAL_FILTER_700
IDX_UNFILTERED_TOTAL_RAW_ROWS       = 700
IDX_UNFILTERED_UNIQUE_SOURCE_IDS    = 700
IDX_UNFILTERED_DUPLICATE_SOURCE_IDS = 0
IDX_UNFILTERED_INVALID_IDS          = 0
IDX_UNFILTERED_CROSS_PAGE_CONFLICTS = 0
IDX_UNFILTERED_POSITIVE_RESULT_SET  = COMPLETE_AS_RETURNED_ACROSS_CONSISTENT_PAGINATION
```

Page evidence hashes are preserved in the immutable artifact's three page
ledgers. The result is not called an atomic historical snapshot: page
retrieval timestamps differ and source-defined historical as-of semantics are
still unproven.

## Six retained-only identities

Five are present and payload-identical in the complete current broad result:
`19811 PDPP`, `22961 RCCC`, `45220 KLAS`, `82369 WINS`, and `82782 SPMA`.
`82860 PACK` is absent from the complete current 700-row result. All six are
comparable on the exact broad query parameters; therefore the observed
retained-only disappearance count is one, and the snapshot monotonicity
finding is revised narrowly to:

```text
RETAINED_SIX_PRESENT_COUNT = 5
RETAINED_SIX_CHANGED_COUNT = 0
RETAINED_SIX_ABSENT_COUNT = 1
RETAINED_ONLY_TRUE_DISAPPEARANCE_COUNT = 1
IDX_HISTORICAL_SNAPSHOT_MONOTONICITY = FAIL_OBSERVED_TRUE_DISAPPEARANCE
```

This is an observed source-result disappearance between comparable captures,
not historical as-of authority and not an inference from page placement.

## Category-filter loss

All 700 broad rows were compared locally with the already captured nine-filter
union; no category refetch occurred. The union contains 202 IDs. `498` broad
rows are absent from that union, comprising `290` structural/action candidates
and `208` IPO listing-only rows. The structural missing breakdown is retained
row-by-row with source ID, exact native label, ticker, candidate date, family
classification, and scope/census decision.

```text
IDX_CATEGORY_FILTER_SEMANTIC_COMPLETENESS = FAIL_OBSERVED
UNFILTERED_ROWS_MISSING_FROM_CATEGORY_UNION = 498
UNFILTERED_STRUCTURAL_ROWS_MISSING_FROM_CATEGORY_UNION = 290
```

Structural missing labels are: `Waran` 155, `Tanpa HMETD` 58, `Dividen Saham`
7, `Delisting` 34, `Partial Delisting` 31, `Pencatatan Kembali Sebagian` 2,
and `ESOP/MSOP` 3. The unknown/unrepresented labels are preserved as
taxonomy-only or outside-scope findings; no new frozen family is selected.

## Physical census

Recognized in-scope frozen-family/MERGER rows from the broad result were
already represented in the accepted IDX census. The 192 in-scope rows whose
source-native actions are not represented by the frozen nine-filter taxonomy
remain `TAXONOMY_ONLY_NOT_CENSUS`; no source policy permits force-mapping them.
Therefore the physical census is unchanged:

```text
NEW_IN_SCOPE_PHYSICAL_EVENTS_FROM_UNFILTERED_QUERY = 0
NEW_IN_SCOPE_PHYSICAL_EVENT_IDS = []

PHYSICAL_EVENT_CENSUS_BEFORE = 412
PHYSICAL_EVENT_CENSUS_AFTER  = 412
RESOLVED_TRANSITIONS_BEFORE = 121
RESOLVED_TRANSITIONS_AFTER  = 121
UNRESOLVED_TRANSITIONS_BEFORE = 291
UNRESOLVED_TRANSITIONS_AFTER  = 291
```

The unresolved distribution remains 291 events / 193 unique tickers:

```text
BONUS_SHARES 11; CAPITAL_RESTRUCTURING 19; MANDATORY_CONVERSION 39;
MERGER 5; RIGHTS_HMETD 72; STOCK_DIVIDEND 7; STOCK_SPLIT 41;
UNKNOWN_TAXONOMY 4; VOLUNTARY_CONVERSION 93

IDX_GET_ISSUED_HISTORY 136; KSEI_REGISTERED_SECURITY_HISTORY 155
```

## Authority and stop state

```text
IDX_NEGATIVE_NO_EVENT_AUTHORITY = UNKNOWN
IDX_HISTORICAL_ASOF_AUTHORITY = UNKNOWN
BULK_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

Controlling artifact: `D:\Documents\Project\idx-ca-source-authority-unfiltered-probe-20260829-v1`.
Its manifest covers the original page-1 capture, both newly authorized pages,
all raw rows, six-row comparison, full category-loss ledger, structural
breakdown, and census/gap summaries. This checkpoint is complete and stops
for ChatGPT review. PR #108/#103 remain unmerged.

