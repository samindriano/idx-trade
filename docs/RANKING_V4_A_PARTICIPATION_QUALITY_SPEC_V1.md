# Ranking V4-A — Participation Quality / Price Impact Spec V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **FROZEN PRE-OUTCOME SPEC — A1/A2 IMPLEMENTATION AUTHORIZED, OUTCOME SCORING NOT YET AUTHORIZED**

## Research role

V4 is the final alpha-generation program. Family V4-A asks whether participation quality adds ranking information beyond the frozen V3-B Structure-Lite champion.

Frozen control: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` with exact 33 features, exact H10 TP-before-SL target, exact HGB architecture and exact chronological folds.

V3-B already knows current relative volume, current regular-market traded-value activity, cross-sectional/market-relative versions of those quantities, the primary-liquidity universe and binary breakout-volume confirmation. V4-A therefore does **not** test generic volume anomaly.

Primary question:

> Conditional on frozen V3-B information, does price-impact/absorption quality or persistent directional participation add robust cross-sectional ranking alpha?

## Data and causality boundary

Allowed feature inputs at the after-close signal timestamp are only:

- `ticker`, `date`;
- official exchange-session identity;
- regular-market `high`, `low`, `close`, `volume`, `regular_market_value` already present in the immutable signal-research panel.

Historical Open is not required. Labels, TP/SL outcomes, realized future returns, broker-flow inference and any future bar are prohibited.

All windows are defined in **official-session space**. Missing/suspended/provider-gap rows are not silently interpreted as zero trading. A feature that requires exact consecutive observations remains missing when that requirement is not met.

Required source boundary for the first V4-A historical-development implementation: signal sessions `<=1224`. Sessions `1225+` and all post-2026-07-31 fresh-forward outcomes remain sealed.

## Shared definitions

Let signal session be `s`.

A valid regular-market value is finite and strictly positive. A valid close/high/low is finite and strictly positive, with `high >= low`.

Daily regular-session range fraction:

`range_pct_t = (high_t - low_t) / close_t`.

Adjacent close return is defined only when both `t` and official session `t-1` have valid rows for the ticker:

`cc_return_t = close_t / close_{t-1} - 1`.

Raw range-impact proxy:

`range_impact_t = range_pct_t / regular_market_value_t`.

Raw close-impact proxy:

`close_impact_t = abs(cc_return_t) / regular_market_value_t`.

The close-impact quantity is explicitly a **close-to-close impact proxy**, not canonical intraday Amihud, because the return interval can contain overnight information while regular-market traded value does not.

For a nonnegative current quantity `x` and strictly positive baseline `b`, use the frozen centered transform:

`centered_log_ratio(x,b) = log1p(x / b) - log(2)`.

This equals zero when `x=b`, remains finite at `x=0`, and requires no arbitrary epsilon.

For trailing baseline calculations, `PRIOR20(s)` means official sessions `[s-20, s-1]`. A median baseline requires at least `10` valid observations in that exact official-session window.

## V4-A1 — Impact / Absorption bundle

Candidate identity: `V4-A-PARTICIPATION-V1-IMPACT-013`.

The bundle contains exactly three appended features, in this order:

1. `v4a_range_impact_logrel20`
   - current `range_impact_s` relative to median valid `range_impact` in `PRIOR20(s)`;
   - transform: `centered_log_ratio(current, baseline)`;
   - missing if current invalid or baseline has fewer than 10 valid strictly-positive observations.

2. `v4a_close_impact_logrel20`
   - current `close_impact_s` relative to median valid `close_impact` in `PRIOR20(s)`;
   - transform: `centered_log_ratio(current, baseline)`;
   - current zero impact is allowed; baseline requires at least 10 valid strictly-positive observations;
   - missing if adjacent official-session close is unavailable.

3. `v4a_high_range_impact_fraction_5`
   - for every session `u`, define a causal high-impact flag `I_u = 1[range_impact_u > median(PRIOR20(u))]` when both sides are valid;
   - at signal `s`, return the mean of flags for exact official sessions `[s-4,s]`;
   - all five flags must exist; otherwise missing.

A1 intentionally captures current impact, close-to-close displacement efficiency and persistence of unusually high range impact. Algebraic reciprocals or alternate normalization variants are not separate candidates.

## V4-A2 — Persistent Directional Participation bundle

Candidate identity: `V4-A-PARTICIPATION-V1-PERSIST-DIRECTION-014`.

The bundle contains exactly four appended features, in this order:

1. `v4a_value_persistence_fraction_5`
   - for every session `u`, define `P_u = 1[value_u > median(PRIOR20(u) value)]` when the baseline has at least 10 valid observations;
   - at signal `s`, return the mean of `P_u` over exact official sessions `[s-4,s]`;
   - all five flags must exist; otherwise missing.

2. `v4a_value_acceleration_log_5v20`
   - short state = median valid regular-market value on exact sessions `[s-4,s]`, requiring all five values valid;
   - older baseline = median valid regular-market value on official sessions `[s-24,s-5]`, requiring at least 10 valid values;
   - feature = `log(short_state / older_baseline)`.

3. `v4a_signed_value_5`
   - over exact sessions `[s-4,s]`, compute `sum(sign(cc_return_u) * value_u) / sum(value_u)`;
   - all five signed observations must be valid; otherwise missing;
   - flat return has sign zero.

4. `v4a_signed_value_20`
   - same price-signed traded-value ratio over official sessions `[s-19,s]`;
   - requires at least 10 valid adjacent-return/value observations.

These are **price-signed participation proxies**, not buyer-initiated order flow, broker net buying or ownership flow.

## Frozen first-pass candidates

Reserve V4 ordinals as follows:

- `012`: `V4-A-PARTICIPATION-V1-CONTROL-012` = exact V3-B 33-feature control;
- `013`: `V4-A-PARTICIPATION-V1-IMPACT-013` = exact V3-B + exact A1 three-feature bundle;
- `014`: `V4-A-PARTICIPATION-V1-PERSIST-DIRECTION-014` = exact V3-B + exact A2 four-feature bundle.

A1 and A2 must be fully implemented/frozen before either outcome result is inspected. Their first historical scoring should be atomic/parallel-equivalent against the same control.

No A1+A2 integration candidate exists in the first-pass run. One integration is permitted later **only if both 013 and 014 independently pass**.

## Model architecture

All three candidates use the frozen V3-B HGB template:

- median `SimpleImputer` fitted on training only;
- `add_indicator=True`, `keep_empty_features=True`;
- no scaler;
- `HistGradientBoostingClassifier`;
- learning rate `0.05`;
- `max_iter=200`;
- `max_leaf_nodes=31`;
- `l2_regularization=1.0`;
- `random_state=42`;
- ranking score = logit of clipped class-1 `predict_proba` as in frozen V2/V3 pointwise HGB;
- score is not a calibrated probability.

No hyperparameter/model-family/threshold search is allowed.

## Historical-development folds

The first V4-A comparison uses the already-consumed six Ranking-V2 folds `V2F1..V2F6` as development evidence. They are **not** independent holdouts for V4.

All three candidates use identical rows, targets, train/gap/validation boundaries and eligibility semantics.

## Frozen promotion gate per challenger

The exact V3-B control must first reproduce the frozen V3-B reference on the corresponding historical rows within `1e-12` absolute tolerance for scores and metrics. A control-equivalence failure blocks challenger interpretation.

Absolute sanity for each challenger:

- all reported metrics finite on every fold;
- `PR-AUC - prevalence > 0` on all six folds;
- `Q5-Q1 > 0` on all six folds.

Paired versus exact V3-B control:

- PR-AUC improvement `>=0` on at least `5/6` folds;
- median paired PR-AUC improvement `>= +0.0015`;
- q25 paired PR-AUC improvement `>=0`;
- worst paired PR-AUC improvement `>= -0.0030`;
- median paired ROC-AUC change `>= -0.0020`;
- median paired Q5-Q1 change `>=0`;
- Q5-Q1 change `>=0` on at least `4/6` folds;
- on V2F5/V2F6, neither paired PR-AUC change may be below `-0.0030` and their median paired PR-AUC change must be `>=0`.

Top-decile lift and top-decile membership overlap remain mandatory diagnostics but are not hard promotion gates in this first family. This avoids changing the primary objective after V3-B top-decile behavior became known.

Allowed verdict for each challenger: `PASS` or `FAIL`. No rescue variant is allowed after outcome access.

## Diagnostics allowed before outcome scoring

Pre-outcome implementation review may inspect only feature construction/provenance diagnostics, including:

- missingness/coverage;
- finite-value checks;
- feature distributions without labels;
- pairwise feature correlations/redundancy without labels;
- exact overlap audit against existing V3-B feature columns;
- causal invariance under appending future rows.

These diagnostics may simplify/repair an implementation only when required to match this frozen mathematical definition. They may not change formulas to improve outcome metrics.

## Hard boundaries

This specification does not authorize:

- sessions `1225+` outcome materialization;
- post-2026-07-31 fresh-forward outcome access or `FORWARD_OUTCOME_ACCESS_STARTED`;
- A1/A2 formula rescue after seeing outcomes;
- A1+A2 integration before both independently pass;
- reopening V3-B;
- calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.
