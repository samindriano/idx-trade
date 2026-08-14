# TradingView Historical Price-Path V2 — Runtime

Date: 2026-08-14
Branch: `data/tradingview-historical-price-path-v2`
Runtime artifact root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814`

## Decision

`TRADINGVIEW_PRICE_PATH_V2_REJECTED`

The frozen request returned valid regular-session data for most symbols, but
the frozen maximum of 10 `fetchMore` steps produced only about 550 hourly bars
per ticker. That is not enough to cover the five-year 2021-04-01 through
2026-07-31 window. Active-session coverage therefore failed by a wide margin.
No model-safe derivative was materialized and the canonical panel was not
modified.

## Runtime counts

| Metric | Result |
|---|---:|
| logical ticker requests | 978 |
| corrected provider attempts | 978 |
| first invalid-parameter attempts preserved | 44 |
| total network attempts including bounded repair | 1,022 |
| `AVAILABLE` | 962 |
| `SYMBOL_ERROR` | 16 |
| `TRANSPORT_TIMEOUT` / transport errors | 0 |
| max-period response | 550 bars for 954 tickers |
| official sessions | 1,279 |
| historical common-stock identities | 978 |
| expected ticker-session rows | 1,117,184 |
| ACTIVE sessions | 994,265 |
| NO_TRADE sessions | 122,327 |
| UNKNOWN sessions | 592 (0.05299%) |

The first 44 calls exposed a local pandas-to-Node type coercion defect: the
CSV loader passed `timeframe=60` as a number rather than the frozen string
`"60"`, and the pinned client returned `create_series invalid parameters`.
Those raw responses remain under `raw/mathieu/`; a bounded repair wrote the
corrected responses under `raw/mathieu/repair_timeframe_contract/` without
overwriting them. The corrected request contract remained `prodata`,
`IDX:<ticker>`, `timeframe="60"`, `session=regular`, `adjustment=none`.

Final symbol-error tickers, all reported by the provider as `invalid symbol`,
were: CNTB, FORZ, FREN, HDTX, JKSW, KPAL, KPAS, KRAH, MAMI, MASA, MFIN,
MYRX, NIPS, PRAS, RMBA, and TURI. No alternate symbols or sources were tried.

## DATA GATE

| Gate | Result |
|---|---:|
| active coverage overall | 87,372 / 994,265 = 8.7876% — FAIL (98% required) |
| active coverage 2021 | 686 / 123,958 = 0.5534% — FAIL |
| active coverage 2022 | 1,456 / 174,888 = 0.8325% — FAIL |
| active coverage 2023 | 1,986 / 185,137 = 1.0727% — FAIL |
| active coverage 2024 | 3,012 / 196,046 = 1.5364% — FAIL |
| active coverage 2025 | 3,436 / 199,165 = 1.7252% — FAIL |
| active coverage 2026 | 76,796 / 115,071 = 66.7379% — FAIL (95% yearly required) |
| UNKNOWN activity | 592 / 1,117,184 = 0.05299% — PASS |
| malformed OHLCV | 0 — PASS |
| duplicate ticker/timestamp | 0 — PASS |
| session-date leakage | 0 — PASS |
| extended/pre-open contamination | 0 — PASS |

There were 906,893 true provider misses under the frozen active-session
definition. The dominant blocker is not malformed data; it is insufficient
historical depth under the frozen pagination boundary.

## Fidelity on available canonical overlap

These are diagnostic comparisons only and are not a full-window admission
claim because canonical daily artifacts are sparse for some historical names.
Official split/reverse candidates were quarantined within the frozen one-session
radius.

| Metric | Result |
|---|---:|
| matched daily rows | 85,490 |
| non-corporate-action rows | 85,479 |
| corporate-action quarantined rows | 11 |
| HLC exact overall | 94.3705% — FAIL (95% required) |
| volume within ±5% overall | 93.4885% — PASS |
| 2021 HLC / volume | 99.2537% / 98.5075% |
| 2022 HLC / volume | 75.4647% / 74.1636% — FAIL |
| 2023 HLC / volume | 95.8704% / 93.3926% |
| 2024 HLC / volume | 99.4024% / 98.4396% |
| 2025 HLC / volume | 97.0605% / 93.5099% |
| 2026 HLC / volume | 94.1460% / 93.4219% — yearly HLC/volume fail |

## Integrity and boundaries

- canonical panel SHA before: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- canonical panel SHA after: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- runtime artifact manifest SHA-256: `a0bff854f6c76266c8b8487aa0d07af38ac263def3d7f719bea9af7715cb5e1e`
- preregistration manifest SHA-256: `70ca3a4c1088f7f6bde155b4f99fd65eb60cb0963e61a80ea5bd69416fd850f7`
- provider: no alternate source, no authentication, no symbol substitution
- panel write: no
- model / Path Risk / O2 / protected outcomes: not run or accessed
- Historical OPEN repair: not performed

The V2 admission verdict is frozen as rejected for this request contract. A
future remediation would require a new preregistration that changes the
pagination-depth contract and must not reinterpret this failed gate as a
partial admission.

## Validation

- focused V2 and TradingView tests: passed (26)
- full pytest after implementation fix: passed (66)
- `git diff --check`: passed
