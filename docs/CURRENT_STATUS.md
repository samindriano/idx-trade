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
- V3-E True Ranking: **SPEC FROZEN + REVIEW PASS + IMPLEMENTED; LOCAL V2F1-V2F4 RUN AUTHORIZED BUT NOT YET EXECUTED**;
- V2F5/V2F6: **SEALED FOR ONE FUTURE FINAL-V3 LATE-DEVELOPMENT CONFIRMATION**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

Cumulative evaluated V3 candidate count is `7`. V3-D ordinals 008/009 remain `result_viewed=false`. V3-E ordinals 010/011 are implemented/preregistered but remain `result_viewed=false` until the local run actually occurs.

## Frozen identities

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

## V3 results

### V3-A Recency — closed

Exact control equivalence PASS on 84,732 F1-F4 rows. H252 and H504 both failed paired promotion. Result: `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`. No rescue half-lives/windows are allowed.

### V3-B Structure-Lite — promoted survivor

Exact V2 25 features + frozen eight causal geometry features. F1-F4:

- control equivalence PASS, max diff `0.0`;
- median paired PR improvement `+0.0039258450`;
- q25 `+0.0026897894`;
- worst `+0.0018412974`;
- PR improvement positive `4/4`;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- median top-decile lift change `-0.0036228765` retained as diagnostic warning;
- result `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`.

V3-B is the only surviving V3 component so far. Its viewed definition is closed.

### V3-C Regime-Specialization — closed

Two-expert NORMAL/STRESS architecture on exact V2 25 features:

- cache 216,472 rows / 674 tickers / sessions 20..984;
- fragmentation gate PASS all F1-F4;
- control equivalence PASS on 84,732 rows, max diff `0.0`;
- absolute sanity PASS;
- overall paired promotion FAIL;
- regime-specific gate FAIL;
- overall median PR improvement `-0.0123171892`;
- NORMAL median PR improvement `-0.0014712226`;
- STRESS median PR improvement `-0.0289646749`;
- result `V3_C_REGIME_KILL_KEEP_V2_CONTROL`.

Do not rescue with new regime thresholds, more experts, rescaling, blending, or fallback.

## V3-D Sector-Relative — parked blocked, outcomes untouched

Frozen candidate remains exact V2 25 features + six PIT sector-relative features in one global HGB. The post-V3-C NORMAL/STRESS robustness amendment remains frozen.

Latest data-gate result: `BLOCKED_PIT_SECTOR_HISTORY`.

- blocked-run final pytest `290 passed, 0 failed, 3 warnings` in `26.2 s`;
- no V3-D cache/manifest was created;
- no V3-D F1-F4 outcome metric was computed;
- ordinals 008/009 remain unviewed;
- current-sector backfill and guessed report-month dates remain prohibited.

Controlling files:

- `docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PIT_DATA_GATE_BLOCKED.md`;
- `docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_BLOCK_REVIEW_PASS_PARKED.md`.

A future unblock remains possible only if a defensible immutable ticker-level PIT IDX-IC history with publication/effective-date semantics is obtained. Do not stall the V3 ladder on this external data dependency.

## V3-E True Ranking — implemented / run authorized

Frozen research question:

> Does one tightly bounded nonlinear same-date learning-to-rank objective outperform the exact frozen binary HGB ranking score on identical V2 causal rows and V2F1-V2F4 discovery folds?

Controlling spec:

`docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`

- SHA-256 `79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55`;
- Git blob `20df2927b6663ea16955919760db9c1429cff3a5`.

Review addendum:

`docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`

- SHA-256 `6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812`;
- Git blob `01c4dca87ff52fca678c948e4ee23d3e3c82dbcd`.

Implementation checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_IMPLEMENTED_RUN_AUTHORIZED.md`

Local run handoff:

`coordination/handoffs/IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN.md`

Candidate budget:

- ordinal 010 exact V2 `HGB_XS_MARKET` control;
- ordinal 011 exact V2 25 features + one `xgboost==3.2.1` `XGBRanker` LambdaMART candidate with `rank:ndcg` and exact signal-date queries.

Frozen candidate details:

- binary H10 target unchanged;
- exact V2 25 feature order only;
- V2-style training-only median imputer + missing indicators, no scaler;
- `n_estimators=200`, `learning_rate=0.05`, `max_depth=5`;
- `min_child_weight=1`, `reg_lambda=1`, `reg_alpha=0`, `gamma=0`;
- `subsample=1`, `colsample_bytree=1`, `tree_method=hist`;
- seed 42, `n_jobs=1`;
- `lambdarank_pair_method=mean`, 8 pairs/sample, normalization enabled;
- no early stopping, target gain engineering, score normalization or calibration.

Implementation lineage:

- `7e9d9440798d4ece254069a570a7c6e8916df127` — frozen spec;
- `04ad6e1b20359d96295273c34279c305b28dcf35` — independent review addendum;
- `52a267b637eb9277a9f81617e396442d465f1910` — exact XGBoost dependency pin;
- `b1eff77503e91953fe43fac624153eeefc04c8b7` — runner implementation;
- `cc1643d61bae0edb34deb6e7d8b583615dfea2f2` — focused tests;
- `eb4b7ac8f2b85f8ad580967be657a44f914a428b` — deterministic diagnostic fixture correction;
- `7b4e10ccefcf158adb0d03ac2da2e5ecb431489e` — implementation/run-authorization checkpoint;
- `aaaea6ccdd5064de601a8b988a01d11e85358f88` — local-run handoff.

The runner physically reads only prepared rows with `signal_session_index <= 984`, executes the exact V2 control first, requires exact control equivalence, then runs the one LambdaMART candidate. Existing V3 absolute sanity + paired promotion gates remain unchanged.

No V3-E outcome has been viewed. The ChatGPT implementation runtime had XGBoost 3.1.3 rather than frozen 3.2.1, so no full/local outcome-run claim is made here. The local operator must first establish exact XGBoost 3.2.1 and pass full repository pytest.

Allowed V3-E final decisions only:

- `V3_E_TRUE_RANKING_PROMOTE_LAMBDAMART`;
- `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

No post-result rescue/second ranker is authorized.

## Mandatory first reads

1. this file;
2. `docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md`;
3. `docs/RANKING_V3_TRUE_RANKING_SPEC_REVIEW_ADDENDUM_V1.md`;
4. `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_IMPLEMENTED_RUN_AUTHORIZED.md`;
5. `coordination/handoffs/IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN.md`;
6. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`;
7. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
8. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
9. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`.

## Immediate next action

Execute only `coordination/handoffs/IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN.md` locally:

1. sync branch / exact XGBoost 3.2.1;
2. full repository pytest;
3. verify frozen artifacts;
4. exact V2 control F1-F4 and control equivalence;
5. only after PASS run the single frozen LambdaMART candidate F1-F4;
6. document/push result and STOP for ChatGPT review.

Do not start integration automatically even if V3-E promotes.

## Hard boundary

Do not:

- alter/reopen viewed V3-A/B/C hypotheses;
- backfill current-sector labels or bypass V3-D PIT block;
- score V3-D without a future separate data-gate PASS and final authorization;
- alter V3-E candidate/objective/parameters after outcome access;
- include V3-B Structure-Lite in standalone V3-E discovery;
- run a second ranking objective/library;
- load/score/summarize V2F5/V2F6;
- inspect reserved post-2026-07-31 V2 forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start integration/calibration/Stage6/IDX-VAL-002/execution/PnL/Kelly/paper/live/main automatically.
