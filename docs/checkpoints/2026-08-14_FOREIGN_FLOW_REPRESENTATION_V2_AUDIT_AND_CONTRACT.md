# Foreign Flow Representation V2 — Audit and Outcome-Blind Contract

Date: 2026-08-14 (Asia/Jakarta)  
Branch: `research/idx-foreign-flow-representation-v2`  
Status: `REPRESENTATION_REMEDIATION_IMPLEMENTED_MATERIALIZATION_PENDING`

## Why this is a new representation hypothesis

Foreign Flow V1 was causally valid but tested a narrower representation: rolling foreign net shares divided by the same current/window regular-market volume, plus sign consistency, 3-vs-20 acceleration, and one-day gross activity. Its one-shot historical alpha verdict remains `FOREIGN_FLOW_V1_NO_SURVIVOR` and is not reversed or rescued here.

This lane is outcome-blind representation work only. It does not read V1 alpha predictions, fold results, protected outcomes, fresh-forward outcomes, or any model artifact. The branch is based from the accepted V1 feature-contract lineage rather than the V1 alpha-result branch.

The audit identified a mechanical ambiguity in V1 normalization. `foreign_net / current_volume` is a useful participation-pressure measure, but it can fall when an unusually large foreign inflow occurs on a much larger-than-normal volume day, and it can become large when a small flow occurs in a thin-volume session. Therefore V2 separates current-turnover participation from historical economic flow magnitude.

A second audit issue was found before materialization: a raw-share shock such as `foreign_net_shares / prior_share_volume` can jump mechanically across a stock-split share/price rescaling. V2 therefore uses a close-valued foreign-net notional proxy against a strictly prior regular-market-value baseline for the historical shock axis. This is not claimed to be actual foreign execution value; it is a causal EOD economic-magnitude proxy.

## Frozen design principles

1. **Participation and abnormal magnitude are separate axes.** Current-session share volume remains useful for participation, but it is not used as the denominator for historical flow shock.
2. **Historical baselines exclude the current source session.** No current observation may enter its own liquidity/value baseline or history-percentile reference set.
3. **Flow shock is split-scale stable by construction.** A pure share-count ×k / price ÷k stock-split rescaling does not change the close-valued foreign-net notional proxy; same-day share volume is also excluded from the shock baseline.
4. **Cross-sectional preference follows Clean V2 semantics.** Average percentile ranks are computed within each source session's causal `universe_primary_liquid` population, matching Ranking V2's `rank(method="average", pct=True)` convention.
5. **Accumulation dynamics remain outcome-neutral.** Persistence, streak, and acceleration describe flow state; they do not hard-code foreign buying as bullish.
6. **Flow-price divergence is source-session aligned.** Flow and price-return ranks are both measured through source session `t` and become usable only at feature session `t+1`.
7. **No clipping, winsorization, threshold search, feature selection, model fit, or outcome-dependent tuning is permitted in this lane.**

## Frozen V2 feature family

### Participation

`foreign_participation_1`

`foreign_net_shares[t] / regular_share_volume[t]`

This intentionally preserves the information measured by V1: directional foreign imbalance relative to the trading activity of the same session.

### Historical economic flow shock

`foreign_flow_shock_1`

`(foreign_net_shares[t] * close[t]) / median(regular_market_value[t-20:t-1])`

Requirements:
- `close[t]` must be finite and positive;
- prior 20 official sessions only;
- minimum 10 finite non-negative prior regular-market-value observations;
- prior-value median must be strictly positive;
- source-session regular-market value at `t` is excluded from the denominator.

This representation is designed so a same-day volume/value explosion cannot mechanically dilute abnormal foreign-flow magnitude. Multiplying shares by source-session close is an EOD notional proxy only; it does not assert that foreign investors executed at the close.

`foreign_flow_shock_mean_5` and `foreign_flow_shock_mean_20` are exact-session means of the daily historical flow-shock series. All constituent daily shocks must be finite; no forward-fill or synthetic replacement is allowed.

