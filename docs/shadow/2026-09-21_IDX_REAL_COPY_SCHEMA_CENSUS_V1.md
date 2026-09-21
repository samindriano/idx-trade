# IDX-Trade Real Copy Schema Census V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **SCHEMA CENSUS COMPLETE / LINEAGE PARTIAL**

The census was performed on the isolated copy only. It records schema and row
counts, not row values.

## Session input shapes

| Session | Artifact | Rows | Columns |
|---|---|---:|---|
| 2026-09-16 | model_input.parquet | 828 | ticker, date, high, low, close, volume, regular_market_value |
| 2026-09-16 | session_ohlcv.parquet | 828 | ticker, session_date, open, high, low, close, volume, source, source_ref, source_sha256, observed_retrieved_at_utc |
| 2026-09-16 | session_evidence.parquet | 963 | ticker, session_date, point_state, evidence_reason, stock_summary_row_present, regular_market_value |
| 2026-09-16 | idx_stock_summary.csv | 963 | 12 stock-summary fields |
| 2026-09-16 | idx_index_summary.csv | 45 | 18 index-summary fields |
| 2026-09-17 | model_input.parquet | 831 | ticker, date, high, low, close, volume, regular_market_value |
| 2026-09-17 | session_ohlcv.parquet | 831 | ticker, session_date, open, high, low, close, volume, source, source_ref, source_sha256, observed_retrieved_at_utc |
| 2026-09-17 | session_evidence.parquet | 963 | ticker, session_date, point_state, evidence_reason, stock_summary_row_present, regular_market_value |
| 2026-09-17 | idx_stock_summary.csv | 963 | 12 stock-summary fields |
| 2026-09-17 | idx_index_summary.csv | 45 | 18 index-summary fields |
| both | exchange_sessions.csv | 28 | date |

The copied session manifests remain outcome-blind and report
forward_outcomes_accessed=false. No paper-state schema, fill vector, pending
obligation schema, or CA ledger schema was present in this copied class.

The copied schedule attestation is hash-bound to
6c81eb8457cbb5558339e08bd7a159fe700adbe441e287f56a99fb237e081a65. The
copied V4-X1 score manifest is DONE for 2026-09-17 with 296 rows and all
listed outcome/model guards false. Its output artifact_path is an absolute
source path, so the copied score pair is retained for lineage review but is
not loaded as an isolated score pair without an explicit adapter.

## Embedded hash verification

| Check family | Checks | Pass | Fail |
|---|---:|---:|---:|
| session OHLCV, model input, evidence, stock summary, index summary | 10 | 10 | 0 |
| config sidecar against config bytes | 1 | 1 | 0 |
| manifest calendar_sha256 against referenced exchange_sessions.csv | 2 | 0 | 2 |

The embedded calendar hash in both session manifests is
fb853b375c47bcd3afb97a775b0f15a9afbbfef66a000915f89b52c302068762. The
calendar file at the manifest-referenced path currently hashes to
8a5fd51630c331b651fcd41bd024a70c6f8fad6dcc9fe9d5393429e16766a6fe. No local
CSV under the approved forward-monitoring root matched the embedded
fb853b... hash.

The current calendar file was last written after the session manifests were
captured. This is consistent with historical source drift, but it is not a
license to infer the old calendar bytes or substitute another calendar.

## Determination

The copied data is real and structurally readable, but the session lineage is
partial. The calendar mismatch is a real evidence defect:

REAL COPY SCHEMA CENSUS = PASS WITH LIMITATION

CALENDAR LINEAGE = REQUIRES_RECONCILIATION

The affected session inputs must not be used for candidate replay until the
exact historical calendar artifact is separately located and admitted, or the
session is explicitly classified NOT_REPLAYABLE.
