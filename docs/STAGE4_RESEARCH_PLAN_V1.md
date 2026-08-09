# Stage 4 Research Plan V1 — Attribution, Stability, and Calibration

Status: **FROZEN BEFORE STAGE-4 RUNTIME**
Date: 2026-08-09 (Asia/Jakarta)
Parent evidence: `STAGE3_REVIEW_PASS_FOR_BOUNDED_STAGE4_RESEARCH`
Branch: `research/idx-stage4-v1`

## 1. Purpose

Stage 3 found a modest but repeatable development ranking signal. HistGradientBoosting (HGB) beat the base-rate and momentum baselines on PR-AUC in F1/F2/F3, while logistic beat both in F2/F3. Probability quality did not improve consistently over the base-rate predictor, especially during the F3 prevalence shift.

Stage 4 is therefore **not** a general model-improvement search. It asks three bounded questions:

1. **Attribution:** which frozen feature families materially contribute to the HGB ranking edge?
2. **Stability:** does the ranking edge remain directionally useful across chronological folds and causally classified market regimes?
3. **Calibration:** among a tiny pre-registered calibration family, can HGB probability quality improve enough to justify freezing a probability architecture before the final holdout?

The final locked holdout remains inaccessible throughout Stage 4.

## 2. Immutable upstream contract

Do not change:

