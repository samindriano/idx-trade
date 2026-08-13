# Handoff — IDX Ranking V3-E True-Ranking Local Run

Date: 2026-08-10 (Asia/Jakarta)

Status: **RUN-ONLY AUTHORIZATION — EXACT FROZEN V3-E ON V2F1-V2F4**

## Objective

Execute the already-frozen and already-implemented V3-E True-Ranking experiment. Do not redesign it.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`
3. `docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`
4. `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_IMPLEMENTED_RUN_AUTHORIZED.md`
5. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
6. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
7. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
8. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
9. `src/idx_trade/ranking_v3_true_ranking.py`
10. `tests/test_ranking_v3_true_ranking.py`

## Frozen candidate identities

- ordinal 010: `V3-E-TRUE-RANKING-V1-CONTROL-010`;
- ordinal 011: `V3-E-TRUE-RANKING-V1-LAMBDAMART-011`.

Cumulative evaluated candidate count is 7 before this run. V3-D ordinals 008/009 remain unviewed/reserved and are not reused.

## Frozen artifact identities

Prepared V2 table:

`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`

Prepared manifest:

`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`

V2 HGB reference summary:

`24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`

V2 HGB reference predictions:

`5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`

V3-E spec:

- SHA-256 `79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55`;
- Git blob `20df2927b6663ea16955919760db9c1429cff3a5`.

V3-E review addendum:

- SHA-256 `6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812`;
- Git blob `01c4dca87ff52fca678c948e4ee23d3e3c82dbcd`.

Implementation identity:

- dependency pin commit `52a267b637eb9277a9f81617e396442d465f1910`;
- runner commit `b1eff77503e91953fe43fac624153eeefc04c8b7`;
- focused test final commit `eb4b7ac8f2b85f8ad580967be657a44f914a428b`.

## Phase 1 — sync / environment / full pytest

Pull/fetch the latest `research/idx-ranking-v2-spec-v1` and verify clean synchronized tree.

Verify Python environment. The frozen candidate requires exactly:

`xgboost==3.2.1`

If import is missing or version differs, install only the exact frozen dependency before outcome access. Do not substitute another version/library.

Then run the full IDX Trade test suite explicitly from the repo root using the repository `pyproject.toml` and `tests` path. Report exact passed/failed/warnings/time.

If any test fails, stop before outcome access. Fix only engineering defects that do not alter candidate/model/query/gate semantics, rerun full pytest, and document the correction. Any research-semantic change requires ChatGPT review before proceeding.

## Phase 2 — verify frozen artifacts

Locate the exact frozen prepared table/manifest and V2 reference summary/predictions. Verify all hashes above.

Fail closed if missing, ambiguous, or mismatched.

The runner itself must physically materialize only prepared rows with `signal_session_index <= 984`; do not replace this with a full read followed by filtering.

## Phase 3 — execute V3-E

Use existing:

`python -m idx_trade.ranking_v3_true_ranking ...`

Provide:

- exact frozen prepared Parquet;
- exact prepared manifest;
- exact V2 HGB reference directory;
- exact V3-E spec;
- exact V3-E review addendum;
- a new empty output directory;
- implementation code identity in `--code-commit` (use `eb4b7ac8f2b85f8ad580967be657a44f914a428b` unless a pre-outcome engineering-only fix was required, in which case use/document the final corrected code commit).

Mandatory sequence inside the run:

1. exact V2 control F1-F4;
2. prove exact control equivalence;
3. if equivalence fails: STOP, do not interpret LambdaMART;
4. if PASS: fit exactly one LambdaMART candidate;
5. compute exact existing V3 metrics/gates;
6. compute query composition, score-diversity and top-decile overlap diagnostics;
7. write artifacts/verdict and stop.

## Frozen LambdaMART

Do not change:

- `xgboost==3.2.1`;
- `XGBRanker`;
- `rank:ndcg`;
- exact signal date query grouping;
- exact 25 V2 features;
- training-only median imputer + missing indicators;
- n_estimators 200;
- learning_rate 0.05;
- max_depth 5;
- min_child_weight 1;
- reg_lambda 1;
- reg_alpha 0;
- gamma 0;
- subsample/colsample 1;
- tree_method hist;
- seed 42;
- n_jobs 1;
- pair method mean;
- pair count 8;
- LambdaRank normalization true;
- binary H10 labels unchanged;
- no early stopping or score normalization.

All-zero/all-one date queries remain in training. Do not drop them or synthesize labels.

## Frozen decision rule

Use the existing V3 absolute sanity + paired promotion gates exactly.

Allowed final decisions only:

- `V3_E_TRUE_RANKING_PROMOTE_LAMBDAMART`;
- `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

No NDCG result overrides the PR/ROC/Q5-Q1 gates.

No rescue run or second ranker is authorized.

## Required diagnostics returned

Report:

- branch + final HEAD;
- full pytest result;
- exact XGBoost version;
- materialized discovery rows/tickers/session range;
- control equivalence row count + maximum score/metric diffs;
- Control vs LambdaMART metrics F1-F4: PR-AUC, PR delta, ROC, Q5-Q1, top-decile lift;
- paired PR improvements by fold + median/q25/worst/positive count;
- median ROC change;
- median Q5-Q1 change + nonnegative fold count;
- median top-decile lift change;
- absolute sanity PASS/FAIL;
- paired promotion PASS/FAIL;
- final verdict;
- query diagnostics per fold: dates, mixed/all-zero/all-one counts, query-size distribution, rows dropped;
- score diversity per fold;
- top-decile Jaccard/entrants/exits per fold;
- F4 behavior explicitly;
- runtime and major artifact SHA-256 values;
- cumulative evaluated candidate count after execution (should be 9 if both control/candidate results were actually viewed);
- explicit confirmation that V3-D remained blocked/unscored, V2F5/F6 were not materialized, and fresh-forward outcomes were untouched.

## Documentation after run

Update:

- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md` ordinals 010/011;
- a dated V3-E result checkpoint;
- a V3-E result handoff;
- `docs/CURRENT_STATUS.md`.

Commit + push, verify clean/synchronized branch, then STOP for ChatGPT review.

Do not start integration automatically even if V3-E promotes.

## Hard prohibitions

Do not:

- run V2F5/V2F6;
- inspect reserved V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- bypass/reopen V3-D;
- add Structure-Lite to V3-E;
- use regime/sector/recency features;
- tune XGBoost after outcomes;
- run another objective/library/ranker;
- start integration/calibration/Stage6/IDX-VAL-002/execution/PnL/Kelly/paper/live/main.
