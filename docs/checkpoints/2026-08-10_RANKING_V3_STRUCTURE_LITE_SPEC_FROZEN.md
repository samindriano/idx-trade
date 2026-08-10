# Ranking V3 Structure-Lite Specification Frozen

Date: 2026-08-10

Status: **SPECIFICATION / DEFINITION AUDIT COMPLETE — RUNTIME NOT AUTHORIZED**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

Audit source head: `d1c1d21f3728610a3bb82d74ee0d4618499b4f6e`

## Decision

The separately authorized V3-B Structure-Lite specification/definition audit
is complete. One fixed eight-feature causal candidate is frozen against the
exact V2 `HGB_XS_MARKET` 25-feature control. No second variant was justified
or added. The result is a preregistration, not a model or research outcome.

Frozen spec:
`docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`

Spec SHA-256:
`1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`

## Audit evidence

The V2 representation was audited from the frozen V2 specification and source
code. It remains 25 features: 10 cross-sectional security features, 9 same-
date market-context features, and 6 market-relative features. Structure-Lite
is limited to incremental historical level identity/geometry and does not add
another generic momentum, rolling range, or volatility library.

The legacy support/resistance source was inspected read-only from:

- repository: `samindriano/past-models-indo-stock`;
- branch: `frontend/indo-stock-lookup-support-resistance`;
- archive head: `b10f1f619d99590028823addb2cd497333aff20f`;
- snapshot path: `snapshots/indo-stock-lookup-support-resistance/`.

Salvaged concepts are trailing/window extrema, causal pivot candidates,
clustered levels, separated OHLC touches, level age, role reversal, causal
breakout/retest, and prior-volume confirmation. Centered pivot confirmation,
snapshot alignment, strength/selection scores, hand-tuned investment scores,
realized outcomes, routed tests, empirical probabilities, ticker/setup
overlays, and backtest-conditioned layers are explicitly prohibited.

## Frozen candidate

The fixed candidate appends these eight columns after the exact V2 25 columns:

1. `structure_support_distance_atr`
2. `structure_resistance_distance_atr`
3. `structure_support_touch_count_60`
4. `structure_resistance_touch_count_60`
5. `structure_nearest_level_age_sessions`
6. `structure_role_reversal_count_120`
7. `structure_breakout_retest_state`
8. `structure_breakout_volume_confirmed`

The constants are fixed at `P=5`, `L=60`, `R=120`, `S=3`, `B=10`, `V=20`,
cluster tolerance `0.50 * max(ATR14_p, ATR14_q)`, and touch half-width
`max(0.50 * ATR14_j, 0.01 * abs(level))`. All levels use sessions through
`t-1`; current-bar data can only calculate current distance and the explicitly
defined close-confirmed event. No future confirmation bar is allowed.

The state encoding is `-2` successful downside retest, `-1` downside
breakdown, `0` no current event, `+1` upside breakout, and `+2` successful
upside retest. A failed/invalidate event returns to `0`; it is not a score.
Volume confirmation uses only the triggering bar and its preceding 20-session
positive regular-market volume baseline.

## Frozen future run contract

- exact V2 control first, with mandatory row/label/order/feature/score/metric
  equivalence;
- Structure-Lite only after control equivalence passes;
- V2F1-V2F4 discovery only;
- V2F5/V2F6 sealed;
- reserved post-2026-07-31 forward outcomes off-limits;
- same V2 ranking metrics, absolute sanity gate, paired promotion gate,
  q25/worst/late diagnostics, and deterministic kill/keep/promote rule;
- new immutable cache only; frozen V2 cache is not overwritten or expanded;
- source/calendar/security/feature-order/provenance hashes required;
- no silent row drops, zero fills, forward fills, invented levels, or outcome
  derived geometry.

The V3-B ledger slots are preregistered as ordinals `004` (control) and `005`
(Structure-Lite). The cumulative evaluated count remains `3`, because no
candidate was run.

## Validation and stop boundary

This task performed documentation and read-only source inspection only. No
pytest, model fit, score, F5/F6 access, fresh-forward access, or data/runtime
materialization occurred. `FORWARD_OUTCOME_ACCESS_STARTED` was not written.
Recency was not reopened or rescued. The next action is independent ChatGPT
review; a separate authorization is required before implementation or an
F1-F4 discovery run.
