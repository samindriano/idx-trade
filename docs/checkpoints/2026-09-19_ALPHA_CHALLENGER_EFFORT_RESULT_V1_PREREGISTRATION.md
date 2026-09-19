# Alpha Challenger — Effort vs Result V1

Status: `PREREGISTERED / OUTCOME-BLIND FEATURE STAGE`

This is an isolated challenger lane. It does not alter, rescore, refit, or
replace the frozen V4-X1 incumbent. It does not touch the prospective evaluator,
forward counters, production runtime, or forward data.

## Information set

The only initial input is the accepted clean OHLCV panel:

- path: `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_final_20260820_v2\model_safe_signal_research_panel_1260_final_clean.parquet`
- rows: `981,940`
- panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- official-session calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- the panel schema contains OHLCV, liquidity, provenance, and integrity fields;
  it contains no target, label, or outcome column.

The panel is read-only. Every candidate value must use session `t` EOD data and
strictly prior observations for rolling baselines. Rows with invalid OHLC,
duplicate ticker/session keys, failed corporate-action integrity, or forbidden
target-like columns fail closed.

## Frozen candidate family

For each ticker and session `t`, using only data available at the completed
session cutoff:

1. `effort_signed_body`: `log(volume_t / median(volume_{t-20:t-1}))` multiplied
   by `(close_t - open_t) / (high_t - low_t)`.
2. `effort_close_location`: the same log-relative-volume term multiplied by
   `(2*close_t - high_t - low_t) / (high_t - low_t)`.
3. `range_per_effort`: `log(high_t / low_t)` minus the log-relative-volume term.
4. `failed_breakout_signed`: `+1` for a prior-20-session low break that closes
   back above the prior low, `-1` for a high break that closes back below the
   prior high, otherwise zero.
5. `confirmed_breakout_signed`: `+1` when the close finishes above the prior
   20-session high, `-1` when it finishes below the prior 20-session low,
   otherwise zero.
6. `effort_absorption`: log-relative volume multiplied by
   `1 - abs(body_signed_range)`.

The prior-window baseline requires at least 10 valid observations. No clipping,
winsorisation, future fill, centered rolling window, target-conditioned choice,
or feature subset search is allowed in this stage. The implementation returns
raw causal features; any cross-sectional rank must be computed later only after
joining the authoritative decision-universe mask for the same session.

## Research sequence and stop rules

Stage A is outcome-blind: schema/PIT/integrity, coverage, missingness, and
orthogonality diagnostics only. A failure of any causal invariant is a hard
`NO-GO` for the family.

Stage B may be started only as a separately frozen historical-development run.
It must use one fixed family, one fixed chronological split, and the accepted
V4-X1 target/continuity contract. No protected prospective outcomes are allowed.
There is no tuning or rescue branch after observing results. A candidate that
does not show stable incremental evidence versus the frozen incumbent remains a
research-only `NO-GO`.

No conclusion about predictive value is made by this preregistration alone.
