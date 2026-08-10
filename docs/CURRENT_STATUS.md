# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology read `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest dated checkpoint/handoff. If older stage text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1: historical benchmark failed; Stage-5 holdout consumed and never rerun;
- Probability V1: `PROBABILITY_V1_NOT_READY_DEFERRED`;
- Ranking V2 historical-development champion: `HGB_XS_MARKET`;
- V2 final refit + outcome-blind forward runtime: implemented/frozen;
- V2 fresh-forward outcomes: **NOT ACCESSED**; first independent verdict still waits for exactly 100 consecutive H10-mature forward signal sessions under the frozen one-shot contract;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- V3-A Recency: **COMPLETE — CLOSED WITHOUT PROMOTION**;
- V3-A result: `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`; H252/H504 are `KEEP_DIAGNOSTIC`; cumulative V3 candidate count `3`;
- V3-B Structure-Lite: **F1-F4 COMPLETE — PROMOTED FOR NEXT RESEARCH STEP**;
- V3-B outcome score: `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8` on historical development folds only;
- V2F5/V2F6: **SEALED FOR ONE FUTURE FINAL-V3 LATE-DEVELOPMENT CONFIRMATION**;
- V3-C Regime / V3-D Sector / V3-E True Ranking: not started;
- probability calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

## Current controlling V3-B documents

Frozen specification:

`docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`

- reported SHA-256: `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- Git blob: `0392ab506aa451355697327d416f8f2b2ea21d4f`.

Independent review addendum:

`docs/RANKING_V3_STRUCTURE_LITE_SPEC_REVIEW_ADDENDUM_V1.md`

- Git blob: `717871707e833ab9818c249d52aae5b234334fc4`.

Implementation/run-authorization checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_IMPLEMENTED_RUN_AUTHORIZED.md`

Current local-run handoff:

`coordination/handoffs/IDX-RANKING-V3-STRUCTURE-LITE-LOCAL-RUN.md`

Mandatory runtime/read-before-next-model note:

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`

Mandatory V3 research context:

- `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
- `docs/RANKING_V3_RESEARCH_BACKLOG.md`;
- `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`.

## V2 data/model frozen identities

Signal-research source:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Immutable V2 prepared cache:

- SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- 292,633 rows / 737 tickers / signal sessions `20..1250`;
- resolved primary H10 rows only.

Historical-development V2 champion:

- `HGB_XS_MARKET`;
- 25 frozen features = 10 same-date XS ranks + 9 causal market-context + 6 stock-minus-market features;
- median PR-AUC delta `0.0238795` across V2F1-F6;
- q25 PR delta `0.0194015`;
- positive PR folds `6/6`;
- median ROC `0.524410`;
- positive Q5-Q1 folds `6/6`;
- V2F6 ROC `0.493102`, therefore forward validation remains essential.

Final frozen V2 refit:

- model SHA-256 `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
- model manifest SHA-256 `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`;
- fit rows 292,633 / 737 tickers / sessions `20..1250`;
- ranking score is not calibrated probability.

Historical frozen V2 HGB reference artifacts needed for V3 control equivalence:

- summary SHA-256 `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- predictions SHA-256 `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`.

## V3-A Recency closed result

V3-A evaluated exactly:

- ordinal 001 exact V2 control;
- ordinal 002 H252;
- ordinal 003 H504;
- V2F1-F4 only;
- control equivalence PASS on 84,732 rows with maximum score/metric differences `0.0`;
- full local pytest at that run: `240 passed, 3 warnings`;
- H252 absolute sanity PASS, paired promotion FAIL;
- H504 absolute sanity PASS, paired promotion FAIL;
- selected component: none;
- deterministic result `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.

Do not rescue recency with new half-lives/windows/weight clipping.

## V3-B Structure-Lite frozen candidate

Exact candidate budget:

1. ordinal 004: exact V2 `HGB_XS_MARKET` control;
2. ordinal 005: exact V2 25 features + one frozen eight-feature Structure-Lite bundle.

Eight new features, exact order:

1. `structure_support_distance_atr`
2. `structure_resistance_distance_atr`
3. `structure_support_touch_count_60`
4. `structure_resistance_touch_count_60`
5. `structure_nearest_level_age_sessions`
6. `structure_role_reversal_count_120`
7. `structure_breakout_retest_state`
8. `structure_breakout_volume_confirmed`

Implementation:

- `src/idx_trade/research_v3_structure_lite.py` — causal geometry engine;
- `src/idx_trade/ranking_v3_structure_lite.py` — immutable discovery-cache prepare + F1-F4 runner;
- `tests/test_ranking_v3_structure_lite.py` — focused causal/guardrail tests.

Implementation lineage:

- `d451befd10e32711fdaf7f468f6038e2e58f0376` geometry engine;
- `837e5ce42e90825451b019517022db7d79a7bf81` cache/runner;
- `c06f1a32068e3b8ad7c09385709a7f80258d11b4` focused tests;
- `885430ef9d2dbacd85af71fa1119be4a96c34752` fixture correction only.

The implementation uses exact V2 research H/L/C/Volume + causal ATR, official-session windows, prior-session level inventory, deterministic level clustering, separated touches, role reversal, causal breakout/retest state and prior-only volume confirmation. It rejects label/outcome columns and has no Open dependency.

## V3-B F1-F4 result

The frozen local run completed on source/implementation HEAD
`eee4ed0458fdfdea5fdc0f5335ec211efd3dd80b`.

- full pytest: `252 passed, 0 failed, 3 warnings`;
- cache: `216,472` rows, `674` tickers, sessions `20..984`;
- cache SHA-256: `7084759fddaa20e82ec03e50205f2872520e6b3e11ea5f294033589a9c803405`;
- cache manifest SHA-256: `e428cad0ff24b57977106482cef1478e60c0660adcee6dbf103803516b35aeb2`;
- control equivalence: PASS on `84,732` rows; max score and metric differences `0.0` at `1e-12` tolerance;
- Structure-Lite absolute sanity: PASS;
- Structure-Lite paired promotion: PASS;
- deterministic result: `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`;
- cumulative V3 candidate count: `5`.

This is historical-development evidence on V2F1-V2F4, not independent
validation. The full metrics, paired deltas, coverage, runtime, and artifact
hashes are recorded in
`docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_F1_F4_RESULT.md`.

## V3-B next boundary

Stop for independent ChatGPT review. Do not start V3-C or any integration,
F5/F6 late-development confirmation, fresh-forward access, calibration,
Stage 6, `IDX-VAL-002`, execution-PnL, paper/live work, or main merge in this
run.

## Hard authorization boundary

Do not:

- change Structure-Lite features/constants/model/gates based on results;
- add a V3-B variant/ablation/rescue;
- reopen V3-A;
- load/score/summarize V2F5/V2F6 for V3 R&D;
- inspect reserved post-2026-07-31 V2 fresh-forward outcomes before its separate one-shot authorization;
- write `FORWARD_OUTCOME_ACCESS_STARTED` before that authorization;
- start V3-C/D/E outcome work or V3 integration before separate reviewed specs;
- calibrate probabilities, run Stage 6/IDX-VAL-002, claim execution PnL, Kelly-size, paper/live trade, or merge to main.
