# Ranking V3-E True-Ranking Spec Review Addendum V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **INDEPENDENT PRE-OUTCOME REVIEW PASS — CONTROLS IMPLEMENTATION WHERE AMBIGUOUS**

Controlling specification:

`docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`

Spec SHA-256:

`79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55`

## Review verdict

**PASS FOR IMPLEMENTATION, NOT YET FOR OUTCOME INTERPRETATION.**

The specification is narrow enough to answer one question: whether a single nonlinear same-date learning-to-rank formulation adds robust ranking value over exact V2 HGB when target, causal rows, folds and 25 input features are held fixed.

The candidate budget is exactly control ordinal 010 and LambdaMART ordinal 011. No second ranking candidate is authorized.

## Controlling clarifications

Where implementation choices are otherwise ambiguous, this addendum controls.

### 1. Dependency/version is part of the model identity

Use exactly `xgboost==3.2.1`.

If that exact version cannot be installed/run in the local frozen research environment, the V3-E run is **BLOCKED_DEPENDENCY**. Do not silently substitute another XGBoost version, LightGBM, CatBoost, sklearn workaround, or another ranking library.

Installing the exact frozen dependency before outcome access is an engineering/environment action, not another candidate.

### 2. V2-style imputation is mandatory

The LambdaMART candidate does not use XGBoost native missing routing as a new hidden hypothesis.

For each fold:

- select exact 25 V2 feature columns in frozen order;
- fit `SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)` only on training rows;
- transform train and validation;
- no scaler;
- zero row drops.

This is the same missing-value treatment used by the frozen V2 control.

### 3. Query membership is exact signal date

Training rows must be stably sorted by `date,ticker` before `qid` construction.

`qid` must be a zero-based nondecreasing integer code of the exact sorted unique signal dates.

No query may contain multiple dates and one date may not be split.

### 4. Do not label-condition row eligibility

All resolved H10 rows in each frozen training fold remain present.

All-zero and all-one date queries are retained. The implementation may diagnose that they contain no cross-label preference information, but must not drop them, add synthetic rows, or alter labels.

### 5. Validation scoring does not use qid postprocessing

The candidate predicts a raw relevance score for every exact validation row after the training-fitted imputer transform.

Do not normalize scores within dates or across queries. Existing evaluation functions perform the ranking/bucket evaluation.

### 6. Frozen ranker parameters must be asserted in tests

Focused tests must assert every research-significant XGBRanker parameter from the spec, including:

- objective;
- estimator count / learning rate / max depth;
- regularization;
- full subsample/column sample;
- pair method and pair count;
- normalization;
- seed;
- `n_jobs=1`;
- `tree_method="hist"`.

Do not rely on unasserted library defaults for research-significant parameters.

If a necessary XGBoost constructor parameter has a documented default but is not listed in the spec, do not add an experimental value after outcomes. Prefer leaving it at library default and record the full `get_params()` output in runtime artifacts.

### 7. Sealed rows must not be materialized

Hashing the immutable V2 prepared Parquet is allowed.

Reading it into a DataFrame must use a Parquet filter that physically limits `signal_session_index <= 984`. A generic full-table read followed by an in-memory filter is not acceptable.

Reference V2 predictions may likewise materialize only V2F1-V2F4.

### 8. Exact control must execute first

Required order:

1. verify all frozen identities/environment;
2. run exact V2 control F1-F4;
3. prove exact control equivalence;
4. only after PASS, fit/score LambdaMART;
5. compute frozen gates and diagnostics;
6. write result artifacts and stop.

If control equivalence fails, ordinal 011 must not be interpreted.

### 9. No NDCG-based promotion override

Training objective/metric behavior is diagnostic only.

Promotion is determined solely by the frozen V3 absolute sanity and paired promotion gates against exact V2 control. A higher training/evaluation NDCG cannot rescue a failed PR/ROC/Q5-Q1 contract.

### 10. Ranking diagnostics are not a tuning interface

Unique-score fraction, all-tied dates, top-decile overlap, entrants/exits, and query composition must be written for interpretation.

Except for non-finite/global-constant/identity failures explicitly frozen in the spec, these diagnostics do not trigger post-result parameter changes.

## Required focused tests

At minimum:

1. exact candidate IDs/ordinals and 25-feature order;
2. exact XGBoost version guard;
3. exact XGBRanker research parameter contract;
4. training-only imputer and no scaler;
5. query IDs exact by date and nondecreasing;
6. query sorting deterministic by date,ticker;
7. all-zero/all-one query rows preserved;
8. mixed-label query diagnostics correct;
9. validation row identity/order preserved;
10. no row drops after transform;
11. finite/raw score direction contract;
12. global constant score rejected;
13. V2F5/F6 hard blocked;
14. prepared Parquet discovery read capped at session 984;
15. exact prepared/spec/addendum hash/provenance fail closed;
16. control-equivalence PASS/reject behavior;
17. existing V3 absolute/paired gates reused unchanged;
18. score-diversity/top-decile Jaccard diagnostics deterministic;
19. preregistered ledger rows remain `result_viewed=false` before execution;
20. no V3-D/Structure-Lite/Regime feature contamination.

## Authorization boundary

This review authorizes implementation and focused testing only.

The local outcome run may occur only after:

- implementation is committed;
- full repository pytest passes in the local environment with exact XGBoost 3.2.1;
- a run handoff pins the final implementation/spec identities.

V2F5/V2F6 and fresh-forward outcomes remain sealed.
