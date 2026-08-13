# Ranking V2 Research Specification — V1

Date: 2026-08-09 (Asia/Jakarta)
Status: **FROZEN BEFORE RANKING-V2 OUTCOME RUNS**
Branch: `research/idx-ranking-v2-spec-v1`

## 1. Purpose

Ranking V1 failed its one-shot locked historical holdout. The bounded Stage-5
post-mortem supports a regime/covariate-shift hypothesis, especially large
changes in volatility, breadth, market returns, and relative market value, while
several structure-feature relationships remained directionally stable.

Ranking V2 is therefore a new research architecture. It is not a rescue or
reinterpretation of Ranking V1.

The full historical window through `2026-07-31` is now development/research
knowledge. No result on that period can be described as independent final
validation. Any independent Ranking V2 claim requires fresh forward data
strictly after `2026-07-31`, accumulated after V2 is frozen.

Probability V1 remains `PROBABILITY_V1_NOT_READY_DEFERRED`. Ranking V2 remains
ranking-only; no calibrated probability claim is authorized here.

## 2. Frozen target and universe semantics

Unchanged from the V1 research contract:

- signal timestamp: after session-t close;
- reference price: `Close_t` for label geometry only;
- primary label: H10 first-touch barrier;
- ATR14;
- SL distance: `1.0 * ATR14`;
- TP distance: `1.5 * SL distance`;
- same-bar TP+SL remains `AMBIGUOUS_SAME_BAR` and is not guessed;
- primary model rows are resolved `TP_FIRST` / `SL_FIRST` only;
- primary universe is the existing causal broad-liquid universe;
- Open is prohibited from primary V2 features;
- all features and market context use information available no later than close t.

H5/H20 may remain descriptive sensitivity artifacts in the prepared cache, but
**cannot select or rescue a Ranking V2 candidate**. Candidate selection is H10
only.

## 3. Performance prerequisite and prepared-cache boundary

Model workers must not rebuild deterministic labels/features independently.
Before parallel V2 runs, the separate performance track must complete:

1. exact full-frozen-panel legacy-vs-fast label equivalence;
2. local wall-clock and peak-memory benchmark;
3. one immutable prepared Ranking-V2 model table/cache with SHA-256 provenance.

The cache must be generated once and then treated read-only by all model workers.
No candidate worker may regenerate labels, alter feature definitions, or modify
cache contents.

Required prepared-table identity columns:

- `ticker`;
- `date`;
- `signal_session_index` (one-based official-session index);
- `binary_target`;
- `label_status`;
- `universe_primary_liquid`.

The table must also contain all frozen V1 features and all V2 features defined
below.

## 4. V2 feature families

### 4.1 Core stock features used to build cross-sectional ranks

The following ten V1 features remain eligible as stock-state inputs:

1. `close_return_5`
2. `close_return_20`
3. `atr14_over_close`
4. `close_position_20`
5. `distance_high_20_atr`
6. `distance_low_20_atr`
7. `distance_high_60_atr`
8. `distance_low_60_atr`
9. `relative_volume_20`
10. `log_regular_value_relative_20`

For each date, among that date's causal primary-liquid universe, compute a
within-date percentile rank for each finite feature value. The frozen naming
convention is:

`xs_rank_<source_feature>`

Ranks are computed with `rank(method="average", pct=True)`. Missing source
features remain missing; model-specific training-only imputation handles them.
No future date is used.

### 4.2 Explicitly excluded from V2 core

These V1 features are excluded from the V2 core candidate sets:

- `observed_session_count`;
- `security_age_sessions_exact`.

Reason: both can drift mechanically with calendar time and may act as implicit
time/era proxies. This is a design-control decision informed by the post-mortem,
not an independently validated claim that they are harmful.

They may be reconsidered only in a separately frozen future sensitivity study;
they cannot be reintroduced ad hoc during the V2 candidate run.

### 4.3 Causal market-state context

For every signal date, compute from the **entire causal primary-liquid universe
for that date**, not only resolved-label rows:

1. `market_primary_liquid_count`
2. `market_breadth_return_5_positive`
3. `market_breadth_return_20_positive`
4. `market_median_close_return_5`
5. `market_median_close_return_20`
6. `market_median_atr14_over_close`
7. `market_median_close_position_20`
8. `market_median_relative_volume_20`
9. `market_median_log_regular_value_relative_20`

