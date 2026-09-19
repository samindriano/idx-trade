# Alpha Challenger — Financial Reporting Event V1

Status: `PREREGISTERED / OUTCOME-BLIND MATERIALIZATION`

This challenger is separate from both the frozen V4-X1 incumbent and the
previous Financial PIT V1 level-additive experiment. It does not modify or
rescore the incumbent model, prospective evaluator, runtime, counters, or
forward data.

## Frozen source and PIT contract

Input:

- `D:\Documents\Project\idx-financial-representation-v2-20260816-v1-run3\bundle_rows.parquet`
- rows: `277,244`
- bundle SHA-256: `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b`
- representation schema: `idx-trade/financial-representation-v2-structural-audit-v1`
- `labels_loaded=false`, `model_fit=false`, `outcome_blind=true`,
  `protected_outcomes_accessed=false`

Only rows with `bundle_status=SELECTED` and `core3_available=true` are eligible.
The builder fails closed on duplicate ticker/date keys, same-bundle violation,
knowledge-time violation, incomplete selected provenance, missing reporting
state identity, or non-finite CORE3 values. No fallback across periods and no
forward fill is allowed.

## Frozen event representation

For each ticker, selected reporting states are ordered by decision date. A new
state is an event only when its reporting version differs from the immediately
previous distinct selected state. The first observed state has no event delta.

For a valid transition, define:

- `delta_leverage = current leverage - previous leverage`;
- `delta_liquidity = current cash/assets - previous cash/assets`;
- `delta_margin = current net-margin - previous net-margin`;
- `quality_delta = -delta_leverage + delta_liquidity + delta_margin`.

The sign convention is fixed before target access: lower leverage and higher
liquidity/margin are positive. The event overlay is the within-date average-tie
percentile rank of the three directional changes among event rows, with
non-event/unavailable rows assigned neutral `0.5`. No feature selection,
direction flip, winsorisation, or parameter search is allowed.

The historical comparison overlay, if reached, is fixed at:

`0.90 * rank(accepted V4-X1 alpha_consensus) + 0.10 * financial_event_overlay`

The low weight is frozen because reporting events are sparse and the priority
is economic robustness, not a high-turnover replacement signal.

## Historical diagnostic gate

Only after outcome-blind materialization passes may the accepted historical
target ledger through `2026-07-17` be read. No fresh/protected/O2 outcomes are
allowed. On exact common support, report daily cross-sectional Spearman IC,
paired mean/q25 deltas, non-overlapping 20-session block stability, event
coverage, and turnover proxy (fraction of rows whose overlay differs from
neutral).

The fixed blend is a historical `PASS` only if:

1. mean IC delta is at least `+0.005`;
2. q25 IC delta is non-negative;
3. at least `80%` of non-overlapping 20-session blocks have non-negative delta;
4. common-support coverage is at least `95%` and event rows are not concentrated
   in fewer than 100 tickers.

Failure closes this exact event specification. No alternate weighting, ratio
subset, period window, horizon, model, or rescue search follows.

Even a pass is historical evidence only and cannot enter V4-X1 without the
separate prospective/PIT admission gates.
