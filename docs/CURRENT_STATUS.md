# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed; consumed Stage-5 holdout is never rerun;
- Probability V1 remains `PROBABILITY_V1_NOT_READY_DEFERRED`;
- Ranking V2 historical-development champion remains exact `HGB_XS_MARKET`;
- V2 final refit + outcome-blind forward runtime remain frozen;
- V2 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- V3-A Recency: **COMPLETE — KILLED / NO PROMOTION**;
- V3-B Structure-Lite: **COMPLETE — PROMOTED / ONLY CURRENT V3 SURVIVOR**;
- V3-C Regime-Specialization: **COMPLETE — KILLED**;
- V3-D Sector-Relative: **PARKED AT `BLOCKED_PIT_SECTOR_HISTORY`; OUTCOMES UNCONSUMED**;
- V3-E True Ranking: **DEPENDENCY ERRATUM APPLIED PRE-OUTCOME; LOCAL F1-F4 RUN REAUTHORIZED**;
- V2F5/V2F6: **SEALED FOR ONE FUTURE FINAL-V3 LATE-DEVELOPMENT CONFIRMATION**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

Cumulative evaluated V3 candidate count remains `7`. V3-D ordinals 008/009 and V3-E ordinals 010/011 remain `result_viewed=false`.

## Frozen data/model identities

Signal-research source:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Immutable V2 prepared cache:

- SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- 292,633 rows / 737 tickers / sessions 20..1250.

Frozen V2 HGB reference:

- summary SHA-256 `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- predictions SHA-256 `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`.

Final V2 refit:

- model SHA-256 `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
- manifest SHA-256 `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`;
- score is ranking-only, not calibrated probability.

## V3 results so far

### V3-A Recency — closed

Exact control equivalence PASS on 84,732 F1-F4 rows. H252 and H504 both failed paired promotion. Result: `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`. No recency rescue is allowed.

### V3-B Structure-Lite — promoted survivor

Exact V2 25 features + frozen eight causal geometry features.

- control equivalence PASS, max diff `0.0`;
- median paired PR improvement `+0.0039258450`;
- q25 `+0.0026897894`;
- worst `+0.0018412974`;
- PR improvement positive `4/4`;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- median top-decile lift change `-0.0036228765` retained as diagnostic warning;
- result `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`.

V3-B remains the only surviving V3 component so far. Its viewed definition is closed.

### V3-C Regime-Specialization — closed

- fragmentation gate PASS all F1-F4;
- control equivalence PASS on 84,732 rows, max diff `0.0`;
- absolute sanity PASS;
- overall paired promotion FAIL;
- regime-specific gate FAIL;
- overall median PR improvement `-0.0123171892`;
- NORMAL median `-0.0014712226`;
- STRESS median `-0.0289646749`;
- result `V3_C_REGIME_KILL_KEEP_V2_CONTROL`.

No rescue/new expert/threshold/blending/rescaling is allowed.

### V3-D Sector-Relative — parked blocked, outcomes untouched

Latest data-gate result: `BLOCKED_PIT_SECTOR_HISTORY`.

- blocked-run pytest `290 passed, 0 failed, 3 warnings`;
- no V3-D cache/manifest/outcome metric was created;
- ordinals 008/009 remain unviewed;
- current-sector backfill and guessed report-month dates remain prohibited.

Controlling checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PIT_DATA_GATE_BLOCKED.md`

A future immutable ticker-level PIT IDX-IC history with defensible publication/effective dates may unblock this frozen lane. Do not stall the V3 ladder on it.

## V3-E True Ranking — dependency erratum resolved pre-outcome

The first V3-E local attempt stopped correctly before outcome access because the original spec pinned nonexistent public package release `xgboost==3.2.1`.

Blocked checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_BLOCKED_DEPENDENCY.md`

The blocked attempt did **not** materialize prepared/reference artifacts for the run, did not execute control or LambdaMART, and did not increment the evaluated denominator.

### Controlling original research contract

Spec:

`docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`

- SHA-256 `79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55`;
- Git blob `20df2927b6663ea16955919760db9c1429cff3a5`.

Review addendum:

`docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`

- SHA-256 `6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812`;
- Git blob `01c4dca87ff52fca678c948e4ee23d3e3c82dbcd`.

### One pre-outcome dependency erratum

`docs/RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_V1.md`

- SHA-256 `bd029458f7a7cd14424af9b748cb7522f1d23b0fe8eaf20ad8f6b44d48894bea`;
- Git blob `327e053c2a1b4270acc4e7de313bba97680eff8b`;
- corrected exact dependency: **`xgboost==3.2.0`**.

This erratum changes only the impossible dependency identity. Research semantics remain unchanged:

- ordinal 010 exact V2 HGB control;
- ordinal 011 one `XGBRanker` LambdaMART candidate;
- `objective="rank:ndcg"`;
- exact signal-date query/qid;
- exact V2 25 features;
- unchanged binary H10 target;
- training-only median imputer + missing indicators;
- 200 estimators, LR .05, depth 5;
- min-child 1, lambda 1, alpha/gamma 0;
- full row/column sampling, CPU hist;
- seed 42, `n_jobs=1`;
- mean pair method, 8 pairs/sample, LambdaRank normalization enabled;
- no early stopping, score normalization, tuning, graded gains, or second ranker.

Corrected implementation:

- `src/idx_trade/ranking_v3_true_ranking_erratum.py` wraps the original frozen runner and records the erratum identity;
- `pyproject.toml` pins `xgboost==3.2.0`;
- `tests/test_ranking_v3_true_ranking.py` asserts the corrected dependency and unchanged ranker contract.

Run-reauthorization checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_RUN_REAUTHORIZED.md`

Controlling local-run handoff:

`coordination/handoffs/IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN-ERRATUM.md`

The run must use `python -m idx_trade.ranking_v3_true_ranking_erratum`, execute exact control first, prove exact control equivalence, then and only then score ordinal 011. Existing absolute sanity + paired promotion gates are unchanged.

Allowed final V3-E decisions only:

- `V3_E_TRUE_RANKING_PROMOTE_LAMBDAMART`;
- `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

No post-result rescue/second ranker is authorized.

## Mandatory first reads

1. this file;
2. `docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`;
3. `docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`;
4. `docs/RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_V1.md`;
5. `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_DEPENDENCY_ERRATUM_RUN_REAUTHORIZED.md`;
6. `coordination/handoffs/IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN-ERRATUM.md`;
7. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`;
8. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
9. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`.

## Immediate next action

Execute only the corrected V3-E local-run handoff:

1. sync latest branch;
2. install/verify exact `xgboost==3.2.0`;
3. full repository pytest;
4. verify original spec/review + erratum + frozen V2 artifact identities;
5. run exact control F1-F4 and prove equivalence;
6. only after PASS run frozen LambdaMART F1-F4;
7. document/push result;
8. STOP for ChatGPT review.

Do not start integration automatically even if V3-E promotes.

## Hard boundary

Do not:

- alter/reopen viewed V3-A/B/C hypotheses;
- bypass V3-D PIT block;
- alter V3-E research semantics after outcome access;
- run another XGBoost version/ranking objective/library;
- include Structure-Lite in standalone V3-E discovery;
- load/score/summarize V2F5/V2F6;
- inspect reserved post-2026-07-31 V2 forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start integration/calibration/Stage6/IDX-VAL-002/execution/PnL/Kelly/paper/live/main automatically.
