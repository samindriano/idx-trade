# IDX-Trade All-Session Legacy Ambiguity Hunt V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **29-COPY STRUCTURAL HUNT COMPLETE / NO PAPER-STATE DISCOVERED**

## Boundary

This hunt used only the immutable 237-file discovery copy at
`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-all-sessions\inputs`.
It read no provider checkout, protected outcome, counter, cloud/R2, scheduler,
or live runtime state. It did not run a migration, replay, or production flow.

## Checks across all 29 session packages

| Check | Result |
|---|---:|
| Session packages checked | 29 |
| `model_input.parquet` present | 29/29 |
| `session_ohlcv.parquet` present | 29/29 |
| `session_evidence.parquet` present | 29/29 |
| `idx_stock_summary.csv` present | 29/29 |
| `idx_index_summary.csv` present | 27/29 |
| Duplicate required-key cases | 0 |
| Required-field null cases | 0 |
| Invalid date cases | 0 |
| Model-vs-OHLCV ticker-set mismatch cases | 0 |
| Model-vs-OHLCV close-value mismatch cases | 0 |
| State-like columns in checked session families | 0 |

The checked session families expose market/model/evidence fields only. No
column matching position, pending, fill, execution, prepared, portfolio, cash,
order, obligation, entitlement, receivable, dividend, corporate-action, or
reconciliation state was present in these five families.

## Wider-universe scope, not duplicate state

Evidence and stock summaries contain the wider retained listed universe than
model input. The exact extra-row counts are recorded below without persisting
row contents:

| Session | Evidence extras | Stock-summary extras |
|---|---:|---:|
| 2026-08-03 | 132 | 131 |
| 2026-08-10 | 126 | 125 |
| 2026-08-11 | 131 | 131 |
| 2026-08-12 | 127 | 127 |
| 2026-08-13 | 131 | 131 |
| 2026-08-14 | 129 | 129 |
| 2026-08-18 | 128 | 128 |
| 2026-08-19 | 133 | 133 |
| 2026-08-20 | 129 | 129 |
| 2026-08-21 | 131 | 131 |
| 2026-08-24 | 130 | 130 |
| 2026-08-26 | 132 | 132 |
| 2026-08-27 | 136 | 136 |
| 2026-08-28 | 130 | 130 |
| 2026-08-31 | 131 | 131 |
| 2026-09-01 | 132 | 132 |
| 2026-09-02 | 135 | 135 |
| 2026-09-03 | 128 | 128 |
| 2026-09-04 | 132 | 132 |
| 2026-09-07 | 132 | 132 |
| 2026-09-08 | 132 | 132 |
| 2026-09-09 | 131 | 131 |
| 2026-09-10 | 131 | 131 |
| 2026-09-11 | 135 | 135 |
| 2026-09-14 | 135 | 135 |
| 2026-09-15 | 133 | 133 |
| 2026-09-16 | 135 | 135 |
| 2026-09-17 | 132 | 132 |
| 2026-09-18 | 134 | 134 |

This is a universe-scope constraint. It is not evidence of a duplicate fill,
multiple paper-state versions, or a hidden position/obligation. Any future
replay must keep the model-input/score universe explicit.

## Disposition

`ALL_SESSION_LEGACY_SHAPE = PASS WITH LIMITATION`.

The all-session hunt found no locally visible structural ambiguity in the
retained market/model package. It does not close the separate calendar-lineage
blocker, and it cannot substitute for absent paper-state, CA, recovery, or
old-vs-candidate artifacts. The real migration and historical E2E replay gates
remain blocked.
