# Open Backfill Tier-1 — Wildan Runtime Result

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-v1`
Runtime code HEAD: `906e017ddd276cf0eea5d55666be63ed981f6607`

## Decision

**`OPEN_BACKFILL_WILDAN_RUNTIME_COMPLETE_REVIEW_REQUIRED`**

The authorized Tier-1 runtime completed successfully against the immutable
1260-session signal-research panel. It produced a derivative panel but
accepted **0** secondary Open values under the strict row-level admission
contract. This is a data-quality result only; it does not promote the panel
to execution grade.

No IDX website scraping/crawling, Tier-2 source, Yahoo, TradingView,
Investing.com, modelling, Stage-5 rerun, execution-PnL analysis, paper/live
trading, or main merge was performed.

## Frozen inputs and source

- input panel:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`
- input panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- baseline: 981,940 ACTIVE rows; 979 required common stocks; 945 tickers
  with ACTIVE rows in the panel; 446,843 null Open rows
- source repository:
  `https://github.com/wildangunawan/Dataset-Saham-IDX`
- pinned Wildan commit:
  `bc0ac7712ce5e46f1067349e13ab9f338883c6c4`
- `info.json` last update metadata: `2024-07-19`
- actual raw CSV date range across 958 archive CSV files:
  `2019-07-29` through `2025-02-21`
- actual source date range observed inside the panel window:
  `2021-04-29` through `2025-02-21`

## Runtime and coverage result

- pytest: **217 passed, 3 pre-existing warnings**
- source archive CSV files present: **958**
- panel-ticker files with rows in the evaluated window: **920 / 945**
- panel-ticker files missing: **25 / 945**
- source rows in the evaluated panel window: **750,861**
- known-existing-Open overlap rows: **271,702**
- known-row exact H/L/C matches: **271,702 / 271,702 = 100.0000000000%**
- known-row exact Open matches: **62,277 / 271,702 = 22.9210679347%**
- initial null Open rows: **446,843**
- candidate missing-Open rows with a secondary row: **424,556**
- accepted fills: **0**
- final null Open rows: **446,843**
- original gap closed: **0 / 446,843 = 0.0000000000%**
- `execution_grade_promoted`: **false**

All 446,843 target rows remain unresolved. Diagnostic breakdown:

| diagnostic | rows |
|---|---:|
| `SECONDARY_OHLC_INVALID` | 424,556 |
| `SECONDARY_ROW_UNAVAILABLE` | 22,287 |
| total unresolved | 446,843 |

The zero-fill result is expected under the fail-closed contract: no secondary
row was admitted unless ticker/date matched, secondary H/L/C exactly matched
the certified panel, secondary Open was positive, and secondary Open was
inside the certified Low/High interval. Existing panel Open values were not
overwritten.

## External runtime artifacts

Output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_wildan_v1_20260810`

| artifact | SHA-256 |
|---|---|
| `execution_open_backfill_wildan_v1.parquet` | `19b4885760448ee3f36267d5eb185206e9171b928a658f880b1bf0df541e05e2` |
| `wildan_source_coverage.csv` | `e266dbdd90c926d20c9165dde2a7ce13b5da8060188e2e7a74f74a20eb6ff3d0` |
| `wildan_existing_open_overlap_audit.csv` | `918ac1a008b3ae53dc7333bf4b2c86d21e3069441d85dfd7812764f2886c4979` |
| `wildan_open_backfill_diagnostics.csv` | `50c9c9042e84e749b18fb0ac00a380c1cee1f76e127aafbc9b33fb52f0cba4a4` |
| `wildan_open_backfill_summary.json` | `f6e13fff725b61eedd8e5b2f26c27870db8f374e6fd9d2c9872c2b490817e583` |

The immutable input panel was re-hashed after runtime and remained
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Stop boundary

Stop for independent ChatGPT review. The exact residual gap is unchanged,
and any Tier-2 source audit requires a separate authorization and contract.
