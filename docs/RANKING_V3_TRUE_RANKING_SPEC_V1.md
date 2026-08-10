# Ranking V3-E True-Ranking Specification V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **FROZEN PRE-OUTCOME SPECIFICATION — NOT AUTHORIZATION TO SCORE**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

Hypothesis ID: `V3-E-TRUE-RANKING-V1`

## Research question

> Does one tightly bounded nonlinear same-date learning-to-rank objective outperform the exact frozen binary HGB ranking score on identical causal V2 rows and V2F1-V2F4 discovery folds?

This experiment changes only the ranking model/objective formulation. It does not add a new feature family, target, universe rule, recency weighting, sector information, regime routing, calibration, execution logic, or Structure-Lite.

## Candidate budget

Exactly two permanent ledger slots are reserved:

- ordinal `010`: `V3-E-TRUE-RANKING-V1-CONTROL-010` — exact frozen V2 `HGB_XS_MARKET` control;
- ordinal `011`: `V3-E-TRUE-RANKING-V1-LAMBDAMART-011` — one frozen nonlinear same-date LambdaMART candidate.

V3-D ordinals 008/009 remain reserved and unviewed. Cumulative evaluated V3 candidate count remains `7` until V3-E is actually run.

No second V3-E ranker/objective/library may be added after outcomes are viewed.

## Frozen data / target / folds

Use the immutable Ranking-V2 prepared model table:

- SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`.

Use only resolved primary-liquid H10 rows and the existing `binary_target`:

- `1` = TP first;
- `0` = SL first.

No label transformation, graded relevance, return weighting, gain engineering, sample weighting, or target smoothing is allowed.

Discovery folds are exactly V2F1-V2F4:

- F1 train 1..504, purge 505..524, validation 525..624;
- F2 train 1..624, purge 625..644, validation 645..744;
- F3 train 1..744, purge 745..764, validation 765..864;
- F4 train 1..864, purge 865..884, validation 885..984.

V2F5/V2F6 are sealed and must not be materialized, scored, or summarized.

## Exact feature contract

Use exactly the frozen 25 `HGB_XS_MARKET` features, in exact existing order. No Structure-Lite, sector, regime, recency, alternative-data, fundamental, broker-flow, macro, or new technical features.

The exact V2 control is trained and scored using the existing V2 pipeline.

The true-ranker uses the same 25 input columns and the same fold-local numeric preprocessing semantics:

- `SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)`;
- fit the imputer on training rows only;
- no scaler;
- transform training and validation separately;
- no row may be dropped because of missing features.

This preserves V2 missing-data treatment while changing the estimator/objective.

## Frozen true-ranking estimator

Library/version contract:

- `xgboost==3.2.1`;
- estimator `xgboost.XGBRanker`;
- CPU deterministic/reference execution only for this experiment.

Objective:

- `objective="rank:ndcg"`;
- query/group = exact signal `date`;
- labels remain binary 0/1 relevance;
- no custom label gains;
- `ndcg_exp_gain=True`;
- `lambdarank_pair_method="mean"`;
- `lambdarank_num_pair_per_sample=8`;
- `lambdarank_normalization=True`.

Frozen tree/fit parameters:

- `n_estimators=200`;
- `learning_rate=0.05`;
- `max_depth=5`;
- `min_child_weight=1.0`;
- `reg_lambda=1.0`;
- `reg_alpha=0.0`;
- `gamma=0.0`;
- `subsample=1.0`;
- `colsample_bytree=1.0`;
- `tree_method="hist"`;
- `random_state=42`;
- `n_jobs=1`;
- `verbosity=0`.

No early stopping, hyperparameter search, GPU-specific algorithm, dart booster, subsampling experiment, alternate pair construction, alternate ranking objective, or objective rescue is allowed.

Rationale for the bounded parameterization:

- 200 boosting rounds and learning rate 0.05 mirror the scale of the frozen HGB control;
- max depth 5 is a bounded tree complexity close to the V2 control's 31-leaf cap;
- full row/column sampling avoids introducing a second stochastic hypothesis;
- one fixed mean-pair LambdaMART configuration tests nonlinear same-date ranking without a ranking-model tournament.

## Query semantics

For every training fold:

1. sort training rows deterministically by `date`, then `ticker`;
2. assign one integer `qid` per unique signal date in ascending date order;
3. all securities on the same signal date belong to the same query;
4. do not combine adjacent dates into a query;
5. do not split one date across queries.

All training rows remain present, including dates whose resolved H10 labels are all-zero or all-one. Such dates are retained for row-preservation/accounting; no artificial opposite-class row or label is created.

Mandatory query diagnostics per fold:

- total train query/date count;
- mixed-label query count;
- all-zero query count;
- all-one query count;
- min/median/q25/max query row count;
- exact train row count before/after preprocessing;
- zero rows dropped.

A fold is invalid if query grouping changes row identity/order unexpectedly, `qid` is not nondecreasing at fit time, or the training set does not contain both target classes overall.

## Validation / scoring semantics

Validation rows are exactly the existing V2 fold rows in their deterministic V2 order.

Prediction:

- transform the validation 25 features using the training-fitted V2-style imputer;
- `XGBRanker.predict(...)`;
- output is the raw ranking/relevance score;
- larger score = higher rank;
- the score must be finite for every validation row;
- the score is **not** calibrated probability and must never be labeled P(TP before SL).

No query-specific postprocessing, score normalization, date z-score, isotonic transform, blending, or calibration is allowed.

## Mandatory exact control equivalence

Before the LambdaMART result may be interpreted, ordinal 010 must reproduce the immutable V2 HGB reference on F1-F4:

- exact row count;
- exact row identity/order;
- score tolerance `atol=1e-12`, `rtol=0`;
- exact prevalence, PR-AUC, PR-AUC delta, ROC-AUC, Q1/Q5 rates, Q5-Q1, top-decile rate/lift within `1e-12`.

If control equivalence fails, stop before interpreting ordinal 011.

Historical frozen V2 reference artifacts:

- summary SHA-256 `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- predictions SHA-256 `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`.

