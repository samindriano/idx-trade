# Market / Index Forward EOD Capture V1 — implementation checkpoint

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/market-index-forward-eod-v1-monitoring`
Base lineage: `origin/frontend/model-monitoring-v1` at `72446ec`
Status: `IMPLEMENTED_PRE_CAPTURE_STOP_FOR_REVIEW`

## Scope and architecture decision

The accepted Market / Index / Breadth source audit was
`CONDITIONAL_SOURCE_READY_PIT_BLOCKED`. Its approved next step was
prospective, outcome-blind EOD evidence collection. The existing frontend and
Python `forward_monitoring` session package is the canonical capture path.

This branch extends that exact session transaction. It does not create a
second recorder, scheduler, database, API route, session hierarchy, model
input schema, or model-output path.

`model_input.parquet` remains unchanged. Index context is archival/context
data only; no breadth aggregate is invented. Any future breadth derivation
must remain explicitly non-official and derived from Stock Summary.

## Source completeness preflight

Direct official IDX probes on the completed session `2026-08-11` established:

| Endpoint | Request probe | Result |
|---|---|---|
| `TradingSummary/GetIndexSummary` | `length=100,start=0,date=2026-08-11` | `recordsTotal=45`, `recordsFiltered=45`, `45` rows |
| `TradingSummary/GetIndexSummary` | `length=100,start=100,date=2026-08-11` | zero rows / zero totals |
| `TradingSummary/GetIndexSummary` | `length=1000,start=0,date=2026-08-11` | same `45` rows |
| `TradingSummary/GetStockSummary` | `length=100,start=0,date=2026-08-11` | `recordsTotal=963`, `recordsFiltered=963`, `963` rows |
| `TradingSummary/GetStockSummary` | `length=100,start=100,date=2026-08-11` | same `963` rows; pagination parameters are ignored by this response path |
| `TradingSummary/GetStockSummary` | `length=1000,start=0,date=2026-08-11` | same `963` rows |

Therefore the implementation does not treat `length=100,start=0` as a
completeness proof. It requires a positive `recordsTotal`, requires
`len(data) == recordsTotal`, requires `recordsFiltered == recordsTotal` when
present, validates every row's requested session date, and rejects duplicate
security/index identities. Missing metadata, zero rows, date mismatch, or a
partial response fail closed.

The existing runtime provider uses the official date-param endpoint form and
records the exact endpoint, params, row counts, and completeness status in the
session manifest.

## Implemented artifact contract

For each successful canonical session, the same session directory now includes:

```text
model_input.parquet                 # unchanged frozen model-safe schema
session_evidence.parquet            # unchanged tradability evidence
idx_stock_summary.csv               # existing normalized Stock Summary
idx_stock_summary.raw.json          # exact official response bytes
idx_index_summary.csv               # normalized official Index Summary
idx_index_summary.raw.json          # exact official response bytes
manifest.json                       # source params/times/counts/hashes
```

The manifest records per source:

- canonical endpoint and exact params;
- target session date;
- retrieval start and successful response time as
  `observed_available_at_utc`;
- official source identity/ref;
- raw and normalized artifact SHA-256;
- row count, `recordsTotal`, `recordsFiltered`, and completeness status.

The observed timestamp is acquisition time only. It is never promoted to a
historical publication timestamp or `knowledge_at`.

Raw and normalized context artifacts use create-once semantics: an identical
existing artifact is accepted, while different bytes produce a revision
conflict. Verified `DATA_READY` sessions remain idempotent and are not
refetched or overwritten. Stale-capture recovery now verifies all artifacts
declared by the manifest before promoting a session to `DATA_READY`.

## Automation boundary

Read-only Windows Task Scheduler inspection found the existing
`IDX-Trade Stockbit Intraday Daily` task and the separate
`IDXTrade-ForwardOpenArchive` task. Their worktrees, actions, schedules, and
external data roots are separate from this extension. No new scheduled task
was registered or enabled in this checkpoint.

No real new-session capture was executed. The branch stops here for ChatGPT
review before routine forward capture is considered accepted.

## Validation

Focused tests:

```text
tests/test_forward_monitoring.py
tests/test_idx_stock_summary_provider.py
tests/test_forward_market_context.py
16 passed
```

Full repository pytest: `247 passed, 0 failed, 3 warnings` in `17.59s`
(PowerShell wrapper elapsed `20.42s`). No model, outcome, OPEN, Stockbit
intraday, Path Risk, or historical PIT work was started.
