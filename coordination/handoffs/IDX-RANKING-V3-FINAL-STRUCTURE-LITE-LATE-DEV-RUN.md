# Handoff — IDX Ranking V3 Final Structure-Lite Late-Development Confirmation

Date: 2026-08-10 (Asia/Jakarta)

Status: **LOCAL RUN AUTHORIZED — ONE-SHOT V2F5/V2F6 ONLY**

## Objective

Run the final historical-development confirmation of the unchanged V3-B Structure-Lite architecture on V2F5/V2F6 exactly once.

This is not a new candidate search. There is no integration experiment because Structure-Lite is the only surviving Tier-1 V3 component.

## Required reads

1. `docs/CURRENT_STATUS.md`
2. `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_RESULT.md`
3. `docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_SPEC_V1.md`
4. `docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_REVIEW_ADDENDUM_V1.md`
5. `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_IMPLEMENTED_RUN_AUTHORIZED.md`
6. `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`
7. `docs/RANKING_V3_STRUCTURE_LITE_SPEC_REVIEW_ADDENDUM_V1.md`
8. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
9. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
10. `src/idx_trade/ranking_v3_final_late_dev.py`
11. `tests/test_ranking_v3_final_late_dev.py`

## Preflight

- sync `research/idx-ranking-v2-spec-v1` to the latest remote;
- require clean working tree before execution;
- record HEAD;
- run full repository pytest from explicit repo root;
- record exact pass/fail/warnings/time.

If pytest fails, stop before cache prepare/outcome access unless the defect is an unambiguous engineering-only issue that does not alter the frozen candidate, gates, data identities or fold contract. Any such fix must be committed and followed by another full pytest PASS.

## Frozen source identities

Verify exact:

- signal panel SHA `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`;
- V2 prepared SHA `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- V2 prepared manifest SHA `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- V2 HGB summary SHA `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- V2 HGB predictions SHA `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`.

Verify controlling documents:

- V3-B Structure-Lite spec SHA `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- V3-B spec Git blob `0392ab506aa451355697327d416f8f2b2ea21d4f`;
- V3-B review Git blob `717871707e833ab9818c249d52aae5b234334fc4`;
- late-confirm spec SHA `c1acbe99656b0a0a0adabc7840ad779ee0553b59b7441a24607a53322d1b369f`;
- late-confirm spec Git blob `08eba22b5f36efb160cc01abbfb5cb82d079f36e`;
- late-confirm review SHA `fa6c856f6cc45714b8ba5b4817a06fab2f9141fe66be7982c0c2a30ee1fd799e`;
- late-confirm review Git blob `8ae7147af61c9aeaf9993576cac198c8ab8c9387`.

The runner normalizes line endings for text identity checks.

## Phase 1 — outcome-independent late cache prepare

Use a new empty output directory and run:

`python -m idx_trade.ranking_v3_final_late_dev prepare ...`

Arguments:

- `--panel <frozen signal panel>`
- `--calendar <frozen official calendar>`
- `--security-master <frozen security master>`
- `--v2-prepared <frozen V2 prepared parquet>`
- `--v2-manifest <frozen V2 manifest>`
- `--structure-spec docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`
- `--structure-addendum docs/RANKING_V3_STRUCTURE_LITE_SPEC_REVIEW_ADDENDUM_V1.md`
- `--late-spec docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_SPEC_V1.md`
- `--late-addendum docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_REVIEW_ADDENDUM_V1.md`
- `--output-dir <new empty prepare dir>`
- `--code-commit <actual implementation HEAD>`

Mandatory prepare checks:

- status `RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CACHE_FROZEN`;
- exact V2 columns/identity/order preserved;
- exact frozen V3-B 25+8 feature order;
- no duplicate/orphan rows;
- no infinity in Structure-Lite features;
- max materialized session <=1224;
- no session 1225+ materialized;
- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`;
- report F5/F6 validation feature finite coverage;
- freeze cache SHA and manifest SHA.

Do not inspect target-performance metrics during prepare.

## Phase 2 — one atomic F5/F6 confirmation

Only after Phase 1 passes, use a second new empty output directory and run:

`python -m idx_trade.ranking_v3_final_late_dev run ...`

Arguments:

- `--cache <prepared late cache>`
- `--cache-manifest <prepared late manifest>`
- `--reference-v2-dir <immutable V2 HGB reference directory>`
- same structure spec/addendum paths;
- same late spec/addendum paths;
- `--output-dir <new empty run dir>`;
- `--code-commit <actual implementation HEAD>`.

Mandatory order:

1. materialize frozen late cache only;
2. materialize immutable V2 reference predictions only for V2F5/V2F6;
3. execute exact V2 control on both folds;
4. prove control equivalence on both folds at `1e-12`;
5. if equivalence fails, stop before interpreting Structure-Lite;
6. if equivalence passes, execute exact frozen Structure-Lite on **both F5 and F6 in the same run**;
7. apply the frozen binary absolute + paired confirmation gates;
8. write diagnostics/verdict and stop.

Do not run F5 alone and inspect it before deciding whether to run F6.

## Frozen final gates

Absolute candidate gate requires on both F5 and F6:

- finite required metrics;
- PR delta >0;
- ROC >0.5;
- Q5-Q1 >0.

Paired confirmation requires:

- paired PR improvement >=0 on both folds;
- median paired PR improvement >=+0.001;
- median ROC change >=-0.005;
- paired Q5-Q1 change >=0 on both folds.

Top-decile lift is diagnostic only.

Allowed final decision only:

- `V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS`; or
- `V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`.

No MIXED/rescue/ablation/second attempt.

## Required return report

Return:

- branch + final HEAD + clean/synced state;
- full pytest result;
- late cache rows/tickers/session range, cache SHA, manifest SHA;
- F5/F6 Structure-Lite feature coverage;
- control-equivalence row count and all max diffs;
- exact Control vs Structure-Lite F5/F6 PR-AUC, PR delta, ROC, Q5-Q1, top-decile lift;
- paired PR/ROC/Q5-Q1/top-decile changes for each fold;
- median/worst paired PR improvement;
- median ROC change;
- median/worst Q5-Q1 change;
- top-decile Jaccard/entrants/exits;
- absolute gate PASS/FAIL;
- paired gate PASS/FAIL;
- deterministic final verdict;
- runtime + major artifact hashes;
- explicit confirmation cumulative architecture-candidate count remains 9;
- explicit confirmation V3-D still blocked, sessions 1225+ not materialized/scored, fresh-forward untouched, marker not written.

## Documentation after run

Update:

- a dated final late-development result checkpoint;
- a result handoff;
- `docs/CURRENT_STATUS.md`;
- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md` to record F5/F6 confirmation on existing ordinals 004/005 without creating a new candidate ordinal.

Commit + push, verify clean/synchronized branch, then STOP for ChatGPT review.

## Hard prohibitions

Do not:

- alter V3-B geometry/model/gates;
- integrate killed V3-A/C/E;
- bypass V3-D PIT sector block;
- create a new V3 candidate ordinal for this confirmation;
- run F5/F6 more than once;
- materialize or score session 1225+;
- access reserved post-2026-07-31 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start calibration, Stage 6, execution/PnL, paper/live or merge main.
