# Reliability / Uncertainty V0 — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Branch reviewed: `research/idx-reliability-uncertainty-v0`
Runtime result HEAD: `1d01a1b21f32ba6b97d2cf3684d4f11a499f653b`

## Decision

`RELIABILITY_V0_FEASIBILITY_GO_ACCEPTED`

The frozen V0 verdict is accepted as historical-development feasibility evidence.

## Review findings

- The runtime remained aligned with the frozen one-shot V0 specification and pinned O2/V3-B/Open inputs.
- `score_margin_reliability` qualified on every frozen robustness dimension: positive Spearman, Q4-Q1 lift, fixed-40% selective lift, and conditional lift in all 6/6 folds. Aggregate median fold Spearman was `0.055202`; median Q4-Q1 lift `0.026501`; median selective lift `0.011495`; median conditional lift `0.007326`.
- The positive conditional lift after within-session O2-score-quintile control is important: the signal is not explained solely by stronger O2 alpha scores.
- `joint_marginal_support_reliability` clearly failed and must not be rescued or combined post hoc; its aggregate metrics were negative with 0/6 positive folds.
- Effect sizes for the qualified score-margin proxy are modest. V0 therefore establishes a repeatable reliability signal, not a production-grade calibrated confidence estimate.
- No reliability ML model, composite score, trade filter, sizing rule, or fresh-forward outcome access was authorized or performed.

## Next boundary

Do not rerun or retune V0. A V1 must be specified separately. The preferred next hypothesis is intentionally minimal: preserve score margin as the only surviving reliability signal, freeze a deterministic score/percentile representation prospectively, and validate it on fresh-forward O2 sessions without peeking at protected outcomes. Do not revive the failed marginal-support proxy in V1 unless a genuinely new preregistered hypothesis and independent evidence source justify it.
