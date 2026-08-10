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
- V3-A Recency: **COMPLETE — KILLED**;
- V3-B Structure-Lite: **F1-F4 COMPLETE — PROMOTED / ONLY SURVIVING TIER-1 COMPONENT**;
- V3-C Regime-Specialization: **COMPLETE — KILLED**;
- V3-D Sector-Relative: **PARKED AT `BLOCKED_PIT_SECTOR_HISTORY`; OUTCOMES UNCONSUMED**;
- V3-E True Ranking: **COMPLETE — KILLED**;
- optional V3 integration: **SKIPPED — only one Tier-1 component survives**;
- final V3 late-development confirmation: **FROZEN + IMPLEMENTED + LOCAL RUN AUTHORIZED; V2F5/V2F6 NOT YET ACCESSED**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

Cumulative evaluated V3 architecture-candidate count is `9`. Final late-development confirmation reuses existing V3-B ordinals 004/005 and does not create a new candidate ordinal. V3-D ordinals 008/009 remain unviewed.

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

## Tier-1 V3 result summary

### V3-A Recency — killed

Exact control equivalence PASS on 84,732 F1-F4 rows. Both H252/H504 failed paired promotion. No rescue is allowed.

### V3-B Structure-Lite — survivor

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

Its viewed definition is closed.

### V3-C Regime-Specialization — killed

Two-expert NORMAL/STRESS architecture passed absolute sanity but failed overall paired and regime-specific gates. Overall median PR improvement `-0.0123171892`; STRESS median `-0.0289646749`. No rescue/new expert/blending is allowed.

### V3-D Sector-Relative — blocked without outcome access

`BLOCKED_PIT_SECTOR_HISTORY`. No cache/model outcome was created. Current-sector backfill and guessed report-month dates are prohibited. A future defensible immutable PIT IDX-IC archive may unblock the frozen lane, but it does not stall current V3 finalization.

### V3-E True Ranking — killed

Authoritative result:

`docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_RESULT.md`

- final pytest `307 passed, 0 failed, 3 warnings`;
- XGBoost `3.2.0` after the pre-outcome dependency erratum;
- exact control equivalence PASS on 84,732 rows, all max diffs `0.0`;
- LambdaMART absolute sanity PASS;
- paired promotion FAIL;
- median paired PR improvement `+0.0049421451` but worst fold `-0.0253353754`;
- median Q5-Q1 change `-0.0072112874`, non-below control only `1/4` folds;
- final `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`;
- no rescue/second ranker is allowed.

## Final V3 historical-development candidate

There is only one surviving component, so no integration experiment is justified.

Candidate for late-development confirmation remains exact existing V3-B ordinal 005:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

No new feature/model/ordinal is introduced.

### One-shot V2F5/V2F6 confirmation contract

Controlling spec:

`docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_SPEC_V1.md`

- SHA-256 `c1acbe99656b0a0a0adabc7840ad779ee0553b59b7441a24607a53322d1b369f`;
- Git blob `08eba22b5f36efb160cc01abbfb5cb82d079f36e`.

Review addendum:

`docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_REVIEW_ADDENDUM_V1.md`

- SHA-256 `fa6c856f6cc45714b8ba5b4817a06fab2f9141fe66be7982c0c2a30ee1fd799e`;
- Git blob `8ae7147af61c9aeaf9993576cac198c8ab8c9387`.

Implementation checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_IMPLEMENTED_RUN_AUTHORIZED.md`

Run handoff:

`coordination/handoffs/IDX-RANKING-V3-FINAL-STRUCTURE-LITE-LATE-DEV-RUN.md`

Implementation:

`src/idx_trade/ranking_v3_final_late_dev.py`

Focused tests:

`tests/test_ranking_v3_final_late_dev.py`

Late folds are exactly:

- V2F5 train 1..984 / purge 985..1004 / validation 1005..1104;
- V2F6 train 1..1104 / purge 1105..1124 / validation 1125..1224.

The two folds must be executed atomically after preflight/cache prepare. Do not inspect F5 before deciding whether to run F6.

Frozen PASS requires:

- candidate PR delta >0, ROC>0.5, Q5-Q1>0 on both F5/F6;
- paired PR improvement >=0 on both;
- median paired PR improvement >=+0.001;
- median ROC change >=-0.005;
- paired Q5-Q1 change >=0 on both.

Top-decile lift remains diagnostic only.

Allowed final decisions only:

- `V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS`;
- `V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`.

No MIXED/rescue/second late-development attempt.

## Mandatory first reads

1. this file;
2. `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_RESULT.md`;
3. `docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_SPEC_V1.md`;
4. `docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_REVIEW_ADDENDUM_V1.md`;
5. `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_IMPLEMENTED_RUN_AUTHORIZED.md`;
6. `coordination/handoffs/IDX-RANKING-V3-FINAL-STRUCTURE-LITE-LATE-DEV-RUN.md`;
7. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`;
8. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`.

## Immediate next action

Execute only `coordination/handoffs/IDX-RANKING-V3-FINAL-STRUCTURE-LITE-LATE-DEV-RUN.md` locally:

1. sync branch and run full pytest;
2. verify all frozen source/spec identities;
3. build outcome-independent Structure-Lite cache through session 1224;
4. freeze/report cache + manifest hashes and coverage;
5. execute exact V2 control on F5/F6 and prove equivalence;
6. only after equivalence PASS execute exact frozen Structure-Lite on both F5/F6 in one run;
7. apply frozen gates, document/push result;
8. STOP for ChatGPT review.

## Hard boundary

Do not:

- alter/reopen V3-A/B/C/E definitions;
- integrate killed components;
- bypass V3-D PIT block;
- create a new candidate ordinal for F5/F6 confirmation;
- run F5/F6 more than once;
- materialize or score session 1225+;
- inspect reserved post-2026-07-31 V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start calibration/Stage6/IDX-VAL-002/execution/PnL/Kelly/paper/live/main automatically.