No regime labels or optimized thresholds are created. These remain continuous
causal context variables.

### 4.4 Stock-minus-market relative features

Six frozen market-relative features are added:

1. `market_relative_close_return_5`
2. `market_relative_close_return_20`
3. `market_relative_atr14_over_close`
4. `market_relative_close_position_20`
5. `market_relative_relative_volume_20`
6. `market_relative_log_regular_value_relative_20`

Each is stock raw value minus the same-date primary-liquid market median.

### 4.5 Sector-relative features

**Not included in Ranking V2 V1.**

A sector-relative hypothesis remains conceptually valid, but no sector-relative
feature may enter these candidate runs until a point-in-time-safe sector mapping
with explicit historical validity is separately established. Current V2 must not
silently use today's sector classifications for historical rows.

## 5. Frozen candidate set

No additional candidate, architecture, feature family, or hyperparameter search
may be added after V2 outcome runs begin.

### CONTROL — `V1_HGB_CONTROL`

Purpose: reproduce the failed V1 architecture as a research comparator on the
new V2 development folds.

Features: exact V1 `BASELINE_FEATURE_COLUMNS` (12 raw features).

Model: exact frozen HGB settings:

- `learning_rate=0.05`
- `max_iter=200`
- `max_leaf_nodes=31`
- `l2_regularization=1.0`
- `random_state=42`

The control is not eligible to become the V2 champion.

### V2-A — `LOGISTIC_XS`

Purpose: test whether cross-sectional normalization alone contains robust linear
ranking information.

Features: ten `xs_rank_*` features only.

Model:

- training-only median imputation;
- standardization fitted on training rows only;
- LogisticRegression;
- `C=1.0`;
- `solver="lbfgs"`;
- `max_iter=1000`;
- `random_state=42`.

No hyperparameter search.

### V2-B — `HGB_XS`

Purpose: isolate nonlinear interactions on cross-sectional normalized stock
features without explicit market context.

Features: ten `xs_rank_*` features only.

Model: exact frozen HGB settings used by V1:

- `learning_rate=0.05`
- `max_iter=200`
- `max_leaf_nodes=31`
- `l2_regularization=1.0`
- `random_state=42`.

No hyperparameter search.

### V2-C — `HGB_XS_MARKET`

Purpose: test the primary post-mortem hypothesis that ranking requires explicit
transportable stock-relative representation plus continuous market-state
context.

Features:

- ten `xs_rank_*` features;
- nine continuous `market_*` context features;
- six `market_relative_*` features.

Total frozen core features: 25.

Model: exact same HGB hyperparameters as `HGB_XS` and V1. This deliberately
isolates the feature/context hypothesis rather than confounding it with tuning.

### V2-D — `PAIRWISE_LOGISTIC_XS`

Purpose: bounded test of objective mismatch: the real task is same-date ranking,
not merely pooled binary classification.

Features: ten `xs_rank_*` features only.

Training objective:

- deterministic within-date positive-vs-negative pair construction;
- at most 256 unique positive-negative pairs per date;
- if a date has <=256 Cartesian positive-negative pairs, use all;
- otherwise sample 256 without replacement using a deterministic date-derived
  RNG seeded from global seed 42;
- each selected `(positive, negative)` pair contributes both ordered examples:
  `x_pos - x_neg -> 1` and `x_neg - x_pos -> 0`;
- item-level median imputer and StandardScaler are fitted on training items only
  before pair differences are formed;
- final pairwise LogisticRegression uses `C=1.0`, `solver="lbfgs"`,
  `max_iter=1000`, `random_state=42`.

Validation scoring is the learned item utility/decision score. No pairwise
probability is interpreted as calibrated probability.

No alternative pair sampler, pair budget, ranking loss, or ranking library may
be tried during this V2 run.

## 6. V2 chronological development folds

V2 uses six expanding-window research folds over the now-development historical
period. All boundaries are frozen by one-based official-session index.

Each fold has an exact 20-session purge/maturity gap before validation.

| fold | train | gap | validation | validation sessions |
|---|---:|---:|---:|---:|
| V2F1 | 1-504 | 505-524 | 525-624 | 100 |
| V2F2 | 1-624 | 625-644 | 645-744 | 100 |
| V2F3 | 1-744 | 745-764 | 765-864 | 100 |
| V2F4 | 1-864 | 865-884 | 885-984 | 100 |
| V2F5 | 1-984 | 985-1004 | 1005-1104 | 100 |
| V2F6 | 1-1104 | 1105-1124 | 1125-1224 | 100 |

