# Open Backfill Tier-1 — Wildan Archive Ready

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-v1`

## Decision

**OPEN_BACKFILL_WILDAN_IMPLEMENTATION_READY_FOR_LOCAL_RUNTIME**

A fail-closed Tier-1 backfill runner is implemented for the already-published `wildangunawan/Dataset-Saham-IDX` archive.

This track does not scrape `idx.co.id`. The public external repository must be cloned normally, pinned to an exact Git commit, and stored outside the project repository.

## Immutable input

Expected signal-research panel:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Required SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Expected baseline facts:

- 981,940 ACTIVE rows;
- 979 tickers;
- 446,843 null Open rows;
- H/L/C/Volume complete;
- original file must remain unchanged.

## Implemented semantics

Module: `src/idx_trade/wildan_open_backfill.py`

For every missing-Open target, the secondary row is admitted only if:

- ticker/date match exactly;
- secondary H/L/C exactly equal the certified panel H/L/C;
- secondary Open is positive and inside the certified `[Low, High]` interval;
- official/certified Volume is valid;
- target Open is null.

Existing Open is never overwritten.

The resulting derivative remains non-promoted:

`execution_grade_promoted=false`.

## Important source-coverage finding

The external repository's `info.json` currently says `last_update=2024-07-19`, but public pinned CSV files contain later observations (including February 2025). The runner therefore records `source_info_last_update` only as metadata and derives `source_observed_last_date` from the actual CSV snapshot.

## Required runtime outputs

- `execution_open_backfill_wildan_v1.parquet`;
- `wildan_source_coverage.csv`;
- `wildan_existing_open_overlap_audit.csv`;
- `wildan_open_backfill_diagnostics.csv`;
- `wildan_open_backfill_summary.json`.

The summary must report:

- exact source commit;
- source observed last date;
- source files/rows coverage;
- known-existing-Open overlap HLC/Open exact rates;
- accepted fills;
- rejected/unresolved rows;
- final null Open count;
- SHA-256 for output artifacts and summary.

## Stop boundary

After Tier-1 runtime, stop for independent ChatGPT review.

Do not yet:

- promote execution-grade OHLCV;
- use the derivative for execution-PnL;
- start paper/live trading;
- automatically add Zapi/Yahoo fills;
- overwrite the original signal panel;
- modify Ranking V2 results or consumed Stage-5 evidence;
- merge to `main`.

The exact residual gap after Tier 1 determines the next source audit.
