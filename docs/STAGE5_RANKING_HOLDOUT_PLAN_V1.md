# Stage 5 V1 — Locked Ranking Holdout Plan

Date: 2026-08-09 (Asia/Jakarta)
Status: **FROZEN — IMPLEMENTATION REVIEW PASS / RUNTIME READY**

## 1. Decision entering Stage 5

Stage 3 and Stage 4 established positive but modest ranking evidence for the
frozen full HistGradientBoosting model. Stage 4 and Stage 4B did **not** establish
probability readiness:

- Stage 4 automatic status: `STAGE4_RANKING_GO_CALIBRATION_BLOCKED`;
- Stage 4B automatic status: `STAGE4B_CALIBRATION_STILL_BLOCKED`;
- no calibration candidate beat the frozen probability-quality gate;
- locked holdout outcomes remain untouched.

The V1 research specification makes PR-AUC the primary metric and probability
quality a separate secondary dimension. Therefore the next scientifically
bounded question is whether the already-frozen HGB **ranking signal** survives
one untouched temporal holdout.

This is not permission to continue calibration search. Probability V1 is
frozen as:

`PROBABILITY_V1_NOT_READY_DEFERRED`

No Stage-5 result may be called a calibrated `P(TP before SL)`.

## 2. Holdout-consumption rule

The locked holdout is consumed **once** for `RANKING_V1_ONLY`.

The runner writes a durable marker named
`STAGE5_RANKING_V1_HOLDOUT_ACCESS_STARTED.json` beside the immutable research
panel **after all rankers have been serialized and hashed, but before any full
panel / holdout outcome read**. A mirror marker is written to the Stage-5 output
directory.

If the durable marker already exists, every later Stage-5 invocation must fail
closed even if a different output directory is supplied. If a process fails
after the marker is written, the holdout is conservatively treated as consumed
and must not be rerun without an explicit independent review.

After Stage 5 begins holdout access:

- sessions 1009–1260 are no longer a reusable model-development holdout;
- Stage-5 outcomes may not be used to tune labels, features, model parameters,
  universe thresholds, calibration, score mappings, or probability architecture;
- any future Probability V2 must receive a **fresh forward evaluation period
  strictly after 2026-07-31**. It may not claim independent validation by
  reusing this consumed holdout.

## 3. Immutable upstream research contract

Unchanged:

