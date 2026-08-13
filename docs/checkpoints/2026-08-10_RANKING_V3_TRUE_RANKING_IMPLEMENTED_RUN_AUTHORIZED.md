# Ranking V3-E True-Ranking — Implemented / Local Run Authorized

Date: 2026-08-10 (Asia/Jakarta)

Status: **SPEC FROZEN + REVIEW PASS + IMPLEMENTED — LOCAL V2F1-V2F4 RUN AUTHORIZED**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

## Frozen hypothesis

V3-E asks only:

> Does one tightly bounded nonlinear same-date learning-to-rank objective outperform the exact frozen binary HGB ranking score on identical V2 causal rows and V2F1-V2F4 discovery folds?

Candidate budget:

- ordinal 010 `V3-E-TRUE-RANKING-V1-CONTROL-010` — exact V2 `HGB_XS_MARKET`;
- ordinal 011 `V3-E-TRUE-RANKING-V1-LAMBDAMART-011` — exact V2 25 features with one XGBoost LambdaMART `rank:ndcg` candidate.

Cumulative evaluated V3 count remains 7 until these candidates are actually run. V3-D ordinals 008/009 remain reserved/unviewed.

## Frozen specification identities

Specification:

`docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`

- SHA-256 `79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55`;
- Git blob `20df2927b6663ea16955919760db9c1429cff3a5`;
- commit `7e9d9440798d4ece254069a570a7c6e8916df127`.

Review addendum:

`docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`

- SHA-256 `6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812`;
- Git blob `01c4dca87ff52fca678c948e4ee23d3e3c82dbcd`;
- commit `04ad6e1b20359d96295273c34279c305b28dcf35`.

## Implementation identity

Dependency pin:

- `xgboost==3.2.1` added to `pyproject.toml`;
- commit `52a267b637eb9277a9f81617e396442d465f1910`.

Runner:

`src/idx_trade/ranking_v3_true_ranking.py`

- implementation commit `b1eff77503e91953fe43fac624153eeefc04c8b7`.

Focused tests:

`tests/test_ranking_v3_true_ranking.py`

- initial test commit `cc1643d61bae0edb34deb6e7d8b583615dfea2f2`;
- deterministic overlap-fixture correction `eb4b7ac8f2b85f8ad580967be657a44f914a428b`.

The implementation physically reads the immutable V2 prepared Parquet with `signal_session_index <= 984` filtering. It does not materialize V2F5/V2F6.

## Frozen LambdaMART model

Exact library: `xgboost==3.2.1`.

Exact relevant settings:

- `XGBRanker`;
- objective `rank:ndcg`;
- query = exact signal date;
- binary H10 target unchanged;
- V2-style training-only median imputer + missing indicators;
- 200 estimators;
- learning rate 0.05;
- max depth 5;
- min child weight 1;
- lambda 1 / alpha 0 / gamma 0;
- row/column subsample 1;
- CPU `hist`;
- seed 42;
- `n_jobs=1`;
- mean LambdaRank pair construction, 8 pairs/sample;
- LambdaRank normalization enabled;
- no early stopping or score postprocessing.

No Structure-Lite, sector, regime, recency, new target, graded relevance, return weighting, calibration or integration is included.

## Mandatory run order

1. synchronize branch and verify clean tree;
2. ensure exact `xgboost==3.2.1`; if unavailable, stop `BLOCKED_DEPENDENCY` rather than substitute;
3. run full repository pytest;
4. verify prepared table/manifest + spec/addendum + exact V2 reference identities;
5. run exact V2 control on F1-F4;
6. prove exact control equivalence;
7. only after equivalence PASS, fit and score LambdaMART on F1-F4;
8. apply unchanged V3 absolute sanity + paired promotion gates;
9. write query/score-diversity/top-decile-overlap diagnostics;
10. update ledger/checkpoint/handoff/current status, commit/push and stop.

## Run decisions

Only two deterministic outcome decisions are allowed:

- `V3_E_TRUE_RANKING_PROMOTE_LAMBDAMART`;
- `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

No post-result rescue variant is authorized.

## Validation status in ChatGPT runtime

The implementation and focused tests were reviewed structurally and syntax-checked before this checkpoint. The ChatGPT runtime available during implementation had XGBoost 3.1.3, not the frozen 3.2.1, so **no claim is made that the full repository or outcome-bearing V3-E run was executed here**.

The local operator must install/verify exact XGBoost 3.2.1 and run the full repository pytest suite before any outcome access.

## Protected boundaries

Do not:

- access V2F5/V2F6;
- access post-2026-07-31 V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- unpark/bypass V3-D sector data gate;
- add a second V3-E ranker/objective/library;
- include V3-B Structure-Lite in standalone V3-E discovery;
- start integration, calibration, Stage 6, IDX-VAL-002, execution/PnL, Kelly, paper/live or main merge.