### Own-history abnormality

`foreign_flow_shock_percentile_120`

The current source-session `foreign_flow_shock_1` is compared with up to the immediately preceding 120 source-session shock observations for the same ticker. The current observation is excluded. At least 60 finite historical observations are required. Ties use an empirical mid-rank CDF:

`(count(history < current) + 0.5 * count(history == current)) / n_history`.

### Cross-sectional foreign preference

- `xs_rank_foreign_flow_shock_1`
- `xs_rank_foreign_flow_shock_mean_5`

Both use the exact Clean V2 average-percentile convention inside the causal primary-liquid universe on source session `t`. Non-primary rows do not receive these ranks.

### Accumulation dynamics

- `foreign_weighted_persistence_5`
- `foreign_weighted_persistence_20`

For an exact shock window:

`sum(shock) / sum(abs(shock))`

Range is `[-1, 1]`; an all-zero valid window is `0`. This preserves direction while allowing large observations to matter more than tiny same-sign observations.

`foreign_signed_streak_10` is the ending same-sign net-flow streak, capped at 10 sessions and scaled to `[-1, 1]`. Zero flow maps to `0`.

`foreign_flow_acceleration_5_20 = foreign_flow_shock_mean_5 - foreign_flow_shock_mean_20`.

### Flow-price divergence

- `foreign_flow_price_divergence_5`
- `foreign_flow_price_divergence_20`

The source-session primary-liquid cross-sectional rank of flow-shock accumulation is compared with the matching source-session cross-sectional rank of `close_return_5` or `close_return_20`:

`flow_rank - price_return_rank`.

Positive values describe relatively strong foreign accumulation with relatively weaker price performance; negative values describe relatively stronger price performance than flow preference. No directional payoff is assumed by the feature definition.

## Causality contract

Every output row must satisfy:

`flow_through_session = t`

`feature_session = immediately next official session after t`

All flow, volume/value history, own-history distributions, primary-liquid membership, and price-return context used in the row must be known through `t` only. No same/future `feature_session` data may enter the feature.

Market context is explicitly rejected if label/outcome columns are present.

## Free-float / HSC normalization — high-priority blocker, not omitted

Foreign-flow pressure relative to economically tradable supply is considered a high-priority future representation. A small net foreign purchase can be economically material when the effective tradable float is very thin, particularly under concentrated ownership / HSC-like conditions.

However, this repository does **not** currently have a defensible point-in-time historical free-float or effective-float series. The existing direct-IDX `GetIssuedHistory` work is only a candidate event/share-count ledger and is not sufficient to construct PIT-safe historical free float. Using current free float to backfill history is prohibited.

The future target concept is therefore recorded but blocked:

`foreign_net_shares / PIT_effective_free_float_shares`

Important semantic guardrail: reported/statutory free float must not automatically be treated as economically effective tradable float. Concentrated ownership can make effective supply materially thinner, but the system must not infer issuer-level manipulation or an undocumented effective-float number. A future lane needs independently sourced, versioned, PIT-safe share-count/free-float evidence and a separate HSC/effective-float methodology.

## Files implemented

- `src/idx_trade/foreign_flow_features_v2.py`
- `tests/test_foreign_flow_features_v2.py`

Local isolated synthetic validation performed during implementation:

- `8 passed`
- verifies current-volume dilution separation;
- verifies invariance to a pure stock-split share/price rescaling;
- own-history percentile excludes current observation;
- Clean-V2-style cross-sectional ranking;
- non-primary exclusion from cross-sectional ranks;
- magnitude-weighted persistence and signed streak;
- source-session flow-price divergence;
- outcome-bearing context rejection.

Repository-wide pytest and real historical materialization are not claimed here because the authoritative Foreign Flow archive and canonical market context are external Windows artifacts. The next step is an offline materialization/census only, with no provider calls, model fitting, or outcome access.
