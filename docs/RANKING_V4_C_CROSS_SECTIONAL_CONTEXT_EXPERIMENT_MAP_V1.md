# Ranking V4-C — Cross-Sectional Opportunity Context Experiment Map V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **DESIGN FROZEN PRE-OUTCOME — ONE CHALLENGER ONLY**

## Research question

`V4-C-CROSS-SECTIONAL-CONTEXT-V1` asks:

> Conditional on exact frozen V3-B stock state, market medians/breadth and Structure-Lite geometry, does the **dispersion of the current cross-sectional opportunity set** add robust ranking information?

This family is deliberately narrower than V4-A/V4-B. The candidate budget is one compact challenger, not multiple return-dispersion / volatility-dispersion / breadth-dispersion variants.

## Why only one challenger

The natural sub-ideas all describe the same date-level latent state:

- return dispersion;
- volatility dispersion;
- range-position dispersion;
- winner/loser separation;
- participation dispersion.

Running each as a separate model and selecting the best would create a post-hoc context-feature tournament. Instead, V4-C freezes one small bundle using robust dispersion measures that are not already present in V3-B.

Participation/value dispersion is intentionally excluded from first pass because V4-A already tested a participation-quality family and closed without a survivor. V4-C must not become a backdoor rescue of V4-A.

## Frozen first-pass architecture

- ordinal `018`: exact final V3-B control;
- ordinal `019`: exact V3-B + one four-feature cross-sectional dispersion bundle.

There is no second V4-C challenger and therefore no within-family integration candidate.

## Frozen information bundle

All features are computed **per signal date from the full causal primary-liquid universe**, before any V4-C model scoring and without using outcome/label availability.

1. 5-session return interquartile range;
2. 20-session return interquartile range;
3. ATR/close interquartile range;
4. 20-session close-position interquartile range.

The exact formulas, minimum cross-section size, causality rules and candidate identities are frozen in `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md`.

## Existing V3-B context already known

V3-B already includes:

- primary-liquid stock count;
- positive-return breadth over 5/20 sessions;
- market medians of 5/20 return, ATR/close, close-position, relative volume and regular-market value-relative activity;
- stock-minus-market versions of several state variables.

V4-C therefore does not add another market median, breadth threshold, regime label, expert router or arbitrary bull/bear state. It adds only **cross-sectional dispersion**, allowing the same stock-level signal to be interpreted differently in compressed versus highly differentiated markets.

## Anti-overfit boundary

- one challenger only;
- no alternate quantile bands (10/90, 20/80, MAD, standard deviation) after outcomes;
- no separate short/medium dispersion candidates;
- no regime expert or threshold routing;
- no V4-A participation features;
- no sector conditioning;
- exact V3-B HGB and target remain unchanged;
- promotion gate is inherited unchanged from V4-A/V4-B;
- sessions `1225+` and fresh-forward remain sealed.

## Outcome boundary

This document does not authorize model scoring. V4-C must complete implementation, outcome-blind cache/audit and separate review before ordinal `019` may be fitted/scored on historical-development folds.