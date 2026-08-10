# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology read `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest dated checkpoint/handoff. If older stage text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1: historical benchmark failed; Stage-5 holdout consumed and never rerun;
- Probability V1: `PROBABILITY_V1_NOT_READY_DEFERRED`;
- Ranking V2 historical-development champion: `HGB_XS_MARKET`;
- V2 final refit + outcome-blind forward runtime: implemented/frozen;
- V2 fresh-forward outcomes: **NOT ACCESSED**; first independent verdict still waits for the frozen 100 consecutive H10-mature signal-session block;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- V3-A Recency: **COMPLETE — CLOSED WITHOUT PROMOTION**;
- V3-B Structure-Lite: **F1-F4 COMPLETE — PROMOTED / SURVIVING COMPONENT**;
- V3-C Regime-Specialization: **SPEC FROZEN + REVIEW PASS + IMPLEMENTED; LOCAL F1-F4 RESULT NOT YET PRESENT IN AUTHORITATIVE BRANCH STATUS**;
- V3-D Sector-Relative: **PROVISIONAL PRE-OUTCOME SPEC + IMPLEMENTATION COMPLETE; OUTCOME RUN NOT AUTHORIZED; PIT SECTOR DATA GATE NOT YET RUN**;
- V3-E True Ranking: not started;
- V2F5/V2F6: **SEALED FOR ONE FUTURE FINAL-V3 LATE-DEVELOPMENT CONFIRMATION**;
- probability calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

Cumulative evaluated V3 candidate count remains `5`. V3-C ordinals 006/007 and provisional V3-D ordinals 008/009 are unviewed in this status.

## Mandatory first reads

Before any next model/runtime action read:

1. this file;
2. newest checkpoint/handoff;
3. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
4. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
5. `docs/RANKING_V3_RESEARCH_BACKLOG.md`;
6. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
7. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`.

## Frozen data/model identities

Signal-research source:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Immutable V2 prepared cache:

- SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- 292,633 rows / 737 tickers / sessions `20..1250`;
- resolved primary H10 rows only.

Historical V2 champion:

- exact 25 features = 10 same-date XS ranks + 9 causal market-context + 6 stock-minus-market;
- median PR-AUC delta `0.0238795` across V2F1-F6;
- q25 `0.0194015`;
- positive PR folds `6/6`;
- median ROC `0.524410`;
- positive Q5-Q1 folds `6/6`;
- V2F6 ROC `0.493102`, therefore forward validation remains essential.

Historical frozen V2 HGB reference artifacts:

- summary SHA-256 `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- predictions SHA-256 `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`.

Final frozen V2 refit:

