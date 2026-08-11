# Yahoo Full-Universe Open Census — Runtime Result

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-yahoo-census-v1`
Runtime HEAD: `c338fe8fafd711eb40dee211897d0ee79842d990`

## Decision

**`YAHOO_FULL_UNIVERSE_OPEN_CENSUS_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW`**

The authorized full-universe Yahoo census completed with the frozen raw-price
and official-factor admission rules. This is a derivative candidate artifact,
not execution-grade promotion. No model, Stage 5, execution-PnL, paper/live
trading, broker integration, or main merge was performed.

## Inputs and immutability

- panel:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`
- panel window: `2021-04-29 -> 2026-07-31`
- panel rows: `981,940`
- panel tickers attempted: `945`
- panel SHA-256 before runtime:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- panel SHA-256 after runtime:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- initial unresolved Open: `446,843`
- `execution_grade_promoted=false`

The authoritative split/reverse-split input was the existing 1260-session
artifact used by the preceding semantics runtime:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\corporate_actions_1260\official_idx_split_reverse_actions_1260.csv`

It contained `55` rows / `52` tickers and SHA-256
`a0ef73a548b3657260b46a0c497e6f87dd9b5138588e23006d4b538677125b35`.

## Fetch and cache

Yahoo raw OHLC was queried through the existing adapter with `auto_adjust=False`.
No additional source was used.

- tickers attempted: `945`
- successful: `940`
- no-data: `0`
- errors: `5`
- network attempts: `955`
- retries: `10`
- cache hits: `0` (fresh census output root)
- provider rows: `1,045,683`
- exact ticker/date coverage: `975,069 / 981,940` (`99.3003%`)
- duplicate provider rows excluded: `0`

Error tickers were retained explicitly: `FREN`, `MASA`, `MFIN`, `RMBA`, and
`TURI`. FREN, MASA, and MFIN each exhausted three attempts with Yahoo
`YFTzMissingError` / no timezone. PURE completed successfully with one
provider row.

## Full known-answer audit

- existing non-null Open rows: `535,097`
- known rows with provider evidence: `534,942`
- known rows compared after provider H/L/C gate: `526,756`
- H/L/C exact: `526,756 / 534,942` (`98.4697%`)
- raw Open exact after H/L/C gate: `526,656 / 526,756` (`99.9810%`)
- existing Open values changed: `0`

## Missing-Open admission

- direct accepted fills: `386,157`
- independently verified split-scale accepted fills: `11,210`
- total accepted fills: `397,367`
- final unresolved Open: `49,476`
- gap closure: `397,367 / 446,843` (`88.9277%`)

Split-scale diagnostics:

- direct H/L/C mismatches evaluated: `62,156`
- non-unit official factor rows: `14,802`
- reconstructed H/L/C exact: `12,941`
- reconstructed known-Open comparisons: `1,731`
- reconstructed known-Open exact: `1,731`
- reconstructed missing-Open accepted: `11,210`

No factor was inferred from Yahoo/panel ratios. No Adj Close, dividend,
previous Close, interpolation, forward fill, averaging, or synthetic Open was
used.

## Rejection and temporal diagnostics

| diagnostic | rows |
|---|---:|
| `HLC_MISMATCH_HIGH` | 42,200 |
| `NO_PROVIDER_ROW` | 6,716 |
| `HLC_MISMATCH_LOW` | 346 |
| `HLC_MISMATCH_CLOSE` | 214 |

| year | missing rows | accepted | provider rows | unresolved |
|---|---:|---:|---:|---:|
| 2021 | 17,931 | 3,238 | 15,615 | 14,693 |
| 2022 | 42,649 | 26,359 | 40,108 | 16,290 |
| 2023 | 173,743 | 162,708 | 172,571 | 11,035 |
| 2024 | 177,829 | 170,999 | 177,285 | 6,830 |
| 2025 | 34,691 | 34,063 | 34,548 | 628 |

| temporal stratum | rows | provider rows | H/L/C exact | accepted |
|---|---:|---:|---:|---:|
| EARLY | 300,515 | 295,427 | 255,366 | 41,725 |
| MID | 333,046 | 331,525 | 312,515 | 295,927 |
| LATE | 348,379 | 348,117 | 345,032 | 59,715 |

## Derivative and artifact integrity

Derivative:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810\execution_open_candidate_panel.parquet`

- rows/tickers: `981,940 / 945`
- every original panel column preserved in the same order: `true`
- existing non-null Open bit-for-bit unchanged: `true`
- unresolved rows remain null: `true`
- derivative SHA-256:
  `d8d3463362a8c43bdb9e8d3aaba5e66ceffe86803b76979d18e3e2e71a276ea4`
- provenance SHA-256:
  `1c11b832c9a8b049202547e8b76c1a4972e9177afefd9a02deb3ca49795bb17d`
- raw-cache manifest SHA-256:
  `08f37a4100e911049a3535357959e43df94c748cdd7bc8cb525a84d870b3b0f6`
- artifact manifest SHA-256:
  `b6e47c98ac256cb07ac0441be41f599ba21481a5340c6b306b5f3301e207da2f`

Runtime root, including raw cache, remains outside Git:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810`

The artifact manifest was independently re-hashed and all listed artifact
hashes matched the files on disk.

## Validation

- full pytest before runtime: `236 passed, 3 warnings`
- code/test changes for this runtime: none
- concrete runtime bug requiring a fix: none

Stop here for independent ChatGPT review. The derivative remains a candidate
artifact only; no automatic execution-grade promotion is implied.