- research panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- signal-research manifest SHA-256: `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- Stage-3 primary model table SHA-256: `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189`;
- Stage-3 development feature table SHA-256: `f16d77caa6642d0aba8c0a39eda5b2d32e53f17717b149f5f0637eeacac80772`;
- Stage-3 runtime summary SHA-256: `979c56be43e2fdc5c0502e1b1625d74dbcab6ba28f097338575479739baa029f`;
- exact 1,260-session official calendar;
- H10 primary label;
- ATR14;
- SL=1.0 ATR;
- RR=1.5;
- signal reference=`Close_t`;
- same-bar ambiguity handling;
- primary IDR 1bn broad-liquid universe;
- F1/F2/F3 fold boundaries;
- H20 purge/embargo;
- Stage-3 HGB hyperparameters;
- Stage-3 logistic hyperparameters;
- final locked holdout starting session 1009 / 2025-07-15.

No Stage-4 result may retroactively redefine Stage 3.

## 3. Frozen feature families

The existing compact feature registry is partitioned exactly once as follows.

### MOMENTUM

- `close_return_5`
- `close_return_20`

### VOLATILITY

- `atr14_over_close`

### STRUCTURE

- `close_position_20`
- `distance_high_20_atr`
- `distance_low_20_atr`
- `distance_high_60_atr`
- `distance_low_60_atr`

### VOLUME_LIQUIDITY

- `relative_volume_20`
- `log_regular_value_relative_20`

### HISTORY

- `observed_session_count`
- `security_age_sessions_exact`

No new technical indicator is introduced in Stage 4.

## 4. Frozen HGB ablation family

Use the exact Stage-3 HGB hyperparameters and preprocessing. Fit each variant on the same fold partitions and chronological fit/calibration split.

Variants:

1. `HGB_FULL`
2. `HGB_NO_STRUCTURE`
3. `HGB_NO_MOMENTUM`
4. `HGB_NO_VOLUME_LIQUIDITY`
5. `HGB_NO_VOLATILITY`
6. `HGB_NO_HISTORY`

No combinatorial ablation and no feature-by-feature search.

For attribution, report for each ablation versus `HGB_FULL`:

- PR-AUC delta in F1/F2/F3;
- mean fold PR-AUC delta;
- ROC-AUC delta;
- Brier/ECE diagnostics;
- number of folds in which removal helps/hurts.

Interpretation rule:

- evidence that a family contributes to ranking is **directionally supported** when removing it lowers PR-AUC in at least 2 of 3 folds and lowers mean fold PR-AUC;
- evidence that a family is consistently harmful requires its removal to improve PR-AUC in **all 3 folds** and improve mean fold PR-AUC;
- otherwise the family remains `INCONCLUSIVE` and is not pruned automatically.

Stage 4 does not search for the best subset.

## 5. Cross-sectional ranking diagnostic

PR-AUC alone is not enough for the intended ranking product.

For each validation fold, use `HGB_FULL` raw score and rank securities **within each signal date**. Report score quintiles Q1-Q5 using deterministic rank-percentile assignment.

For each fold and pooled OOF:

- rows per quintile;
- TP_FIRST rate per quintile;
- Q5 minus Q1 TP-rate spread;
- Q5 lift relative to the fold base rate;
- whether Q5 > Q1.

No threshold is optimized from these results.

Directional ranking support requires `Q5 > Q1` in at least 2 of 3 folds. This is a Stage-4 diagnostic gate, not a profitability claim.

## 6. Causal regime diagnostics

Regimes are diagnostic slices only; they are **not added as model features in Stage 4**.

Regime metrics are calculated from the Stage-3 development feature table using all primary-liquid rows on each signal date, not only rows whose future barrier label resolves.

Two date-level metrics:

### TREND REGIME

Daily cross-sectional median of `close_return_20`.

### VOLATILITY REGIME

Daily cross-sectional median of `atr14_over_close`.

For each fold independently:

1. derive 33.333% and 66.667% thresholds using **training dates only**;
2. freeze those thresholds for that fold;
3. classify validation dates as LOW / MID / HIGH;
4. merge the date regime onto resolved validation rows.

For `HGB_FULL`, report by fold and regime:

- rows;
- positive rate;
- PR-AUC;
- ROC-AUC;
- Brier;
- ECE;
- mean probability.

A regime slice with fewer than 1,000 resolved rows is reported but flagged `LOW_SAMPLE_DIAGNOSTIC` and cannot drive a stage decision.

Do not select features/models based on one favorable regime.

## 7. Frozen calibration family

Calibration research applies to `HGB_FULL` only. Ranking model hyperparameters remain unchanged.

Use the existing chronological model-fit / H20 maturity-gap / calibration-tail split in every fold.

Candidates:

1. `NATIVE`
   - HGB native `predict_proba` probability;
   - no post-hoc calibration.

2. `PLATT`
   - existing Stage-3 logistic calibration on HGB raw score;
   - this is the Stage-3 reference calibrator.

3. `ISOTONIC`
   - monotonic isotonic regression on HGB raw score;
   - fit only on the chronological calibration tail;
   - `out_of_bounds='clip'`;
   - no parameter search.

Do not add beta calibration, temperature scaling, recency weighting, dynamic priors, or calibration ensembles in Stage 4 V1.

## 8. Calibration metrics and selection

For every candidate and fold report:

- PR-AUC;
- ROC-AUC;
- Brier score;
- ECE using calibration-derived bins;
- log loss;
- observed positive rate;
- mean predicted probability;
- absolute prevalence gap = `abs(mean_probability - positive_rate)`.

Also report pooled OOF metrics.

Calibrator selection is frozen as:

1. choose the candidate with lowest **pooled OOF Brier**;
2. if pooled Brier is exactly tied at reported precision, choose lower pooled ECE;
3. if still tied, prefer the simpler order `NATIVE -> PLATT -> ISOTONIC`.

This selection is development-only and is made once.

### Calibration readiness gate

A selected HGB probability architecture is `CALIBRATION_READY_FOR_HOLDOUT_FREEZE` only if all are true:

- pooled OOF Brier is lower than the pooled base-rate Brier from the same Stage-4 folds;
- pooled OOF ECE is lower than the pooled base-rate ECE from the same Stage-4 folds;
- absolute prevalence gap is lower than base-rate in at least 2 of 3 folds;
- no fold has non-finite probability metrics;
- no holdout data is accessed.

If this gate fails, ranking research may still pass, but calibrated `P(TP before SL)` remains blocked and the holdout stays closed.

## 9. Reference baselines

Retain exactly:

- `base_rate`;
- `momentum_20`;
- `logistic_compact`;
- `HGB_FULL`.

Stage-4 ablations are diagnostic challengers, not a general model zoo.

## 10. Stage-4 decision states

### `STAGE4_RANKING_AND_CALIBRATION_FREEZE_READY`

Requires:

- HGB ranking still satisfies the Stage-3 advancement rule;
- Q5 > Q1 in at least 2 of 3 validation folds;
- no admission/causality/holdout violation;
- one pre-registered HGB calibrator passes the calibration readiness gate.

This status allows a **separate Stage-5 holdout-freeze review**, but does not itself authorize reading the holdout.

### `STAGE4_RANKING_GO_CALIBRATION_BLOCKED`

Use when:

- ranking diagnostics remain directionally positive;
- but no calibration candidate passes the readiness gate.

Do not inspect the holdout. A separate Stage-4B calibration hypothesis would be required.

### `STAGE4_RANKING_REVIEW_REQUIRED`

Use when:

- Stage-3 ranking improvement fails to reproduce;
- cross-sectional Q5/Q1 ordering fails in at least 2 folds;
- or regime/ablation diagnostics expose a material contradiction needing review.

Do not rescue by tuning in the same run.

### `STAGE4_RUNTIME_BLOCKED`

Use for artifact-hash mismatch, fold violation, unexpected schema, holdout access, or non-finite metrics.

## 11. Explicitly prohibited Stage-4 actions

- inspect any session >=1009;
- use locked-holdout outcomes to choose a calibrator or feature family;
- change H/RR/ATR/barrier semantics;
- change universe/liquidity threshold;
- add technical indicators;
- tune HGB/logistic hyperparameters;
- AutoML/model zoo;
- external data;
- news/fundamental features;
- execution-PnL claims;
- synthetic Open;
- Kelly, sizing, or portfolio simulation;
- Stage 5 in the same task;
- merge to `main`.

## 12. Required implementation/runtime artifacts

Code implementation should produce deterministic artifacts for:

- fold/model/ablation metrics;
- calibration-candidate metrics;
- selected calibrator decision;
- cross-sectional quintile diagnostics;
- causal regime thresholds and regime metrics;
- feature-family attribution table;
- Stage-4 summary JSON with input hashes, code commit, spec hash, dependency versions, and `holdout_outcome_accessed=false`.

Runtime artifacts stay outside Git.

## 13. Why the holdout remains closed

Stage 3 established ranking evidence but not reliable probability calibration. Opening the final 252-session holdout now would spend the project's only clean final evaluation before the probability architecture is frozen. Stage 4 therefore uses development data only to freeze attribution, robustness, and calibration choices first.
