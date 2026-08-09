# IDX Trade — Stage 3 Implementation Plan V1

Status: PRE-OUTCOME IMPLEMENTATION FREEZE
Date: 2026-08-09
Branch: `research/idx-stage3-v1`
Base: `data/idx-data-002c` at approved `STAGE2_SPEC_GO`

This document freezes implementation choices before the immutable 981,940-row
research panel is used for any development outcome/model evaluation. It does not
open or authorize the locked final holdout.

## 1. Immutable research input

- contract: `SIGNAL_RESEARCH_HLCV`;
- exact calendar: 1,260 official IDX sessions, `2021-04-29 -> 2026-07-31`;
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- research manifest SHA-256: `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- strict execution-grade 1260 remains FAIL and is not modified by Stage 3.

Stage-3 development code must hash-check the panel before execution.

## 2. Holdout access boundary

The locked holdout begins at session 1009 (`2025-07-15`). Stage-3 development
must not read holdout outcomes.

Development validation ends at F3 session 942 (`2025-03-20`). Because the
maximum pre-registered label sensitivity horizon is H=20, the latest source bar
needed by development is session 962. The runtime runner therefore reads the
panel through session 962 only and rejects an unfiltered fallback.

Development label builders are hard-bounded by one-based official-session
indices:

- maximum signal index: 942;
- maximum future source index: 962.

This makes accidental holdout label inspection a code-level failure rather than
a procedural promise.

## 3. Primary label implementation

Primary V1:

- reference: `Close_t` (`SIGNAL_REFERENCE_CLOSE`), never a claimed fill;
- ATR: simple ATR14 through t using observed valid ACTIVE research bars;
- H=10;
- SL distance = `1.0 * ATR14_t`;
- TP distance = `1.5 * SL distance`;
- no Open dependency.

Explicit outcomes:

- `TP_FIRST`;
- `SL_FIRST`;
- `AMBIGUOUS_SAME_BAR`;
- `NO_BARRIER_HIT`;
- `UNRESOLVED_PATH`;
- `UNRESOLVED_HORIZON_END`;
- `INVALID_BARRIER`.

A resolved/no-touch label requires the complete future official-session path for
the configured H. Missing/non-ACTIVE path evidence fails closed. Same-bar TP+SL
is never ordered by assumption.

H=5 and H=20 are generated as declared sensitivity ledgers only. H=10 remains
the sole primary binary model target.

## 4. Primary causal universe

The Stage-2 primary broad liquid rule is implemented in official-session space:

- trailing window: 60 official sessions ending at t;
- minimum observed ACTIVE rows with valid Regular-Market Value: 20;
- trailing observed-value median >= IDR 1,000,000,000.

Top-100 and top-300 are causal date-by-date sensitivity views based on the same
trailing value statistic. No current-survivor/static membership is used.

## 5. Baseline feature freeze

Primary compact model columns:

- 5-observation close return;
- 20-observation close return;
- ATR14 / Close;
- Close position in trailing 20-observation high/low range;
- ATR-normalized distance to 20-observation high;
- ATR-normalized distance to 20-observation low;
- ATR-normalized distance to 60-observation high;
- ATR-normalized distance to 60-observation low;
- current Volume / trailing-20 median Volume;
- log(current Regular-Market Value / trailing-20 median Value);
- observed ACTIVE-session count;
- exact security age in official sessions when identifiable inside the certified calendar.

### Security-age implementation clarification

The Stage-2 concept `security age in sessions at t` cannot be exactly reconstructed
for securities listed before the certified calendar begins. Filling such names
with "sessions since 2021-04-29" would create a calendar-time proxy and is
prohibited.

Therefore:

- in-window listing: exact official-session age is populated;
- pre-window/unknown listing age: model value is NaN;
- `security_age_left_censored` is retained as a diagnostic column;
- training-only `SimpleImputer(add_indicator=True)` handles missing exact age;
- no fabricated pre-2021 exchange calendar is introduced.

This is a pre-outcome implementation clarification, not a response to model
performance.

No primary feature contains `Open`.

## 6. Frozen temporal validation

Development folds remain exactly:

- F1 train 1-504, gap 505-524, validation 525-650;
- F2 train 1-650, gap 651-670, validation 671-796;
- F3 train 1-796, gap 797-816, validation 817-942.

Each 20-session gap is the H_max purge/embargo boundary. Same-date securities
remain grouped.

Inside each fold training block:

- nominal chronological split: 80% model-fit prefix / 20% calibration tail;
- an additional H=20 maturity gap is removed immediately before calibration;
- no fit-row label path may overlap calibration dates.

## 7. Frozen baseline models

### Base rate

Constant probability equal to the resolved TP_FIRST prevalence in the complete
fold training block.

### Momentum

Fixed score: causal 20-observation close return. Missing score values use a
median fitted on the model-fit prefix only. Probability mapping is Platt/logistic
calibration fit on the chronological calibration tail only.

### Compact logistic

- preprocessing: median imputation with missing indicators, then StandardScaler;
- solver: `lbfgs`;
- C: `1.0`;
- max_iter: `1000`;
- seed: `42`.

### Bounded tree challenger

`HistGradientBoostingClassifier` with:

- learning_rate: `0.05`;
- max_iter: `200`;
- max_leaf_nodes: `31`;
- l2_regularization: `1.0`;
- seed: `42`.

No hyperparameter search is permitted in the primary development run.

## 8. Calibration and metrics

Primary calibration: Platt/logistic mapping fitted on the chronological
calibration tail only. Calibration requires both binary classes; otherwise the
fold/model calibration result fails explicitly.

Metrics:

- primary: PR-AUC;
- secondary: ROC-AUC, Brier score, ECE;
- probability bins are fixed from calibration/training probabilities, never from
  validation or holdout data.

The Stage-2 advancement rule is evaluated exactly: a challenger must beat both
the base-rate and momentum baselines in at least two of three development folds,
without hidden denominator/coverage changes.

## 9. Runtime output contract

The bounded development runner writes:

- H5/H10/H20 label ledgers;
- compact causal feature table;
- primary resolved model table;
- per-fold out-of-fold predictions;
- fold metrics;
- label outcome prevalence/ambiguity/unresolved diagnostics;
- advancement-rule result;
- artifact SHA-256 values;
- explicit `holdout_outcome_accessed=false` record.

No model is persisted for deployment and no BUY/SELL/EXIT signal is produced.

## 10. Stop rules

Stop rather than repair after seeing results if:

- panel hash mismatches;
- calendar boundary mismatches;
- any label request crosses session 962;
- any holdout row enters the model table;
- a fold lacks both classes;
- calibration tail lacks both classes;
- a feature depends on Open;
- an unexpected material coverage shift appears;
- implementation behavior contradicts the frozen Stage-2 contract.

A material specification change after development outcomes are observed must be
recorded as a new research iteration/version. V1 results cannot be silently
rescued by changing label geometry, liquidity thresholds, folds, or model
parameters.
