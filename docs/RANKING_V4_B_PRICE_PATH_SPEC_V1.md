# Ranking V4-B Price-Path Quality — Spec V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **FROZEN PRE-OUTCOME SPEC — IMPLEMENTATION MAY FOLLOW REVIEW; OUTCOME SCORING NOT AUTHORIZED**

## Research role

V4 is the final bounded alpha-generation program. `V4-B-PRICE-PATH-V1` asks whether the formation path of the current setup adds robust ranking information beyond frozen V3-B Structure-Lite.

Frozen control: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`, exact 33 features, exact H10 TP-before-SL target, exact HGB architecture and the same six historical-development folds.

V3-B already knows 5/20-session return magnitude, ATR-normalized volatility, current 20-session range position, distances to 20/60-session highs/lows, market-relative state, volume/value context and causal support/resistance/breakout/retest geometry. V4-B therefore does **not** add another generic momentum, volatility, high/low-distance or candlestick-pattern zoo.

Primary question:

> Conditional on frozen V3-B state and geometry, does coherent versus jump-concentrated price travel or repeated daily-range acceptance/rejection add robust cross-sectional ranking alpha?

## Data and causality boundary

Allowed feature inputs at the after-close signal timestamp are only:

- `ticker`, `date`;
- official exchange-session identity;
- regular-market `high`, `low`, `close` from the immutable signal-research panel.

Historical Open is not required. Volume/value is intentionally not required by this family. Labels, TP/SL outcomes, future returns and any future bar are prohibited.

All windows are defined in official-session space. A missing official-session observation is never silently treated as a flat return or neutral candle.

Historical-development implementation must materialize signal sessions `<=1224`. Session `1225+` and post-2026-07-31 fresh-forward outcomes remain sealed.

## Shared definitions

Let signal session be `s`.

A valid close/high/low is finite and strictly positive with `high >= low`.

For two adjacent official sessions with valid closes, define daily log return:

`lr_t = log(close_t / close_{t-1})`.

An exact W-return path ending at `s` requires valid ticker rows on every official session `[s-W, ..., s]`, yielding exactly W adjacent log returns. If any official session or required close is missing, every exact-path feature using that W is missing.

For one valid daily bar with `high > low`, define close-location value:

`clv_t = (2*close_t - high_t - low_t) / (high_t - low_t)`.

Numerical values are clipped only for floating-point tolerance to `[-1,1]` after validating `low <= close <= high`. A zero-range day (`high == low`) has undefined close location and is missing rather than assigned a neutral value.

## V4-B1 — Path Coherence / Jump Concentration

Candidate identity: `V4-B-PRICE-PATH-V1-COHERENCE-016`.

The bundle contains exactly three appended features, in this order:

1. `v4b_path_efficiency_5`
   - use the exact five daily log returns over official sessions `[s-4,...,s]`, requiring closes on `[s-5,...,s]`;
   - `gross = sum(abs(lr))`;
   - if `gross > 0`, feature = `abs(sum(lr)) / gross`;
   - if `gross == 0` because all five log returns are exactly zero, feature = `0`;
   - range `[0,1]`.

2. `v4b_path_efficiency_20`
   - same definition over exact 20 daily log returns ending at `s`, requiring closes on `[s-20,...,s]`;
   - if total absolute movement is zero, return `0`;
   - range `[0,1]`.

3. `v4b_largest_move_share_20`
   - use the same exact 20 daily log returns;
   - `gross = sum(abs(lr))`;
   - if `gross > 0`, feature = `max(abs(lr)) / gross`;
   - if `gross == 0`, feature = `0`;
   - range `[0,1]`.

Interpretation:

- path efficiency asks how much of gross travel survives as net directional displacement;
- largest-move share asks whether the path is dominated by one session.

No alternate 10/60-session variants, skew/kurtosis features, MAX/MIN return variants, trend-R2 variants or thresholded jump flags are separate candidates.

## V4-B2 — Range Acceptance / Rejection Quality

Candidate identity: `V4-B-PRICE-PATH-V1-RANGE-ACCEPTANCE-017`.

The bundle contains exactly three appended features, in this order:

1. `v4b_range_acceptance_mean_5`
   - mean `clv_t` over exact official sessions `[s-4,...,s]`;
   - all five close-location values must be valid, otherwise missing;
   - range `[-1,1]`.

2. `v4b_range_acceptance_mean_20`
   - mean valid `clv_t` in official sessions `[s-19,...,s]`;
   - require at least 10 valid close-location observations in that exact official-session window;
   - missing observations are excluded, never replaced by zero;
   - range `[-1,1]`.

3. `v4b_extreme_close_balance_5`
   - for each of exact sessions `[s-4,...,s]`, map valid `clv_t` to:
     - `+1` if `clv_t >= +0.5` (close in top quarter of the daily range),
     - `-1` if `clv_t <= -0.5` (close in bottom quarter),
     - `0` otherwise;
   - all five values must be valid;
   - feature = mean of those five mapped values;
   - range `[-1,1]`.

B2 measures repeated daily-range acceptance/rejection. It is distinct from the existing `close_position_20`, which measures the current close inside the aggregate 20-session high-low range, and from Structure-Lite support/resistance geometry.

No separate wick family, candlestick-pattern family, Open-dependent body/gap feature or structure-conditioned interaction exists in first pass.

## Frozen first-pass candidates

Reserve V4 ordinals:

- `015`: `V4-B-PRICE-PATH-V1-CONTROL-015` = exact frozen V3-B 33-feature control;
- `016`: `V4-B-PRICE-PATH-V1-COHERENCE-016` = exact V3-B + exact B1 three-feature bundle;
- `017`: `V4-B-PRICE-PATH-V1-RANGE-ACCEPTANCE-017` = exact V3-B + exact B2 three-feature bundle.

Both challengers must be fully implemented/frozen before either outcome result is inspected. First historical scoring must be atomic / parallel-equivalent against the same exact control.

No B1+B2 integration candidate exists in first pass. One integration may be designed only if both `016` and `017` independently PASS and receives a separate spec/review/authorization.

## Model architecture

All three candidates reuse the exact frozen V3-B HGB template:

- training-only median `SimpleImputer`;
- `add_indicator=True`, `keep_empty_features=True`;
- no scaler;
- `HistGradientBoostingClassifier`;
- learning rate `0.05`;
- `max_iter=200`;
- `max_leaf_nodes=31`;
- `l2_regularization=1.0`;
- `random_state=42`;
- ranking score = the same logit transform of clipped class-1 `predict_proba` used by V2/V3;
- score is not a calibrated probability.

No model-family, hyperparameter or threshold search is allowed.

## Historical-development folds

The first V4-B comparison uses V2F1..V2F6 only as already-consumed historical-development evidence. They are not independent holdouts for V4.

All candidates use identical rows, target, train/gap/validation boundaries and eligibility semantics.

## Frozen promotion gate per challenger

To reduce adaptive degrees of freedom after V4-A, V4-B inherits the **same challenger gate unchanged**.

The exact V3-B control must first reproduce frozen V3-B F1-F6 reference scores and metrics within absolute tolerance `1e-12`. Control-equivalence failure blocks challenger interpretation.

Absolute sanity requires for each challenger:

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

Top-decile lift and top-decile membership overlap are mandatory diagnostics only, not hard gates.

Allowed verdict per challenger: `PASS` or `FAIL`. No rescue variant is permitted after outcome access.

## Pre-outcome audit requirements

Before outcome scoring, implementation review may inspect only outcome-independent diagnostics:

- finite/missing coverage;
- feature distributions;
- pairwise Spearman redundancy within B1/B2;
- Spearman overlap against the exact existing V3-B 33 features, especially return, ATR and range-position features;
- causal invariance when future rows are appended;
- exact candidate feature order and boundary checks.

A feature with a mechanical definition bug may be repaired only to match this frozen mathematics. Outcome-blind redundancy is documented; it is not an invitation to search alternate formulas.

## Hard boundaries

This specification does not authorize:

- V4-B outcome scoring before implementation + blind audit + separate run authorization;
- any B1/B2 rescue after outcomes;
- B1+B2 integration before both independently PASS;
- sessions `1225+` materialization/scoring;
- post-2026-07-31 fresh-forward access or `FORWARD_OUTCOME_ACCESS_STARTED`;
- reopening V4-A or V3;
- calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live or main merge.