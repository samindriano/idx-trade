# Ranking V3-E True-Ranking — Dependency Erratum / Run Reauthorized

Date: 2026-08-10 (Asia/Jakarta)

Status: **PRE-OUTCOME ERRATUM REVIEW PASS — LOCAL F1-F4 RUN REAUTHORIZED**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

## Decision

The earlier `BLOCKED_DEPENDENCY` stop was correct, but the blocked version identity `xgboost==3.2.1` was itself invalid: public XGBoost release history/PyPI contains `3.2.0` and then later releases, with no public `3.2.1` package release.

No V3-E prepared rows, control outcomes, LambdaMART outcomes, V2F5/V2F6 rows, or fresh-forward outcomes were accessed during the blocked attempt. Therefore the dependency identity may be corrected pre-outcome without creating a new research candidate or post-result rescue.

The one controlling dependency correction is frozen in:

`docs/RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_V1.md`

- SHA-256 `bd029458f7a7cd14424af9b748cb7522f1d23b0fe8eaf20ad8f6b44d48894bea`;
- Git blob `327e053c2a1b4270acc4e7de313bba97680eff8b`.

Corrected dependency identity:

**`xgboost==3.2.0`**

## Research semantics unchanged

The V3-E candidate remains exactly the previously frozen ordinal 011:

- `XGBRanker`;
- `objective="rank:ndcg"`;
- exact signal date query/qid;
- exact V2 25 feature order;
- unchanged binary H10 target;
- training-only V2-style median imputer + missing indicators;
- 200 trees, learning rate .05, max depth 5;
- min child 1, lambda 1, alpha/gamma 0;
- full row/column sampling;
- CPU `hist`;
- seed 42, `n_jobs=1`;
- `lambdarank_pair_method="mean"`;
- 8 pairs/sample;
- LambdaRank normalization enabled;
- no early stopping, score normalization, blending, graded gains, tuning, or second ranker.

All original V3 absolute sanity and paired promotion gates remain unchanged.

## Corrected implementation lineage

- `88b1ceb3a9eea30a89fa367a040fc396e90bfda0` — dependency erratum document;
- `d6d727758a5d90c673e0e7c3845cb282a2fc221b` — erratum wrapper around the original frozen runner;
- `98863ce24e99d247be5755f8d568b8abbb07c61f` — project dependency pin corrected to `xgboost==3.2.0`;
- `e6373cdb8827abb2c5d49b68c1f1fcb8e4826d61` — tests switched to the corrected dependency contract.

The original V3-E runner/spec/addendum are retained as historical immutable evidence. The erratum wrapper changes only the dependency identity and records the erratum hash in result provenance.

## Authorization

The local operator may now:

1. sync the latest branch;
2. install/import exact `xgboost==3.2.0`;
3. run full repository pytest;
4. verify original spec/addendum plus dependency-erratum identities and frozen V2 artifacts;
5. run exact V2 control F1-F4;
6. prove exact control equivalence;
7. only after PASS, run the one frozen LambdaMART candidate F1-F4 through `idx_trade.ranking_v3_true_ranking_erratum`;
8. apply unchanged gates, document, push, and stop for ChatGPT review.

If exact `3.2.0` is unavailable or pytest fails for a research-semantic reason, fail closed before outcomes.

## Protected boundary

- V3-D remains parked and unscored;
- V2F5/V2F6 remain sealed;
- reserved post-2026-07-31 fresh-forward outcomes remain untouched;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- no integration/calibration/Stage6/IDX-VAL-002/execution/PnL/Kelly/paper/live/main work is authorized.

Cumulative evaluated V3 candidate count remains `7` until ordinals 010/011 are actually executed/viewed.
