# Regular-Market Value Basis Audit V1 — Runtime Result

Date: 2026-08-20 Asia/Jakarta
Status: `REGULAR_MARKET_VALUE_BASIS_NO_MATERIAL_MISMATCH_ON_OFFICIAL_OVERLAP`
Branch: `audit/regular-market-value-basis-v1`
Tested implementation HEAD before this documentation commit: `f51e5d2a53becad131ed73253b537ed69190306d`

## Scope

Outcome-blind audit only. No provider calls, model fit/scoring, target access, protected forward access, parent-panel overwrite, or value remediation.

## Frozen inputs

- panel: `model_safe_signal_research_panel_1260.parquet`
- panel SHA256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- calendar SHA256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- official IDX Stock Summary witness root: `D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1`

## Verification

Focused tests after fixture correction: `3 passed`.

The earlier synthetic test failure was fixture-only: the shocked ticker's value-relative feature changed without crossing the other ticker, so XS percentile rank correctly remained unchanged. The fixture was changed to force an actual rank flip; audit implementation semantics were unchanged.

## Coverage

- frozen panel rows: `981,940`
- frozen panel tickers: `945`
- exact ticker/date official overlap: `981,940`
- comparable positive-value rows: `981,940`
- identity overlap rate on witness dates: `1.0`
- official raw files found/accepted/rejected: `1,288 / 1,288 / 0`
- witness rows: `1,129,024`
- witness tickers: `983`
- witness date range: `2021-04-01` to `2026-08-13`

## Value parity

Frozen `regular_market_value` versus official IDX Stock Summary `Value`:

- exact rows: `981,940 / 981,940`
- exact rate: `1.0`
- within 1% rate: `1.0`
- mismatch rows: `0`
- panel/IDX value-ratio median/p01/p05/p95/p99: all `1.0`
- ratio seams >=20%: `0`
- ratio seams with price-provenance change: `0`

The fact that about `64.787%` of rows have `regular_market_value` within 1% of `close * volume` is not evidence of synthetic value: the official IDX `Value / (Close * Volume)` distribution on the same rows has the same economic shape (median `1.0`, p01 `0.94007`, p99 `1.06590`). The authoritative field itself exactly matches the panel.

## Bounded official counterfactual

Replacing panel value by official IDX value on exact overlap changed nothing because there were zero value mismatches:

- direct value rows/tickers changed: `0 / 0`
- `log_regular_value_relative_20` changed rows: `0`
- XS-rank value feature changed rows: `0`
- market-median value feature changed rows: `0`
- market-relative value feature changed rows: `0`
- primary-liquid eligibility changed rows/tickers: `0 / 0`

## Decision

`REGULAR_MARKET_VALUE_BASIS_NO_MATERIAL_MISMATCH_ON_OFFICIAL_OVERLAP`

Regular-Market Value is exonerated for the full frozen research panel represented by the accepted witness set. No value remediation is authorized or needed from this evidence. The H/L/C price-basis remediation remains a separate issue.

Remaining pre-refit data checks should focus on Volume basis and post-HLC-remediation Open-within-corrected-H/L consistency, not Regular-Market Value.

Runtime manifest:
- path: `D:\Documents\Project\idx-trade-data-gate-20260808v\regular_market_value_basis_audit_v1_20260820\MANIFEST.json`
- SHA256: `e7147f9f378d8c05ed5307e9c0fd92c29a8465221207e2484001a7772c8d8f37`
