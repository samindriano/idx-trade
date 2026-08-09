# Open Backfill Policy V1

Date: 2026-08-10 (Asia/Jakarta)

## Purpose

Recover historical IDX daily Open values that are null in the immutable 1260-session signal-research panel without synthesizing prices, weakening the existing H/L/C/V contract, or overwriting any existing Open.

This is a **parallel data-quality track**. It does not rescue Ranking V1, does not change Ranking V2 research semantics, and does not promote the current 1260 panel to execution-grade by itself.

## Immutable starting point

- signal-research window: `2021-04-29 -> 2026-07-31`;
- rows: `981,940` ACTIVE rows;
- required common stocks: `979`;
- H/L/C/Volume coverage: 100%;
- null Open rows: `446,843`;
- input panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

The input panel remains immutable. Backfill always creates a new derivative artifact.

## Source ladder

### Tier 1 — existing Wildan/IDX-derived public archive

Repository: `wildangunawan/Dataset-Saham-IDX`.

Use is limited to the already-published repository snapshot. Do **not** scrape/crawl `idx.co.id` directly. The external repository must be cloned/pinned to an exact Git commit and the commit SHA stored in provenance.

Important discovery: repository `info.json` currently records `last_update=2024-07-19`, but actual pinned CSV files contain rows later than that date (e.g. public files include February 2025 rows). Therefore `info.json` is metadata only; actual source coverage is measured from the CSV rows in the pinned commit.

### Tier 2 — permitted API/source for remaining rows

After the Tier-1 runtime reports the exact residual Open gaps, audit a second source. Current first candidate is Zapi IDX historical data because its public documentation exposes IDX historical stock data and a free-tier API. It must pass a separate licensing/access/semantics pilot before ingestion.

### Tier 3 — personal-research fallback/validator

Yahoo/yfinance may be evaluated only as a fallback/validator under its personal-use/research constraints. Any Yahoo row must still match certified panel H/L/C before its Open can be admitted.

### Excluded automated sources

Do not build an automated dataset pipeline from TradingView or Investing.com where current terms restrict machine processing/scraping. They may be used only for manual spot checks when permitted.

## Row-level acceptance rule

A secondary Open can fill a null panel Open only when all are true:

1. exact ticker/date match;
2. panel row already has valid official/certified H/L/C/Volume evidence;
3. secondary Open, High, Low, Close are positive/non-null;
4. secondary High == panel High exactly;
5. secondary Low == panel Low exactly;
6. secondary Close == panel Close exactly;
7. secondary Open lies inside `[panel Low, panel High]`;
8. the target panel Open is currently null;
9. existing non-null panel Open is never overwritten.

Any mismatch remains unresolved. No averaging, interpolation, previous-close substitution, forward fill, or synthetic Open is allowed.

## Known-answer audit

Before interpreting filled rows, compare the pinned source against panel rows where Open already exists. Report:

- overlap row count;
- exact H/L/C agreement count/rate;
- exact Open agreement count/rate;
- source coverage by ticker/date;
- source files missing from the 979-ticker universe.

This audit is descriptive. Row-level H/L/C equality remains the admission rule even if aggregate overlap looks strong.

## Provenance fields on derivative panel

Every row in the derivative carries/retains:

- `open_source`;
- `open_source_ref`;
- `open_source_commit`;
- `open_validation_status`.

Existing Opens remain `EXISTING_PANEL`. Wildan-accepted fills use `WILDAN_IDX_ARCHIVE` and store the pinned external commit in `open_source_commit`.

## Runtime artifacts

The Tier-1 runner writes outside Git:

- `execution_open_backfill_wildan_v1.parquet`;
- `wildan_source_coverage.csv`;
- `wildan_existing_open_overlap_audit.csv`;
- `wildan_open_backfill_diagnostics.csv`;
- `wildan_open_backfill_summary.json`.

All produced artifacts are SHA-256 hashed. Runtime market data and downloaded source snapshots remain outside Git.

## Promotion boundary

`execution_grade_promoted=false` is mandatory after Tier 1.

A later independent review may consider execution-grade promotion only after:

- exact residual null Open count is known;
- source provenance/licensing is reviewed;
- all accepted rows pass the strict row-level gate;
- corporate-action/ticker identity edge cases are reviewed;
- any remaining gaps are resolved or explicitly accepted under a newly frozen execution-grade contract.

No execution-PnL, paper/live trading, or main merge is authorized by this track.