- immutable `SIGNAL_RESEARCH_HLCV` panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- research manifest SHA-256:
  `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- official calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- official calendar: 1,260 sessions, `2021-04-29 -> 2026-07-31`;
- primary label: H10, ATR14, SL=1.0 ATR, RR=1.5;
- primary universe: broad causal liquid view, trailing 60 official sessions,
  at least 20 observed ACTIVE rows, median Regular-Market Value >= IDR 1bn;
- primary feature registry: exact frozen Stage-3 compact features;
- HGB hyperparameters: unchanged from Stage 3;
- random seed: 42;
- Open remains optional and is never synthesized.

Stage-4B summary SHA-256 required for admission:

`f9cbce089c21debd6420943ebf5cd647fc41942e4f210964ddbb5d165d10ebb7`

It must state:

- `STAGE4B_CALIBRATION_STILL_BLOCKED`;
- `holdout_outcome_accessed=false`.

## 4. Final development refit boundary

Locked holdout starts at official session 1009 (`2025-07-15`).

The frozen validation contract uses maximum horizon H20 for purge/embargo.
Therefore the latest training **signal** allowed in the final refit is:

`1009 - 20 - 1 = 988`

So:

- final ranking-model training signals: sessions 1–988;
- purge/buffer before holdout: sessions 989–1008;
- no training target may use a future interval intersecting the holdout.

The primary model still trains on resolved H10 `TP_FIRST` / `SL_FIRST` rows.
The H20 boundary is a leakage guard, not a change of target.

## 5. Model freeze before outcome access

The Stage-5 runner must perform this order:

1. verify immutable input hashes and Stage-4B parent status;
2. verify the durable global holdout marker does not already exist;
3. build causal development features;
4. build **development-only** H10 labels with signal index <=988 and future
   access bounded to development sessions;
5. create the final primary model table;
6. fit and serialize all frozen rankers;
7. hash the serialized model artifacts and write a pre-holdout freeze record;
8. write the global/local one-shot holdout-access markers;
9. only then generate/read holdout outcome labels.

The runner must record:

`models_frozen_before_holdout_labels=true`

Any implementation that reads holdout targets before final model serialization
is invalid.

## 6. Frozen final rankers

All are fit only on the final development model table through session 988.

### A. BASE_RATE

Constant training prevalence. It is a comparator; its holdout PR-AUC equals
holdout positive prevalence.

### B. MOMENTUM_20

One-dimensional ranking baseline using `close_return_20` with training-only
median imputation and a single logistic rank mapping fit on final development
rows. It may learn the sign from development data. No probability claim is
made.

### C. LOGISTIC_COMPACT

Exact frozen Stage-3 compact logistic pipeline, refit once on final development
rows. Raw decision score only.

### D. HGB_FULL

Exact frozen Stage-3 HistGradientBoosting pipeline with the full frozen feature
registry, refit once on final development rows. Raw decision score only.

No ablated subset, calibrator, new feature, model family, or hyperparameter may
be selected.

## 7. Holdout label windows

### Primary H10

Holdout signal range:

- sessions 1009–1250 inclusive;
- 242 official signal sessions;
- each has a complete possible H10 future window inside the immutable panel.

Sessions 1251–1260 remain explicit H10 horizon-end buffer and are not silently
removed.

### Sensitivity H5

- signals 1009–1255;
- sensitivity only.

### Sensitivity H20

- signals 1009–1240;
- sensitivity only.

H5/H20 may not rescue a failed H10 result.

## 8. Primary ranking metrics

On resolved primary-liquid H10 holdout rows report:

- PR-AUC;
- ROC-AUC;
- positive prevalence;
- row/date/ticker coverage;
- HGB versus BASE_RATE PR-AUC delta;
- HGB versus MOMENTUM_20 PR-AUC delta;
- LOGISTIC_COMPACT as a fixed descriptive comparator.

No Brier, ECE, log-loss, Kelly, Opportunity Score, or calibrated-probability
claim is part of the Stage-5 gate.

## 9. Cross-sectional ranking diagnostics

Using HGB raw score only, assign within-date deterministic buckets.

Report:

- Q1–Q5 TP rates and row counts;
- Q5 - Q1 spread;
- Q5 lift versus overall holdout prevalence;
- top-decile TP rate and lift versus overall prevalence.

No threshold is optimized from holdout outcomes.

## 10. Predeclared temporal stability diagnostic

The 242 evaluable H10 signal sessions are split mechanically into two equal
121-session blocks:

- HOLDOUT_A: sessions 1009–1129;
- HOLDOUT_B: sessions 1130–1250.

For each block report HGB:

- rows;
- prevalence;
- PR-AUC;
- ROC-AUC;
- PR-AUC delta versus base prevalence;
- Q5 - Q1 spread.

These boundaries are fixed before outcome inspection.

## 11. Primary decision gate

All safety/admission guards must pass first.

### `STAGE5_RANKING_HOLDOUT_PASS`

Require all:

1. HGB overall H10 PR-AUC > BASE_RATE PR-AUC;
2. HGB overall H10 PR-AUC > MOMENTUM_20 PR-AUC;
3. HGB overall H10 ROC-AUC > 0.50;
4. HGB overall Q5 TP rate > Q1 TP rate;
5. HGB H10 PR-AUC > base prevalence in HOLDOUT_A;
6. HGB H10 PR-AUC > base prevalence in HOLDOUT_B;
7. all metrics finite;
8. models were frozen before holdout labels;
9. no data/hash/causality guard failed.

### `STAGE5_RANKING_HOLDOUT_MIXED`

Use when overall conditions 1–4 pass but one or both temporal-half conditions
5–6 fail.

### `STAGE5_RANKING_HOLDOUT_FAIL`

Use when any overall condition 1–4 fails while safety guards remain clean.

### `STAGE5_RUNTIME_BLOCKED`

Use for hash, manifest, environment, schema, causality, model-freeze-order,
one-shot marker, or other admission failure.

No Stage-5 status automatically authorizes paper/live trading.

## 12. Sensitivity reports

Using the **same frozen HGB score** without retraining:

- H5 resolved outcome PR-AUC / ROC-AUC / prevalence;
- H20 resolved outcome PR-AUC / ROC-AUC / prevalence;
- full H5/H10/H20 outcome-status distributions.

Sensitivity results are descriptive only and cannot replace H10.

## 13. Probability semantics after Stage 5

Probability V1 remains disabled regardless of ranking PASS/MIXED/FAIL:

`PROBABILITY_V1_NOT_READY_DEFERRED`

If ranking passes, future probability work must be a separately versioned V2
architecture and must use fresh forward validation after 2026-07-31.

If ranking fails, calibration work should not continue as a rescue exercise.

## 14. Reporting and immutability

Runtime outputs stay outside Git and must be hashed.

The Stage-5 report must record:

- exact source code HEAD;
- immutable panel/manifest/calendar hashes;
- Stage-4B summary hash/status;
- dependency versions;
- final development training boundary and rows;
- model artifact hashes frozen before outcome access;
- global and local holdout-access marker paths/hashes;
- H10 outcome distribution;
- all ranking metrics;
- quintile/decile diagnostics;
- two temporal-half diagnostics;
- H5/H20 sensitivity metrics;
- final decision;
- `holdout_consumed=true`;
- `holdout_consumed_for=RANKING_V1_ONLY`;
- `probability_v1_status=PROBABILITY_V1_NOT_READY_DEFERRED`.

No runtime prediction/model/parquet/CSV artifact is committed to Git.

## 15. Implementation review result

Stage-5 implementation and regression suite are green before holdout access:

- GitHub CI: **206 passed, 0 failed**;
- warning flood introduced by the initial Stage-5 test fixture was removed;
- remaining warnings are existing pandas/NumPy deprecation/future warnings;
- the runner refuses numerical-environment drift;
- the runner refuses input hash or manifest drift;
- the final model refit is serialized and hashed before holdout labels;
- a durable global one-shot marker prevents accidental reruns into a new output
  directory after holdout access begins.

Runtime is authorized only as the exact one-shot execution described here.