- model SHA-256 `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
- model manifest SHA-256 `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`;
- ranking score is not calibrated probability.

## V3-A Recency — closed

- control equivalence PASS on 84,732 F1-F4 rows, max score/metric diff `0.0`;
- H252: absolute sanity PASS, paired promotion FAIL;
- H504: absolute sanity PASS, paired promotion FAIL;
- deterministic result `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`;
- no recency component survives; do not rescue with more half-lives/windows.

Cumulative count after V3-A: `3`.

## V3-B Structure-Lite — promoted survivor

Exact V2 25 features plus eight causal geometry features:

1. `structure_support_distance_atr`
2. `structure_resistance_distance_atr`
3. `structure_support_touch_count_60`
4. `structure_resistance_touch_count_60`
5. `structure_nearest_level_age_sessions`
6. `structure_role_reversal_count_120`
7. `structure_breakout_retest_state`
8. `structure_breakout_volume_confirmed`

F1-F4 result:

- full pytest `252 passed, 0 failed, 3 warnings`;
- cache `216,472` rows / `674` tickers / sessions `20..984`;
- control equivalence PASS on 84,732 rows, max diff `0.0`;
- median paired PR improvement `+0.0039258450`;
- q25 `+0.0026897894`;
- worst `+0.0018412974`;
- PR positive vs control `4/4`;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- median top-decile lift change `-0.0036228765` retained as diagnostic warning;
- deterministic result `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`.

Independent review: `docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_REVIEW_PASS.md`.

Cumulative count after V3-B: `5`.

## V3-C Regime-Specialization — pending local result

Controlling files:

- `docs/RANKING_V3_REGIME_SPEC_V1.md`;
- `docs/RANKING_V3_REGIME_SPEC_REVIEW_ADDENDUM_V1.md`;
- `docs/checkpoints/2026-08-10_RANKING_V3_REGIME_IMPLEMENTED_RUN_AUTHORIZED.md`;
- `coordination/handoffs/IDX-RANKING-V3-REGIME-LOCAL-RUN.md`.

Frozen candidate = exact global V2 control vs one two-expert architecture:

- prior 252 official sessions, min 126 observations;
- stress votes: breadth-20 <= q25, market median return-20 <= q25, market median ATR/close >= q75;
- >=2/3 votes = `STRESS`, else `NORMAL`;
- one NORMAL exact-V2 HGB and one STRESS exact-V2 HGB;
- regime is router only; exact 25 V2 model features;
- no Structure-Lite, recency, score alignment, blending, or fallback.

Pre-outcome alignment bug was fixed in `9c94678b970c271b6a9f85c8943e719a5b651bff`; regression coverage was added in `3406f835d9d6573bf320daee1edb058e14b1dd77`.

At this status update, no authoritative V3-C F1-F4 result checkpoint is present yet.

## V3-D Sector-Relative — provisional implementation complete

Controlling pre-outcome files:

- spec baseline: `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_V1.md`;
- review addendum: `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_REVIEW_ADDENDUM_V1.md`;
- implementation checkpoint: `docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PROVISIONAL_IMPLEMENTED.md`;
- pre-run handoff: `coordination/handoffs/IDX-RANKING-V3-SECTOR-PRE-RUN-REVIEW.md`.

Provisional candidate budget:

- ordinal 008 exact V2 global control;
- ordinal 009 exact V2 25 features + six PIT sector-relative features.

Six provisional features:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

Implementation:

- `src/idx_trade/research_v3_sector.py` — PIT interval validation/assignment + six-feature builder;
- `src/idx_trade/ranking_v3_sector.py` — PIT validation CLI, F1-F4 cache preparation, guarded outcome runner, control equivalence and sector diagnostics;
- `tests/test_ranking_v3_sector.py` — focused no-backfill/data/feature/run guards.

Implementation lineage:

- `670a4cbc7c9fdc98eb3d82dfc336a7b23624d8a0` spec baseline;
- `ae8dcfe91e4656d4f8536d0fcf1f7fd7575ecb92` PIT sector builder;
- `ca658e13d0d3ad4333820cab7ba9d2ef766c8ffc` cache/guarded runner;
- `28981a25a427f67db0fc940415d0d7c910a9ff84` focused tests;
- `600c439c42e2a4452859ea7354e41d246db1e42e` PIT/schema/dtype hardening;
- `055cca747d5ee0ecc3209b8b0efb36dcf25ddd5d` pre-outcome review addendum;
- `1f49929b67c87e5f86e0a28eb0f512c540c97ecb` implementation checkpoint;
- `227cbbec23a5c0225dbd66709684ce075c93d391` pre-run review handoff.

### V3-D PIT data prerequisite

No V3-D outcome may run until a real historical sector artifact provides:

- `ticker`, `sector_code`;
- `effective_from`, `effective_to_exclusive`;
- `available_at`;
- `source_id`, `source_sha256`.

`usable_from=max(effective_from, available_at date)`. Current-sector backfill is prohibited.

Every referenced source hash must be tied to actual immutable source bytes or a trusted immutable archive identity and independently verified before final run authorization.

Pre-score gate, per F1-F4 train/validation:

- sector assignment >=90%;
- every sector feature finite >=80%;
- validation >=8 sectors;
- exact recomputed V2 25-feature equality <=1e-12;
- no invalid assignment/row drop;
- F5/F6 not materialized.

### V3-D outcome run is intentionally locked

The implemented `run` command requires a separate JSON with status:

`V3_D_OUTCOME_RUN_AUTHORIZED`

and pinned V3-C review + final spec/cache/manifest/implementation identities. No such authorization exists.

After V3-C is reviewed, one outcome-blind V3-D amendment is allowed before the first V3-D score. Prefer adding regime-stratified diagnostics if V3-C reveals useful state dependence; do not silently inherit V3-C experts into the V3-D discovery candidate.

**No local/full pytest result is claimed for V3-D implementation yet.**

## Immediate next actions

### V2 track

Wait. Do not inspect fresh-forward outcomes until the separate frozen one-shot forward contract is mature and authorized.

### V3-C track

Finish the already-authorized local V3-C run and return its result for independent review.

### V3-D track

Do not score. After V3-C review, follow `coordination/handoffs/IDX-RANKING-V3-SECTOR-PRE-RUN-REVIEW.md`: run full pytest, locate/validate real PIT sector history and source provenance, build the outcome-independent cache/coverage report, then stop again for final V3-D run authorization.

## Hard authorization boundary

Do not:

- alter viewed V3-A/B definitions;
- rescue V3-C after outcome access;
- use current-sector backfill for V3-D;
- score V3-D without separate final authorization;
- load/score/summarize V2F5/V2F6 for ongoing V3 hypotheses;
- inspect reserved post-2026-07-31 V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-E/integration/calibration/Stage6/IDX-VAL-002/execution-PnL/Kelly/paper/live/main automatically.
