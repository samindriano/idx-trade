# INC-001 V1.1 — IDX unfiltered capability probe (2026-08-29)

## Status

Read-only, single-request capability probe. No Phase-E, provider retries, outcomes, model work, counter mutation, or canonical rewrite. PR #108/#103 remain unmerged.

## Exact observation

Query: `GetIssuedHistory?caType=&dateFrom=20180101&dateTo=20260814&start=0&length=250`.

- HTTP 200; `recordsTotal=700`; `recordsFiltered=700`; returned rows `250`.
- Stop rule applied: `STOP_PAGE_1_ONLY_RECORDS_TOTAL_GT_250`; no page 2+, retry, or larger request.
- Body SHA256: `8b41163373fcab57904a14a812571c07ae8cbc9642f016f4a381d34a3650b38a`.
- Artifact: `D:\Documents\Project\idx-ca-source-authority-unfiltered-probe-20260829-v1`.

## Reconciliation

The page-1 rows were compared only with the already retained nine-category union (202 rows). 167 page-1 rows are absent from that union; 15 of those are structural/action rows under the bounded local classification. This proves observed category-filter semantic incompleteness, not a complete historical snapshot or new-event census.

For retained-only IDs, 22961 RCCC, 45220 KLAS, 82369 WINS, and 82782 SPMA are present on page 1; 19811 PDPP and 82860 PACK are not on page 1. Because the exact unfiltered result is incomplete, none may be called a full-scope disappearance: `RETAINED_ONLY_TRUE_DISAPPEARANCE_COUNT=0_NOT_DETERMINABLE` and `IDX_HISTORICAL_SNAPSHOT_MONOTONICITY=UNKNOWN_NOT_EQUIVALENT_QUERY_SCOPES`.

`IDX_CATEGORY_FILTER_SEMANTIC_COMPLETENESS=FAIL_OBSERVED`; `IDX_CATEGORY_FILTER_NEGATIVE_AUTHORITY=UNSUPPORTED_BY_OBSERVED_SOURCE_BEHAVIOR`. `NEW_IN_SCOPE_PHYSICAL_EVENTS_FROM_UNFILTERED_QUERY=UNKNOWN_NOT_COMPLETE_PAGE_1_ONLY`.

The accepted physical census remains 412, with 121 resolved and 291 unresolved. Negative no-event and historical as-of authority remain UNKNOWN; bulk acquisition, Phase-E, refit, and counter action remain unauthorized.

