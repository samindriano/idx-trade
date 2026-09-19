# Price/Trend State Alpha Challenger V1 — Structural Audit

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-challenger-pit-safe-20260919`
Status: `STRUCTURAL SHADOW ONLY — NOT ADMITTED`

## Scope and safety boundary

This was a read-only, in-memory structural audit. It did not write runtime
sidecars, counters, canonical evaluation artifacts, or incumbent outputs. It
did not inspect protected targets, forward returns, model outcomes, or provider
responses.

The descriptive state builder was read from the accepted external
Price/Trend State V1 implementation in the separate
`idx-price-trend-runtime-bridge-adapter-v1` worktree. Inputs were the clean
historical panel plus available forward `model_input.parquet` snapshots after
the clean-panel cutoff, joined only on ticker and feature session. The audit
covered the 15 clean V4-X1 prospective score sessions from 2026-08-21 through
2026-09-17.

## Frozen structural result

The resulting descriptive state table contained `338,562` rows for `311`
tickers, with feature dates from 2021-04-30 through 2026-09-17. The state
contract was `PRICE_TREND_CONFIRMATION_STATE_V1` and the builder reported
`outcome_blind=True`.

Using the preregistered fixed state map and 90/10 higher-is-better blend:

- mean non-indeterminate coverage: `97.3469968%`;
- mean Spearman versus incumbent `alpha_consensus`: `0.09305004`;
- mean Top-30 churn: `15.333333%`;
- maximum Top-30 churn: `23.333333%`.

These are structural overlap/coverage diagnostics only. They are not IC,
return, OOS, promotion, or superiority evidence. The unseen canonical gate in
the challenger claim remains mandatory and separately authorized.

## Reproducibility notes

The audit used actual available session dates to form the calendar union after
the pinned forward calendar did not cover the earliest available runtime
session. No new session was created and no existing session was modified.

No protected canonical evaluation was run, no H5-only substitution was made,
and no incumbent model was refit, rescored, or replaced.
