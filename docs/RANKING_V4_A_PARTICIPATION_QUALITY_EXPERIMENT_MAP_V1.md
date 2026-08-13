# Ranking V4-A — Participation Quality / Price Impact Experiment Map V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **PRE-OUTCOME DESIGN MAP — NOT AUTHORIZATION TO SCORE V4-A**

## Parent contract

This file refines Family 1 from `docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`.

Frozen control remains the exact final V3-B Structure-Lite architecture. V4-A must test incremental information beyond V3-B's existing:

- `relative_volume_20`;
- `log_regular_value_relative_20`;
- cross-sectional ranks of both;
- market medians / stock-minus-market versions of both;
- primary-liquidity universe rule;
- Structure-Lite breakout-volume confirmation.

Therefore V4-A is **not** a generic abnormal-volume experiment.

Primary research question:

> Conditional on the information already available to V3-B, does the quality, persistence, directional character, or price-impact efficiency of trading participation add robust cross-sectional ranking alpha?

## Data boundary

Primary observable participation input is regular-market traded value plus causal H/L/C/volume already present at the after-close signal timestamp.

The project must not require historical Open for V4-A. A close-to-close-return divided by same-day traded-value quantity may be retained only as an explicitly named proxy, not described as a canonical intraday Amihud measure, because its return window includes overnight information while the regular-market traded value window does not.

Features must be right-aligned and causal. No future bars, labels, TP/SL outcomes, broker-flow inference, or hidden order-flow reconstruction is allowed.

## Subresearch map

### A1 — Price-impact / fragility / absorption

Question:

> For a given amount of regular-market participation, how much price displacement or intraday range is produced, and is that relationship unusually fragile or absorptive relative to the stock's own history?

Economic distinction:

- large price/range movement on modest traded value can indicate fragile/high-impact trading;
- large traded value with limited displacement can indicate absorption/churn;
- this is different from V3-B simply knowing that today's volume/value is high relative to normal.

Pre-outcome feature-design candidates to reduce into one compact frozen bundle:

1. intraday high-low range percentage per regular-market traded value, normalized versus the stock's own trailing history;
2. absolute close-to-close move per regular-market traded value, explicitly labeled a close-to-close impact proxy;
3. short-window value-absorption efficiency: cumulative traded value relative to cumulative absolute price movement;
4. persistence of high/low impact over a short causal window.

Do not score multiple algebraically equivalent reciprocals/normalizations as separate candidates. One representation must be frozen before outcome access.

### A2 — Participation persistence / acceleration

Question:

> Is abnormal participation persistent across several sessions, building gradually, or merely a one-session spike?

Economic distinction:

V3-B observes current relative volume/value. A2 asks about the *path of participation itself*.

Pre-outcome feature-design candidates:

1. fraction of recent sessions with regular-market value above the stock's causal rolling baseline;
2. short-window mean/median of log relative traded value;
3. participation acceleration: short-window activity versus a longer causal baseline;
4. one-day concentration: current participation shock relative to the cumulative/median recent participation state.

A2 should prefer regular-market value over duplicating both value and raw volume variants unless the pre-outcome overlap audit shows distinct information.

### A3 — Directional participation asymmetry

Question:

> Is high participation associated more consistently with positive or negative price days?

This is **not** true signed order flow or broker net buying. With daily OHLCV/value data it is only a causal price-signed participation proxy.

Pre-outcome feature-design candidates:

1. signed-value imbalance over a short window: sum(sign(close-to-close return) * regular-market value) divided by total regular-market value;
2. signed-value imbalance over a medium window;
3. balance of high-participation positive versus negative sessions;
4. up-day versus down-day traded-value asymmetry.

Do not include multiple mathematically redundant forms in the final bundle.

### A4 — Structure-conditioned participation quality

Question:

> Around a causal Structure-Lite breakout/retest state, does continuous participation quality add information beyond the existing binary breakout-volume-confirmed feature?

Examples for design diagnostics only:

- participation build-up before a breakout;
- persistence of participation through a retest;
- price-impact/absorption state around the structural event.

A4 is **not an independent first-pass executable candidate** because it overlaps directly with the already successful V3-B Structure-Lite family and would create a high-risk interaction search. It may be considered only as a preregistered integration diagnostic if an independent V4-A participation hypothesis survives.

## Proposed executable budget

To avoid sub-family feature fishing, V4-A should not score A1, A2, A3, and A4 as four independent architectures.

The preferred executable reduction is:

### V4-A1 — Impact / Absorption bundle

Merge the nonredundant core of A1 into one compact feature bundle.

Intended information dimension: **price displacement per unit participation / absorption-fragility**.

### V4-A2 — Persistent Directional Participation bundle

Merge the nonredundant core of A2 + A3 into one compact feature bundle.

Intended information dimension: **whether participation is sustained and directionally associated with price movement rather than a one-day activity spike**.

### V4-A3 — One allowed family integration

Only if both V4-A1 and V4-A2 independently survive their frozen gates, allow one preregistered comparison of:

1. exact V3-B control;
2. best single V4-A survivor;
3. exact union of the frozen V4-A1 + V4-A2 bundles.

No rescue variants, alternate windows, alternate formula tournament, or second integration run after outcomes.

## What is diagnostic, not model selection

The following may be reported without becoming additional candidate architectures:

- feature missingness / coverage;
- pairwise feature correlations / redundancy audit;
- cross-sectional distribution stability through time;
- overlap with V3-B relative-volume/value features;
- monotonicity plots or bucket summaries on training-only data before validation outcomes, if explicitly separated from promotion evidence;
- structure-conditioned summaries for understanding only.

## Required pre-outcome decisions before implementation scoring

Before V4-A outcome access, freeze:

1. exact feature formulas;
2. exact lookback windows;
3. treatment of zeros/missing/nonfinite values;
4. whether each raw participation feature is transformed to own-history-relative, within-date cross-sectional rank, or another single fixed representation;
5. exact V4-A1 and V4-A2 feature columns/order;
6. exact V3-B control identity;
7. folds and candidate rows;
8. metrics and paired promotion gates;
9. candidate-count accounting;
10. explicit prohibition on fresh-forward outcome access.

## Current recommendation

Proceed in this order:

1. **A1 Impact / Absorption design audit**;
2. **A2+A3 Persistent Directional Participation design audit**;
3. overlap/redundancy review against existing V3-B volume/value information;
4. freeze two compact executable bundles at most;
5. independent review;
6. only then implement/score historical V4-A candidates.

No V4-A outcomes are authorized by this experiment map.