# Zapi TradingView Accepted-Candidate Derivative Application Runtime

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-tradingview-targeted-census-v1`
Starting HEAD: `9ffa1b9738f8fc77bd8fb8b29e3aed42ad6cd941`
Decision: `TRADINGVIEW_5675_OPEN_CANDIDATES_APPLIED_TO_YAHOO_DERIVATIVE_STOP_FOR_INDEPENDENT_REVIEW`

## Authorized scope

This runtime applied exactly the 5,675 accepted non-corporate-action
TradingView Open candidates authorized by the independent review. The input
candidate set was reused from the preserved targeted census; no provider call
was made.

The accepted admission gate remained unchanged:

- exact ticker and session date;
- certified High, Low, and Close exact agreement;
- finite positive raw Open;
- Open within the certified Low--High range;
- no corporate-action residual row.

The accepted Yahoo derivative was the only base dataset. Existing non-null
Open values were immutable. TradingView values were written only where the
base Yahoo derivative had a null Open. The certified immutable panel was not
written.

No new provider, corporate-action repair, OHLCV experiment, modelling,
Ranking/PIT-sector work, execution-grade promotion, or execution PnL was
performed.

## Input evidence

| Input | Result |
|---|---:|
| Accepted TradingView candidates | 5,675 |
| Accepted TradingView tickers | 585 |
| Candidate date range | 2021-04-29 through 2025-07-01 |
| Candidate provenance: `ORIGINAL_RUN` | 3,281 |
| Candidate provenance: `PRO_RESUME` | 1,202 |
| Candidate provenance: `TARGETED_CENSUS` | 1,192 |
| Candidate residual class: `NO_PROVIDER_ROW` | 3,664 |
| Candidate residual class: `PROVIDER_HLC_MISMATCH_NO_VERIFIED_SPLIT_FACTOR` | 2,011 |
| TradingView row-audit SHA-256 | `1c05a53155ed52783f112f58babc363e4ee081180542be71a9dfa1bd3ba4c5cd` |
| TradingView combined rows/provenance SHA-256 | `0453776a87995cb32a2a1da9b662bc4eb33e7318f6c53181d33a47130d2da87f` |
| TradingView source manifest SHA-256 | `d0f5899310f9bf37d9f2f726be440fa11a8dcbf7de6703dde068a18009290bf1` |
| Yahoo derivative panel SHA-256 | `d8d3463362a8c43bdb9e8d3aaba5e66ceffe86803b76979d18e3e2e71a276ea4` |
| Yahoo derivative provenance SHA-256 | `1c11b832c9a8b049202547e8b76c1a4972e9177afefd9a02deb3ca49795bb17d` |
| Yahoo source manifest SHA-256 | `b6e47c98ac256cb07ac0441be41f599ba21481a5340c6b306b5f3301e207da2f` |

## Derivative application result

| Metric | Result |
|---|---:|
| Yahoo derivative rows | 981,940 |
| Yahoo derivative null Open before | 49,476 |
| Authorized candidate rows requested | 5,675 |
| Additional null Open values filled | 5,675 |
| Existing non-null Open overwrites | 0 |
| Derivative null Open after | 43,801 |
| New non-null Open count | 938,139 |
| Open coverage before TradingView | 94.9614% |
| Open coverage after TradingView | 95.5393% |
| Candidate row-level TradingView provenance rows | 5,675 |
| Canonical `ZAPI_TRADINGVIEW` rows | 5,675 |
| Non-candidate Yahoo provenance rows changed | 0 |

The exact coverage before application was 932,464 / 981,940 = 94.9614%.
After application it was 938,139 / 981,940 = 95.5393%.

The post-application canonical Open-source counts were:

- `IMMUTABLE_PANEL`: 535,097;
- `YAHOO_YFINANCE`: 397,367;
- `ZAPI_TRADINGVIEW`: 5,675;
- unresolved null Open: 43,801.

Independent verification confirmed that all original Yahoo canonical
provenance fields were unchanged on the 976,265 non-candidate rows. The
TradingView row-level fields preserve candidate census ID, provider class,
residual class, source reference, raw OHLC, validation status, and source
manifest hash.

## Execution-grade diagnostics

| Metric | Result |
|---|---:|
| Immutable panel null Open baseline | 446,843 |
| Yahoo Open fills retained | 397,367 |
| Accepted TradingView Open fills | 5,675 |
| Cumulative Open gap closure | 403,042 |
| Cumulative gap closure rate | 90.1977% |
| Remaining non-corporate-action residual | 33,144 |
| Remaining corporate-action residual | 10,657 |
| Remaining total null Open | 43,801 |
| `execution_grade_promoted` | `false` |
| Execution-grade status | `NOT_PROMOTED_REMAINS_UNRESOLVED` |

The 10,657 corporate-action residuals remain untouched. No claim was made
that the derivative is execution-grade.

## Immutable-panel and artifact verification

Immutable panel:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

- SHA before: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- SHA after: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- unchanged: `true`.

External runtime root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_derivative_v1_20260811`

| Artifact | SHA-256 |
|---|---|
| `accepted_tradingview_open_candidates.csv` | `873efda1e5c7278f22909d988d5f87e395d3f431256582fbb595dc78ccdb06f2` |
| `execution_grade_diagnostics.json` | `9b01dc4beb5536fd2efd06ef6f604f6138a75ceac9eccedc62ae2e6c7738d0e7` |
| `execution_open_candidate_panel_yahoo_tradingview.parquet` | `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab` |
| `execution_open_candidate_provenance_yahoo_tradingview.parquet` | `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687` |
| `source_input_manifest.json` | `cf66000e1e8c81d52b9bcf0f3248aab861aca783d2b8e64e3de776e18b2f8663` |
| `artifact_manifest.json` | `1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14` |

The runtime artifact manifest was independently rehashed and all listed file
hashes matched. The external artifacts remain outside Git.

## Validation and stop condition

- Focused derivative tests: **3 passed**.
- Full pytest: **266 passed**.
- Provider/network calls: **0**.
- `execution_grade_promoted=false`.

Stop for independent ChatGPT review. Do not start another provider, repair
corporate-action rows, write the certified immutable panel, promote execution
grade, model, run Ranking/PIT-sector work, or calculate execution PnL without
a separate authorization.
