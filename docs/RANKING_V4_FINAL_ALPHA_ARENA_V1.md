# Ranking V4 Final Alpha Arena V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **DESIGN ARENA ONLY — NOT AUTHORIZATION TO SCORE V4 CANDIDATES**

## Purpose

V4 is the final alpha-generation research round before the project moves primary attention to fresh-forward validation, path risk, calibration/uncertainty, portfolio construction, costs/execution, and paper/live layers.

The frozen V3-B Structure-Lite architecture remains the immutable benchmark. V4 must search for **orthogonal information families**, not a new model zoo or post-hoc feature tournament.

## Frozen seven-family shortlist

1. **Liquidity & Participation Quality** — Does the move have healthy, persistent trading participation and favorable price-impact characteristics beyond the volume/value information already known by V3-B?
2. **Price-Path Quality** — Is the current setup formed by a persistent, coherent path rather than one-off spikes, noisy extremes, rejection-heavy ranges, or unstable return distribution?
3. **Cross-Sectional Opportunity Context** — Does the day-level dispersion/opportunity environment alter the quality of stock-level signals without explicit regime-expert routing?
4. **Peer / Sector Relative Strength** — Is the stock truly strong relative to economically relevant peers, conditional on a defensible PIT sector-history data gate?
5. **Systematic-Adjusted / Idiosyncratic Strength** — After removing market sensitivity/common movement, does residual/idiosyncratic strength add information beyond V3-B's simpler market-relative features?
6. **Catalyst / Fundamental Context** — Does fresh, point-in-time-available fundamental/event information improve ranking beyond market-derived signals, conditional on a strict availability-time provenance gate?
7. **Flow / Ownership Information** — Does broker/investor-flow or ownership-participation information add alpha, conditional on complete PIT provenance, correction/versioning rules, and data readiness?

## Overfitting boundary

The seven families are a **design shortlist**, not seven automatically executable experiments.

Before outcome scoring, V4 must reduce this arena to a bounded executable set. The intended budget is:

- normally three main executable families;
- at most one conditional wildcard family if its data gate becomes defensible;
- one frozen feature bundle per executed family;
- exact V3-B model/target/folds unless a separate preregistered question explicitly requires otherwise;
- no model-family tournament, broad hyperparameter search, threshold search, or post-result rescue;
- at most one preregistered integration comparison after independent family results are known;
- simpler architecture wins unless the integration is materially more robust.

Brainstorming can be broad; **scoring must remain narrow**.

## Known overlap rule

Ideas that largely inspect the same underlying information must be merged before execution rather than tested as many variants. For example, tail asymmetry, trend coherence, candle/range quality, and spike concentration belong under the single **Price-Path Quality** family unless a future pre-outcome overlap audit establishes a genuinely orthogonal question.

## V3-B benchmark information already present

V3-B already contains price returns, volatility, range position, relative volume, traded-value-relative activity, cross-sectional ranks, market context, stock-minus-market relative features, and eight causal Structure-Lite support/resistance/breakout/retest features including breakout-volume confirmation.

Therefore V4 families must demonstrate incremental information beyond these existing dimensions rather than re-labeling existing features.

## Current first family

The first family to specify is:

**V4-A — Liquidity & Participation Quality / Price Impact**.

Its detailed experiment map is maintained separately in:

`docs/RANKING_V4_A_PARTICIPATION_QUALITY_EXPERIMENT_MAP_V1.md`

No V4-A outcome access is authorized by this arena document.
