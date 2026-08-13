# 1260-session Open-vs-HLC diagnostic — OPEN-GAP DOMINANT

Date: 2026-08-09 (Asia/Jakarta)
Branch: `data/idx-data-002c`
Source code head: `d4517c61216d8efcae7b61225e03c7670e5cd5b9`

## Scope and controls

This was a bounded diagnostic of the preserved strict 1260 failure. It did
not refetch Stock Summary, Yahoo, or other providers; it did not rewrite raw
price artifacts; and it did not alter the production DATA GATE or the strict
execution-grade Open requirement. Four local read-only cache workers processed
date-partitioned parquet evidence to reduce elapsed diagnostic time.

The exact target remains the trailing 1260 official IDX sessions ending
2026-07-31: `2021-04-29` through `2026-07-31`. The preserved unresolved input
contains 6,716 ticker/session pairs over 989 dates. All 989 corresponding
official fallback payload dates were available.

## Validation

Full pytest: **157 passed, 0 failed**, exit code 0. Three existing non-blocking
pandas `FutureWarning` messages were emitted from the curated-identity and
tradability-anchor reconstruction paths.

## Exact unresolved-pair classification

| class | rows | share | affected known Regular-Market Value | known-value share |
|---|---:|---:|---:|---:|
| `OPEN_ONLY_MISSING` | 6,716 | 100.000% | 66,890,258,565,100 | 100.000% |
| `HLC_MISSING` | 0 | 0.000% | 0 | 0.000% |
| `OPEN_AND_HLC_MISSING` | 0 | 0.000% | 0 | 0.000% |
| `OTHER` | 0 | 0.000% | 0 | 0.000% |

Every unresolved pair had official ACTIVE Regular-Market evidence and valid
High, Low, and Close. The recheck found no full-OHLC row because the missing
field was Open only. No synthetic or forward-filled Open was created.

Exact machine-readable outputs are retained outside Git under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\diagnostic_open_hlc_1260_20260809\`

- `diagnostic_summary.json`
- `diagnostic_class_summary.csv`
- `diagnostic_year_class_summary.csv`
- `unresolved_pair_diagnostics.csv`
- `failed_ticker_diagnostics.csv` (all 62 strict failed-ticker rows)
- `signal_research_unsupported_bias.csv` (header only: no unsupported names)

Year/value distribution:

| year | rows | affected known Regular-Market Value |
|---:|---:|---:|
| 2021 | 2,316 | 37,835,732,109,000 |
| 2022 | 2,541 | 21,987,421,358,300 |
| 2023 | 1,172 | 4,641,507,805,500 |
| 2024 | 544 | 2,302,577,000,300 |
| 2025 | 143 | 123,020,292,000 |

The 62 failed-ticker CSV rows contain exact per-ticker missing counts,
diagnostic classes, affected value, required ACTIVE sessions, UNKNOWN count,
and strict blocker fields. Of these 62 names, 24 were ever top-50, 31 ever
top-100, and 46 ever top-200. None was flagged by this diagnostic as delisted,
IPO-in-window, or corporate-action affected. The strict ticker names remain
the exact list recorded in the preceding 1260 NO-GO checkpoint.

## Hypothetical signal-research HLCV contract

The diagnostic contract was: official ACTIVE state; valid High, Low, Close,
and Volume; Regular-Market Value where available; corporate-action integrity;
Open optional and never synthesized.

- Required common-stock tickers: 979.
- Signal-research eligible tickers: 979/979 (100.000%).
- Required-scope ACTIVE rows: 981,940.
- Signal-research eligible ACTIVE rows: 981,940/981,940 (100.000%).
- Known Regular-Market Value: 15,620,249,523,853,300 total and eligible,
  100.000% coverage.
- Remaining unsupported tickers: none.
- Remaining unsupported top-50/top-100/top-200, delisted, IPO-in-window, or
  corporate-action clusters: none.

The 981,940 denominator is the required common-stock scope and excludes CNTX;
the broader all-anchor summary still contains 982,398 ACTIVE anchors including
out-of-scope evidence rows.

## Decision and blockers

Decision: **OPEN_GAP_DOMINANT**. The evidence supports considering a separate,
explicit signal-research HLCV contract versus execution-grade OHLCV, but this
run did not implement that split or claim certification. Strict 126 remains
PASS. Strict 504 and strict 1260 remain FAIL/NO-GO because execution-grade
Open evidence and existing tradability/semantics blockers remain.

Stop for independent ChatGPT review. Do not weaken the gate, synthesize Open,
materialize a panel or manifest, model, run `IDX-VAL-002`, start 252/1260, or
merge to `main` from this checkpoint.