## Promotion gates

Use the existing V3 absolute sanity gate unchanged.

Candidate absolute sanity requires:

- all required metrics finite;
- median PR-AUC minus prevalence > 0;
- positive PR delta in at least 3/4 folds;
- median ROC-AUC > 0.50;
- ROC-AUC > 0.50 in at least 3/4 folds;
- median Q5-Q1 > 0;
- positive Q5-Q1 in at least 3/4 folds.

Use the existing V3 paired promotion gate unchanged against exact V2 control:

- median paired PR-delta improvement >= `+0.001`;
- q25 paired PR improvement >= `0`;
- worst paired PR improvement >= `0`;
- candidate PR delta not below control in at least 3/4 folds;
- median ROC change >= `-0.005`;
- median Q5-Q1 change >= `-0.005`;
- candidate Q5-Q1 not below control in at least 3/4 folds.

No NDCG training metric can override these gates.

Deterministic final decisions:

- `V3_E_TRUE_RANKING_PROMOTE_LAMBDAMART` if absolute and paired gates both pass;
- otherwise `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

There is no post-result rescue variant.

## Mandatory ranking diagnostics

In addition to the existing V3 metrics, report per fold:

- train query/date count and class-composition counts;
- validation date count;
- validation row count;
- per-date unique-score fraction: median, q25, minimum;
- per-date all-tied score-date count;
- global unique score count;
- top-decile Jaccard overlap between control and LambdaMART using `(date,ticker)` identity;
- top-decile entrants/exits count;
- paired top-decile lift change;
- F4 metrics explicitly.

Score-diversity diagnostics are diagnostic only except:
- any non-finite score fails closed;
- globally constant candidate scores fail closed;
- row/query identity mismatch fails closed.

## Runtime / provenance

Before any run:

- read `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
- verify exact prepared table/manifest hashes;
- verify frozen spec/review identities;
- verify exact `xgboost` version `3.2.1`;
- verify exact V2 reference artifact hashes;
- run the full repository pytest suite.

Use sequential reference execution first. Do not introduce multiprocessing/parallel candidate scheduling. `n_jobs=1` is frozen for the ranker.

Persist:

- exact code commit;
- Python/NumPy/pandas/scikit-learn/XGBoost versions;
- candidate feature-order hash;
- query diagnostics;
- fold metrics;
- predictions;
- paired metrics;
- control-equivalence artifact;
- model artifacts/hashes;
- runtime;
- verdict;
- executed ledger rows;
- summary and artifact SHA inventory.

## Data-access boundary

The V3-E runner must physically materialize only rows needed through signal session 984 from the immutable V2 prepared Parquet.

Do not load/score/summarize:

- V2F5/V2F6;
- reserved post-2026-07-31 V2 fresh-forward outcomes.

Do not write `FORWARD_OUTCOME_ACCESS_STARTED`.

## Hard prohibitions

Do not:

- add Structure-Lite to V3-E discovery;
- use sector features or try to bypass the blocked V3-D data gate;
- use V3-C regime as router/feature;
- use recency weighting;
- change H10 target;
- add graded relevance or realized-return gains;
- run `rank:map`, `rank:pairwise`, another LambdaMART pair policy, LightGBM, CatBoost, neural ranker, or any second ranking candidate after viewing results;
- tune XGBoost parameters from F1-F4 outcomes;
- access V2F5/F6;
- access V2 fresh-forward outcomes;
- start V3 integration automatically;
- start calibration, Stage 6, IDX-VAL-002, execution/PnL, Kelly, paper/live, or merge main.

## Interpretation boundary

This is historical-development evidence only. Even a V3-E promotion does not establish independent validation and does not authorize production/live use.

After V3-E is reviewed, the Tier-1 ladder is complete except for parked V3-D. Any integration step must be separately preregistered and may combine only independently surviving Tier-1 components.
