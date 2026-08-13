# Handoff

from: Codex
to: ChatGPT
task_id: IDX-RANKING-V3-STRUCTURE-LITE-SPEC
model_used: Codex
reasoning_level: xhigh
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: d1c1d21f3728610a3bb82d74ee0d4618499b4f6e
branch: research/idx-ranking-v2-spec-v1
head_commit: final pushed documentation head is reported with this handoff
scope: specification/definition audit only for RANKING_V3_STRUCTURE_LITE_SPEC_V1

## Files changed

- `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`
- `docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_SPEC_FROZEN.md`
- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_LEDGER.md`
- `coordination/handoffs/IDX-RANKING-V3-STRUCTURE-LITE-SPEC-RESULT.md`

## Findings

The exact V2 representation remains the frozen 25-feature
`HGB_XS_MARKET` control. Its existing returns, ATR, rolling high/low distance,
range-position, relative-volume, market-context, and market-relative features
already cover generic momentum/range/volatility context. The candidate is
restricted to historical level identity and causal geometry.

The read-only legacy source was:

- repository `samindriano/past-models-indo-stock`;
- branch `frontend/indo-stock-lookup-support-resistance`;
- head `b10f1f619d99590028823addb2cd497333aff20f`.

Safe conceptual salvage: trailing/window extrema, causal pivots, clustered
levels, OHLC touch density with minimum separation, level age, causal role
reversal, close-confirmed breakout/retest, and prior-volume confirmation.

Unsafe and rejected: centered/future-confirmed pivots, snapshot-aligned
boosts, hand-tuned strength/selection/primary scores, `actual_up`, realized
returns, routed tests, range-backtest groups, empirical probabilities,
ticker/setup overlays, horizon weights, and investment verdict logic.

## Decisions frozen

One fixed candidate only; no second Structure-Lite variant. It appends eight
features:

1. `structure_support_distance_atr`
2. `structure_resistance_distance_atr`
3. `structure_support_touch_count_60`
4. `structure_resistance_touch_count_60`
5. `structure_nearest_level_age_sessions`
6. `structure_role_reversal_count_120`
7. `structure_breakout_retest_state`
8. `structure_breakout_volume_confirmed`

Fixed constants: pivot `P=5`, level lookback `L=60`, reversal history `R=120`,
touch separation `S=3`, retest horizon `B=10`, volume baseline `V=20`, cluster
tolerance `0.50 * max(ATR14_p, ATR14_q)`, touch half-width
`max(0.50 * ATR14_j, 0.01 * abs(level))`.

The complete point-in-time definitions, tie rules, event codes, missing
behavior, cache contract, control-equivalence gate, discovery gates, tests,
and provenance requirements are in the frozen spec.

## Decisions not made

No model was fit. No score was calculated. No V2F5/V2F6 or post-2026-07-31
fresh-forward outcome was accessed. No `FORWARD_OUTCOME_ACCESS_STARTED` marker
was written. V3-A Recency was not reopened or rescued. No V3-B code or data
cache was implemented. No candidate was evaluated; the ledger cumulative
counter remains `3`, with preregistered slots `004` and `005` only.

## Artifacts

- frozen spec SHA-256:
  `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- frozen checkpoint:
  `docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_SPEC_FROZEN.md`;
- result handoff: this file.

## Validation run

Read-only governance and archive audit completed. No pytest or research
runtime was run because the authorized scope was specification/definition audit
only. Documentation diff must be reviewed before any future implementation.

## Recommended next action

Independent ChatGPT review of the pushed specification. If approved later,
implement the frozen feature builder and tests in a separately authorized
task, then run exact-control equivalence before inspecting Structure-Lite
F1-F4 outcomes. Do not access F5/F6 or fresh-forward outcomes.
