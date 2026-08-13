# Ranking V3-E True-Ranking Dependency Erratum V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **PRE-OUTCOME DEPENDENCY IDENTITY CORRECTION — RESEARCH SEMANTICS UNCHANGED**

Controlling base specification:

`docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`

Controlling review addendum:

`docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`

Blocked dependency checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_BLOCKED_DEPENDENCY.md`

## Reason for erratum

The original V3-E specification pinned `xgboost==3.2.1`. The first local run correctly stopped before any prepared-row materialization, control execution, LambdaMART execution, or outcome inspection because that exact public package release does not exist.

Official package/release evidence checked after the fail-closed stop shows:

- public PyPI has XGBoost `3.2.0` and then `3.3.0`, with no `3.2.1` release;
- XGBoost's official release history contains `v3.2.0` but no `v3.2.1`;
- PyPI provides a Windows x86-64 wheel for `xgboost==3.2.0`.

Therefore `3.2.1` was an invalid dependency identity, not a research result and not evidence against V3-E.

## Corrected dependency identity

Replace only the dependency/version contract:

- old invalid identity: `xgboost==3.2.1`;
- corrected frozen identity: **`xgboost==3.2.0`**.

The corrected version is now part of the permanent V3-E model/runtime identity.

If exact `xgboost==3.2.0` cannot be installed and imported, fail closed with `BLOCKED_DEPENDENCY`. Do not substitute `3.1.3`, `3.3.0`, a dev build, private patched build, LightGBM, CatBoost, or another ranker.

## Research semantics explicitly unchanged

This erratum changes **nothing else**.

The candidate remains:

- `xgboost.XGBRanker`;
- `objective="rank:ndcg"`;
- exact signal date as query/qid;
- exact frozen V2 25 features;
- unchanged binary H10 target;
- training-only `SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)`;
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
- `verbosity=0`;
- `ndcg_exp_gain=True`;
- `lambdarank_pair_method="mean"`;
- `lambdarank_num_pair_per_sample=8`;
- `lambdarank_normalization=True`;
- no early stopping, score normalization, blending, tuning, or second ranker.

Official XGBoost 3.2.0 documentation supports `XGBRanker`, `rank:ndcg`, qid grouping, `mean` pair construction, `lambdarank_num_pair_per_sample`, and `lambdarank_normalization`. No parameter was introduced or removed by this erratum.

## Outcome-access integrity

At the time this erratum is frozen:

- V3-E prepared rows were not materialized for the blocked attempt;
- exact V2 control ordinal 010 was not executed;
- LambdaMART ordinal 011 was not executed;
- no V3-E outcome metric was viewed;
- ordinals 010/011 remain `result_viewed=false`;
- cumulative evaluated V3 count remains `7`;
- V2F5/V2F6 remain sealed;
- reserved post-2026-07-31 fresh-forward outcomes remain untouched;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten.

This correction is therefore a legitimate pre-outcome engineering/specification erratum, not post-result tuning or candidate rescue.

## Implementation requirement

The V3-E runner and tests must pin and verify all three controlling document identities:

1. original spec;
2. original review addendum;
3. this dependency erratum.

The full repository pytest suite must pass under exact `xgboost==3.2.0` before any V3-E outcome access.

After that gate passes, the existing V3-E run order remains:

1. verify frozen artifacts/contracts;
2. physically materialize only rows through session 984;
3. run exact V2 control;
4. prove exact control equivalence;
5. only then run frozen LambdaMART;
6. apply unchanged absolute + paired promotion gates;
7. document and stop.

No V3-D, V2F5/V2F6, fresh-forward, integration, calibration, Stage 6, execution, or live work is authorized by this erratum.