Sessions 1225-1260 are not an independent holdout and are not used to create a
new historical final test. They remain research-history data available for
future descriptive work, but they cannot be used post hoc to rescue candidate
selection from these frozen folds.

No random split is allowed.

## 7. Training rules

For each fold and candidate:

- fit only on resolved primary H10 rows in that fold's training prefix;
- purge gap rows are neither fit nor validation rows;
- score only the frozen validation range;
- model preprocessing is fit from training rows only;
- no probability calibration;
- no validation-driven thresholding;
- no early stopping configured from validation outcomes;
- no hyperparameter tuning;
- no candidate-specific universe changes.

## 8. Metrics

Primary ranking metrics for each fold:

- prevalence/base rate;
- PR-AUC;
- `PR-AUC - prevalence`;
- ROC-AUC;
- within-date Q5 TP rate;
- within-date Q1 TP rate;
- Q5-Q1 spread;
- within-date top-decile TP rate;
- top-decile lift versus fold prevalence.

Accuracy is not a primary metric.

Probability metrics (Brier/ECE/log-loss) are not part of V2 ranking selection
because no V2 probability claim is authorized.

## 9. Candidate eligibility and champion selection

A V2 candidate is **eligible** only if all are true across V2F1-V2F6:

1. all required metrics are finite;
2. median `PR-AUC - prevalence` > 0;
3. `PR-AUC - prevalence` > 0 in at least 4 of 6 folds;
4. median ROC-AUC > 0.50;
5. ROC-AUC > 0.50 in at least 4 of 6 folds;
6. Q5-Q1 > 0 in at least 4 of 6 folds.

If no V2 candidate is eligible, automatic research result is:

`RANKING_V2_NO_CHAMPION`

and no model is force-selected.

If one or more candidates are eligible:

1. choose the candidate with the highest median `PR-AUC - prevalence`;
2. if multiple candidates are within 0.002 absolute median PR-delta of the best,
   choose the one with the highest 25th-percentile fold PR-delta;
3. if still within 0.002 on both criteria, choose the highest median Q5-Q1;
4. if still practically tied, prefer lower complexity in this order:
   `LOGISTIC_XS`, `PAIRWISE_LOGISTIC_XS`, `HGB_XS`, `HGB_XS_MARKET`.

The selected candidate is a **historical-development champion only**. It is not
validated for production/paper/live use.

## 10. Secondary interpretation versus V1 control

`V1_HGB_CONTROL` must be reported on the same folds but cannot become champion.

The comparison is descriptive:

- median PR-delta;
- number of positive PR-delta folds;
- median ROC-AUC;
- number of ROC>0.5 folds;
- median Q5-Q1;
- worst fold PR-delta.

A V2 champion should ideally improve robustness rather than merely maximize one
large fold. However no new outcome-dependent selection rule may be invented
after results are visible.

## 11. Parallel execution contract

After the prepared cache is frozen, candidate runs may execute in parallel.

Recommended orchestration:

- one control task: `V1_HGB_CONTROL` plus cheap base/momentum references;
- worker A: `LOGISTIC_XS`;
- worker B: `HGB_XS`;
- worker C: `HGB_XS_MARKET`;
- worker D: `PAIRWISE_LOGISTIC_XS`.

All workers:

- read the same immutable cache hash;
- use isolated output directories;
- may not modify shared cache/model-spec files;
- emit the same metrics/prediction/manifest schema;
- stop after their assigned candidate completes.

An integrator may combine summaries only after all workers finish. The
integrator may not rerun or tune candidates.

## 12. Stop and safety boundary

Not authorized in this phase:

- Stage-5 rerun;
- use of the consumed Stage-5 period as independent validation;
- feature/model/hyperparameter expansion after V2 runs begin;
- sector-relative historical features without PIT-safe mapping;
- probability calibration claims;
- Kelly sizing;
- execution-PnL claims;
- paper/live trading;
- `IDX-VAL-002`;
- merge to `main`.

After a historical-development champion is selected, it must be frozen before
any fresh-forward independent evaluation. Fresh-forward validation must use data
strictly after `2026-07-31` that was not available for V2 architecture selection.
