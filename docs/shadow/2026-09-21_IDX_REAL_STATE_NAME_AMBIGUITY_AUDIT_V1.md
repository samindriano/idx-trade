# IDX-Trade Real State-Name Ambiguity Audit V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **AMBIGUOUS NAMES RESOLVED / NO REAL PAPER-STATE DISCOVERED**

## Scope

This independent audit used only the two immutable real-input copies:

- `C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-all-sessions\inputs`
  (237 files);
- `C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-extended-evidence\inputs`
  (32 files).

It inspected filenames, JSON key names, CSV headers, Parquet schemas, and
bounded categorical values. It did not inspect provider/outcome surfaces,
write any source, or treat the operational synthetic shadow root as real input.

## Findings that require semantic resolution

| Apparent state signal | Observed evidence | Resolution |
|---|---|---|
| `snapshot_path` / `snapshot_sha256` | present in all 29 session manifests | each path points to that session's `model_input.parquet`; it is a hash-pinned model-input snapshot, not a paper portfolio snapshot |
| `point_state` | present in all 29 `session_evidence.parquet` files; values `ACTIVE=24,114`, `NO_TRADE=3,784`, `SUSPENDED=29` | market/evidence observation state; adjacent schema fields are `evidence_reason`, `stock_summary_row_present`, and `regular_market_value`; no position, order, fill, cash, or obligation fields |
| execution-anchor `state` | present in `execution/idx_execution_anchors.csv`; `ACTIVE=425,340`, `NO_TRADE=54,131` over 479,471 rows | input observation state; same rows carry `ticker`, `market`, `as_of_date`, `source`, `source_ref`, and `evidence_type`, not transaction/fill/paper-state fields |
| `parent_session_manifest_*` | present in two foreign-flow manifest files | lineage for session input artifacts; no state ancestor, prepared parent, fork, or recovery chain |

The direct filename scan found no paper-state filename class in the 237-file
session copy. The extended `execution` filename matches are the documented
execution-anchor input class, not execution state.

## Disposition

The earlier ambiguity-hunt statement “state-like columns: 0” is interpreted
precisely as **zero explicit paper-trading-state columns**. It does not claim
that the word `state` never appears in market-evidence schemas.

No real artifact in these copies supplies a paper portfolio, position lot,
planned quantity, order, fill, cash, pending obligation, prepared execution,
CA entitlement, receivable, settlement, or recovery ancestor.

`REAL_STATE_NAME_AMBIGUITY = RESOLVED AS INPUT EVIDENCE / NO PAPER-STATE`.

This supports the existing classification:

- session/model/evidence files: `NOT_A_PAPER_STATE`;
- execution anchors: `REAL_EXECUTION_ANCHOR_INPUT / NOT_A_FILL_VECTOR`;
- calendar/lineage fields: input provenance only;
- real migration, replay, CA composition, and recovery: still fail-closed.
