# TradingView Historical Price-Path V2 — Preregistered

Date: 2026-08-14
Branch: `data/tradingview-historical-price-path-v2`
Status: `PREREGISTERED_BEFORE_NETWORK`

## Scope

This lane is a bounded historical price-path acquisition and admission test for
official IDX sessions from 2021-04-01 through 2026-07-31. It does not modify
the canonical panel, access protected outcomes, repair Historical OPEN, fit a
model, or start Path Risk/O2 work.

The provider contract is frozen to anonymous `prodata`, `IDX:<ticker>`, raw
60-minute regular-session OHLCV, `adjustment=none`, using the pinned
Mathieu2301 client commit `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c`.
Initial range, pagination limit, timeout, worker count, stop rule, activity
classification, fidelity metrics, and gates are frozen in
`config/tradingview_historical_price_path_v2.json` before the first provider
request.

## Frozen input evidence

External preregistration root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814`

| Input | Result |
|---|---|
| official sessions | 1,279; 2021-04-01 → 2026-07-31 |
| historical common-stock identities | 978 |
| expected ticker-session rows | 1,117,184 |
| official ACTIVE rows | 994,265 |
| official NO_TRADE rows | 122,327 |
| official UNKNOWN rows | 592 |
| provider requests | 978, one deep request per ticker |
| split/reverse-action candidates | 51 |
| immutable canonical panel SHA-256 | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| prereg artifact manifest SHA-256 | `70ca3a4c1088f7f6bde155b4f99fd65eb60cb0963e61a80ea5bd69416fd850f7` |

Input hashes are recorded in the external `preregistration.json`. The
historical identity sidecar adds only the previously evidenced FREN common
share interval (2006-11-29 through 2025-04-16); it does not create a
tradability state.

## Gates and stop rule

ACTIVE sessions require an admissible regular-session path. NO_TRADE sessions
are not provider misses. UNKNOWN activity remains fail-closed. Structural
violations, session leakage, pre-open contamination, malformed OHLCV, and
duplicate ticker/timestamp rows are blocking. HLC and volume fidelity are
diagnostic gates on non-corporate-action canonical overlap. TradingView regular
Open remains diagnostic and cannot overwrite official Open.

If all frozen gates pass, a derivative ACTIVE-only price-path artifact may be
written outside Git. The canonical panel remains unchanged. Otherwise the
runtime reports `TRADINGVIEW_PRICE_PATH_V2_REJECTED` or
`TRADINGVIEW_PRICE_PATH_V2_INCONCLUSIVE` with exact blockers.

## Validation before network

- focused TradingView/V2 tests: passed (26)
- full pytest: passed (66)
- `git diff --check`: passed
- no TradingView network request has been made from this lane before this
  checkpoint.

