# TradingView IDX Intraday Price-Path Semantic Contract V1

Status: `FROZEN_SEMANTICS_DESIGN_ONLY`

This document freezes field meanings and feature boundaries for a possible
future 2021-01-01 through 2026-07-31 TradingView historical intraday lane. It
does not authorize acquisition, canonical-panel writes, feature generation,
model fitting, Path Risk, O2, or protected-outcome access.

## Source and session contract

The primary provider observation is raw anonymous TradingView data from the
pinned Mathieu adapter commit `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c`,
using `server=prodata`, symbol `IDX:<ticker>`, adjustment `none`, and the
regular session. Session dates must come from the official IDX exchange
calendar. Provider epochs must be converted explicitly to the project
timezone; no nearest-date or nearest-timestamp matching is allowed.

The Stage-1 forensic result is
`TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN`: regular requests did not
return pre-09:00 bars in the bounded 2026 probe, while extended requests did.
The provider exposed no auction flag, trade classification, or auction
boundary. Therefore extended bars are not admitted into the regular path and
cannot be described as auction executions.

Each TradingView 60m result is a **TradingView provider-session bar**, not a
claim of 60 minutes of continuous IDX trading. IDX lunch breaks,
pre-closing, and closing-auction structure require explicit session
segmentation before using clock-time or volume-timing features.

## Frozen semantic fields

| Field | Meaning | Permitted role |
|---|---|---|
| `official_open` | Canonical official IDX daily opening price for the exact session | Canonical anchor for official returns, MAE, MFE, and drawdown |
| `tv_regular_open` | Open of the first chronological raw TradingView regular-session bar | Separate provider observation and provider-anchor sensitivity only |
| `tv_intraday_h/l/c` | Raw chronological regular-session TradingView High/Low/Close path | Path features and deterministic path aggregates |
| `tv_intraday_v` | Raw chronological regular-session TradingView Volume | Volume-path diagnostics/features in provider-native units |

`official_open` and `tv_regular_open` are different fields. The latter must
never overwrite the former. A TV60 first bar is not an official opening-auction
observation merely because it is the first returned bar.

## Permitted feature families

The following families are safe only after exact-session identity, resolved
activity state, regular-session boundaries, and raw-bar validity pass:

- `official_open_to_first_hour_close_return`:
  `first_hour_close / official_open - 1`.
- `tv_regular_open_to_first_hour_close_return`:
  `first_hour_close / tv_regular_open - 1`; this is explicitly a provider
  regular-session return, not an official-auction return.
- `intraday_range`:
  `(max(high) - min(low)) / official_open`.
- `path_volatility`: sum of absolute chronological log close returns.
- `MAE` and `MFE`: separate minimum/maximum path excursions relative to
  `official_open`.
- drawdown from the chronological raw-close path.
- raw H/L/C path vectors and deterministic aggregates.
- raw cumulative volume, bar count, and within-session volume timing, with
  provider-native units preserved.
- regular first-bar movement:
  `first_regular_bar_close / first_regular_bar_open - 1`.

Official-anchor and provider-anchor features must remain separately named and
separately measurable. Corporate-action rows are quarantined using
authoritative split/reverse-split evidence; no ratio-based adjustment is
permitted.

## Session-state handling

- `ACTIVE`: a regular-session path is required; missing provider bars are true
  provider misses.
- `NO_TRADE`: no price-path feature is created; provider absence is not a
  provider miss.
- `SUSPENDED` or another non-active state: exclude from the model-safe path
  view and quarantine provider bars.
- `UNKNOWN`: fail closed; it cannot be counted as covered or relabeled
  `NO_TRADE` without independent official evidence.

## Prohibited semantics

The contract prohibits treating `tv_regular_open` as the official auction,
overwriting `official_open`, arbitrary/synthetic Open repair, nearest-OHLC
correction, previous-close Open, interpolation, forward-fill, adjusted-price
substitution, volume rescaling, inferred split factors, or silent mixing of
extended/pre-market bars into the regular path. Opening-auction microstructure
features require an actual auction source or explicit auction classification.

## Readiness decision

The independent official IDX resolution checkpoint now resolves all 195
previously uncertain keys: every exact Stock Summary row has regular-market
`Volume = 0`, `Value = 0`, and `Frequency = 0`; `UNRESOLVED = 0`. This is a
regular-market activity statement only and does not generalize to all boards or
NonRegular activity.

The readiness distinction is therefore:

- `semantic_contract_ready = true`;
- `historical_price_path_preregistration_ready = true`;
- `admission_v2_ready = false`;
- `modeling_authorized = false`;
- `acquisition_authorized = false`.

The contract is now sufficient to preregister a separate 2021-2026 historical
price-path acquisition/admission V2. V2 itself has not run. The unresolved
auction identity of `tv_regular_open` and the 2021/2024 1m/5m probe timeouts are
non-blocking limitations for a regular-session price-path contract, but remain
blocking for any claim that the first bar is auction microstructure. The
original `TRADINGVIEW_INTRADAY_ADMISSION_REJECTED` verdict remains unchanged.
