# IDX-Trade Parent-Root Boundary Census V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **METADATA-ONLY BOUNDARY CENSUS / NO NEW PAPER-STATE CLASS ADMITTED**

## Scope

This pass enumerated file paths and sizes under the already approved local
parent root:

`D:\Documents\Project\idx-trade-data-gate-20260808v`

It did not open file contents, hash new source classes, call providers, inspect
outcomes, read cloud/R2, touch the active runtime, or copy any new input.
Path metadata alone is not promoted to runtime evidence.

## Parent-root scale and exclusions

| Boundary | Top-level directories | Files | Disposition |
|---|---:|---:|---|
| Entire parent root | — | 32,656 | metadata census only |
| Provider/backfill-named clusters (`open_backfill*`, `investing*`, `tradingview*`, `stockbit*`) | 62 | 24,007 | excluded; provider/cache/research provenance not runtime state |
| Research/model-named clusters (`ranking*`, `ohlcv*`, `pit_*`, `stage*`, `research_*`, `v4_x*`, and related audit roots) | 77 | 5,321 | excluded; research/model/feature evidence, not runtime state |

Some excluded path metadata contains holdout/outcome-sensitive naming. No such
file was opened or admitted. This is an explicit boundary, not a negative claim
about its contents.

## Focused runtime-like directories

| Directory | Files | Classification |
|---|---:|---|
| `forward_monitoring` | 819 | retained session/model/EOD evidence; 237-file immutable copy is the admitted session input class |
| `corporate_actions` | 6 | real CA event registry/cross-check input; copied and attested |
| `execution` | 5 | execution-anchor input/session reports; copied and attested, not fills |
| `sessions` | 12 | exchange calendar input; copied and attested, not runtime state |
| `forward_open_archive_windows_20260810` | 9 | Official Open metadata/log archive; copied and attested, source-freeze blocked |
| `repair_504` | 15 | listing/price repair inputs and diagnostics; not paper state |
| `repair_504_complete` | 310 | listing/price/stock-summary source caches; not paper state |
| `_idxtrade_v3_runtime_inputs_20260810` | 1 | review markdown only |
| `listings` | 13 | identity/universe input artifacts |
| `tradability` | 3 | tradability input artifacts |
| `certification` | 0 | empty directory |

No new prepared parent, portfolio snapshot, fill vector, pending obligation,
CA ledger, settlement record, or recovery chain was admitted from these
runtime-like names. The already admitted classes remain exactly the 32-file
extended evidence copy plus the 237-file session copy.

## Disposition

`PARENT_ROOT_DISCOVERY = PASS WITH LIMITATION`.

The census strengthens the accessible local boundary and explains why large
provider/research clusters were not silently treated as runtime history. It
does not authorize reading or copying excluded surfaces, and it does not clear
real migration, replay, CA composition, recovery, or pre-canary gates.
