# Handoff — IDX Ranking V3-E True-Ranking Local Run After Dependency Erratum

Date: 2026-08-10 (Asia/Jakarta)

Status: **RUN-ONLY AUTHORIZED — USE DEPENDENCY ERRATUM / NO REDESIGN**

## Context

The first V3-E local attempt stopped fail-closed before outcome access because the original spec pinned nonexistent public package version `xgboost==3.2.1`.

A pre-outcome dependency erratum has now corrected only that runtime identity to exact public `xgboost==3.2.0`. No candidate/model/feature/target/fold/gate semantics changed.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`
3. `docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`
4. `docs/RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_V1.md`
5. `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_BLOCKED_DEPENDENCY.md`
6. `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_RUN_REAUTHORIZED.md`
7. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
8. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
9. `src/idx_trade/ranking_v3_true_ranking.py`
10. `src/idx_trade/ranking_v3_true_ranking_erratum.py`
11. `tests/test_ranking_v3_true_ranking.py`

## Corrected frozen dependency

Required exact version:

`xgboost==3.2.0`

Do not substitute `3.1.3`, `3.3.0`, a dev build, private patched wheel, LightGBM, CatBoost, or another ranker.

The dependency erratum identity is:

- SHA-256 `bd029458f7a7cd14424af9b748cb7522f1d23b0fe8eaf20ad8f6b44d48894bea`;
- Git blob `327e053c2a1b4270acc4e7de313bba97680eff8b`.

## Frozen candidate

Ordinal 010: exact V2 `HGB_XS_MARKET` control.

Ordinal 011: exact V2 25 features + one XGBoost LambdaMART candidate:

- `XGBRanker`;
- `objective="rank:ndcg"`;
- exact signal date = query/qid;
- binary H10 target unchanged;
- V2-style training-only median imputer + missing indicators;
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
- `lambdarank_normalization=True`.

No second candidate or parameter change is authorized.

## Phase 1 — environment and full pytest

From the explicit IDX Trade repo root:

1. verify branch `research/idx-ranking-v2-spec-v1`, clean tree, synchronized remote;
2. install/verify exact `xgboost==3.2.0`;
3. run full repository pytest using the repo's `pyproject.toml` and `tests` path;
4. record passed/failed/warnings/duration.

If pytest fails, stop before prepared/reference artifact reads unless the failure is an unambiguous engineering-only issue that can be fixed without changing research semantics. Any such fix must be committed and full pytest rerun before outcome access.

## Phase 2 — verify immutable contracts

Verify exact:

- V2 prepared table SHA `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- V2 prepared manifest SHA `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- frozen V2 HGB summary SHA `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- frozen V2 HGB predictions SHA `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`;
- original V3-E spec SHA `79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55` and Git blob `20df2927b6663ea16955919760db9c1429cff3a5`;
- original review addendum SHA `6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812` and Git blob `01c4dca87ff52fca678c948e4ee23d3e3c82dbcd`;
- dependency erratum SHA/blob above.

Fail closed on any mismatch.

## Phase 3 — run V3-E through erratum wrapper

Use:

`python -m idx_trade.ranking_v3_true_ranking_erratum ...`

Required arguments include:

- `--prepared-table`
- `--prepared-manifest`
- `--reference-v2-dir`
- `--spec docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`
- `--addendum docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`
- `--erratum docs/RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_V1.md`
- `--output-dir` pointing to a new empty directory
- `--code-commit` set to the final research implementation commit actually used

Mandatory execution order is enforced and must remain:

1. physically materialize only prepared rows through signal session 984;
2. run exact V2 control ordinal 010;
3. prove exact control equivalence on F1-F4;
4. if equivalence fails, stop and do not interpret ordinal 011;
5. only after PASS, fit/score frozen LambdaMART ordinal 011;
6. compute unchanged absolute + paired V3 gates;
7. write query composition, score diversity, top-decile overlap/Jaccard and F4 diagnostics;
8. document result and stop.

## Allowed final decisions

Only:

- `V3_E_TRUE_RANKING_PROMOTE_LAMBDAMART`; or
- `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

No rescue, second objective, alternate pair method, alternate XGBoost version, or second library.

## Required return report

Return:

- branch + final HEAD;
- full pytest result;
- exact XGBoost version;
- prepared discovery rows/tickers/session range;
- control equivalence row count + max score/metric diffs;
- Control vs LambdaMART F1-F4 PR-AUC, PR-delta, ROC, Q5-Q1, top-decile lift;
- paired PR improvement each fold + median/q25/worst/nonnegative-fold count;
- median ROC change;
- median Q5-Q1 change + nonnegative-fold count;
- median top-decile lift change;
- absolute gate result;
- paired gate result;
- final verdict;
- query/date diagnostics;
- score-diversity diagnostics;
- top-decile Jaccard/entrants/exits;
- F4 behavior;
- runtime + major artifact hashes including dependency-erratum identity artifact;
- cumulative evaluated count;
- confirmation V3-D remained blocked/unscored, V2F5/V2F6 were not materialized, fresh-forward outcomes were untouched, and `FORWARD_OUTCOME_ACCESS_STARTED` was not written.

After outcome access, update ledger/checkpoint/result handoff/CURRENT_STATUS, commit and push, verify clean/synced, and STOP for ChatGPT review. Do not start integration automatically.
