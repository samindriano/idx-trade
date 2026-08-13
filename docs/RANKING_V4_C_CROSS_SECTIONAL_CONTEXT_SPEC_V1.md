# Ranking V4-C Cross-Sectional Opportunity Context — Spec V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **FROZEN PRE-OUTCOME SPEC — IMPLEMENTATION AUTHORIZED, OUTCOME SCORING NOT AUTHORIZED**

## Research role

V4 is the final bounded alpha-generation program. `V4-C-CROSS-SECTIONAL-CONTEXT-V1` asks whether **cross-sectional opportunity dispersion** adds ranking information beyond frozen V3-B Structure-Lite.

Frozen benchmark: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`, exact 33 features, exact H10 TP-before-SL target, exact HGB architecture and the same six historical-development folds.

V3-B already contains market count, positive-return breadth, market medians and stock-minus-market state. It does not contain robust cross-sectional dispersion of return/risk/range-position states.

Primary question:

> Conditional on exact V3-B information, is a stock-level signal more or less informative when the liquid IDX opportunity set is compressed versus widely dispersed?

## Data and causality boundary

V4-C context must be constructed from the immutable signal-research panel and official exchange calendar using the **same causal V2 baseline-feature semantics** already defined in `src/idx_trade/research_features.py`.

Allowed raw inputs:

- `ticker`, `date`;
- official exchange-session identity;
- regular-market `high`, `low`, `close`, `volume`, `regular_market_value`;
- existing signal-panel tradability state only as a data-integrity check.

Historical Open is not required. Labels, TP/SL outcomes, future returns, future bars and any outcome-derived row filtering are prohibited from context construction.

All context statistics are computed from the **full causal primary-liquid universe on each signal date**, not from only rows whose H10 labels later resolve and not from only the validation/model subset.

Historical-development implementation must materialize signal sessions `<=1224`. Session `1225+` and post-2026-07-31 fresh-forward outcomes remain sealed.

## Shared definitions

For each signal date `d`, first construct the exact existing causal V2 baseline features and `universe_primary_liquid` flag from the bounded signal-research panel.

Let `U_d` be all rows on date `d` with `universe_primary_liquid == true`.

For a source feature `x`, define `finite(U_d, x)` as all finite `x` values among `U_d`.

A V4-C dispersion feature is defined only when there are at least:

`MIN_CROSS_SECTION = 50`

finite observations for that source on the date.

For a valid finite vector `v`, use explicit linear empirical quantiles:

- `q25 = quantile(v, 0.25, method="linear")`;
- `q75 = quantile(v, 0.75, method="linear")`;
- `IQR(v) = q75 - q25`.

A mathematically valid IQR may equal zero. No epsilon, log transform, winsorization or cross-date normalization is applied.

Each date-level context value is then joined identically onto every frozen V3-B model row for that signal date.

## Frozen V4-C challenger bundle

Candidate identity:

`V4-C-CROSS-SECTIONAL-CONTEXT-V1-DISPERSION-019`.

The challenger appends exactly four features, in this order:

1. `v4c_market_return_iqr_5`
   - source: exact causal `close_return_5`;
   - compute `IQR` across `U_d`;
   - require at least 50 finite source values.

2. `v4c_market_return_iqr_20`
   - source: exact causal `close_return_20`;
   - compute `IQR` across `U_d`;
   - require at least 50 finite source values.

3. `v4c_market_atr_iqr`
   - source: exact causal `atr14_over_close`;
   - compute `IQR` across `U_d`;
   - require at least 50 finite source values.

4. `v4c_market_close_position_iqr_20`
   - source: exact causal `close_position_20`;
   - compute `IQR` across `U_d`;
   - require at least 50 finite source values.

These four values are market-context features. They are constant across all model rows sharing the same signal date.

## Why these four and no others

- Return IQR at 5 and 20 sessions measures short/medium opportunity separation without inventing another return signal for the stock itself.
- ATR/close IQR measures heterogeneity of risk state, whereas V3-B currently knows only the market median ATR/close and the stock-minus-market ATR state.
- Close-position IQR measures whether stocks are clustered versus spread across their own 20-session ranges, whereas V3-B currently knows market median/current stock range position but not cross-sectional dispersion.

Explicitly excluded from first pass:

- 10/90 or 20/80 winner-loser spreads;
- cross-sectional standard deviation or MAD variants;
- skewness/kurtosis;
- volume/value dispersion, to avoid reopening V4-A through a context proxy;
- regime labels or expert routing;
- sector/peer dispersion;
- thresholded high-dispersion/low-dispersion flags;
- interactions manually multiplied with stock features.

The frozen HGB may learn nonlinear interactions between these context features and existing V3-B stock features without manually creating interaction candidates.

## Frozen first-pass candidates

Reserve V4 ordinals:

- `018`: `V4-C-CROSS-SECTIONAL-CONTEXT-V1-CONTROL-018` = exact frozen V3-B 33-feature control;
- `019`: `V4-C-CROSS-SECTIONAL-CONTEXT-V1-DISPERSION-019` = exact V3-B + exact four-feature V4-C bundle.

There is only one V4-C challenger. No second challenger and no within-family integration candidate exists.

## Model architecture

Both candidates use the exact frozen V3-B HGB template:

- training-only median `SimpleImputer`;
- `add_indicator=True`, `keep_empty_features=True`;
- no scaler;
- `HistGradientBoostingClassifier`;
- learning rate `0.05`;
- `max_iter=200`;
- `max_leaf_nodes=31`;
- `l2_regularization=1.0`;
- `random_state=42`;
- ranking score = same logit transform of clipped class-1 `predict_proba` used by V2/V3;
- score is not a calibrated probability.

No model-family, hyperparameter, threshold or feature-subset search is allowed.

## Historical-development folds

The eventual first-pass comparison uses V2F1..V2F6 only as already-consumed historical-development evidence. They are not independent validation for V4.

Control/challenger must use identical rows, target, train/gap/validation boundaries and eligibility semantics.

## Frozen promotion gate

V4-C inherits the **same challenger gate unchanged** from V4-A and V4-B.

The exact V3-B control must first reproduce frozen V3-B F1-F6 reference scores and metrics within absolute tolerance `1e-12`. Control-equivalence failure blocks challenger interpretation.

Absolute sanity requires:

- all reported metrics finite on every fold;
- `PR-AUC - prevalence > 0` on all six folds;
- `Q5-Q1 > 0` on all six folds.

Paired versus exact V3-B requires:

- PR-AUC improvement `>=0` on at least `5/6` folds;
- median paired PR-AUC improvement `>= +0.0015`;
- q25 paired PR-AUC improvement `>=0`;
- worst paired PR-AUC improvement `>= -0.0030`;
- median paired ROC-AUC change `>= -0.0020`;
- median paired Q5-Q1 change `>=0`;
- Q5-Q1 change `>=0` on at least `4/6` folds;
- on V2F5/V2F6, neither paired PR-AUC change may be below `-0.0030` and their median paired PR-AUC change must be `>=0`.

Top-decile lift and top-decile membership overlap remain mandatory diagnostics only.

Allowed challenger verdict: `PASS` or `FAIL`. No rescue variant is permitted after outcome access.

## Pre-outcome audit requirements

Before scoring, implementation review may inspect only outcome-independent diagnostics:

- number of distinct signal dates and primary-liquid cross-section size;
- feature finite/missing coverage;
- date-level feature distributions;
- row-level and date-level Spearman redundancy;
- especially overlap against existing V3-B market context columns;
- constant features;
- future-row causal invariance;
- exact V3-B prefix/order and session-1225 boundary.

Mechanical review is required if any V4-C feature is constant, has finite rate below 80%, or has absolute **date-level** Spearman correlation `>=0.95` with another V4-C feature or an existing V3-B date-level market-context feature.

A mechanical implementation bug may be repaired only to match this frozen mathematical definition. The bundle may not be redesigned to improve expected outcomes.

## Hard boundaries

This specification does not authorize:

- V4-C outcome scoring before implementation + blind audit + separate authorization;
- alternate dispersion formulas/lookbacks after outcomes;
- regime routing or context thresholds;
- sessions `1225+` materialization/scoring;
- post-2026-07-31 fresh-forward access or `FORWARD_OUTCOME_ACCESS_STARTED`;
- reopening/rescuing V4-A;
- adapting V4-C based on V4-B outcomes;
- calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live or main merge.