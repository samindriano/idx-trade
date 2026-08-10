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
- V3-B Structure-Lite: **F1-F4 COMPLETE — PROMOTED / SURVIVING COMPONENT**;
- V3-C Regime-Specialization: **F1-F4 COMPLETE — KILLED / KEEP V2 CONTROL**;
- V3-D Sector / V3-E True Ranking: not started;
- V2F5/V2F6: **SEALED FOR ONE FUTURE FINAL-V3 LATE-DEVELOPMENT CONFIRMATION**;
- probability calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

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
- 292,633 rows / 737 tickers / signal sessions `20..1250`;
- resolved primary H10 rows only.

Historical V2 champion:

- `HGB_XS_MARKET`;
- exact 25 frozen features = 10 same-date XS ranks + 9 causal market-context + 6 stock-minus-market features;
- median PR-AUC delta `0.0238795` across V2F1-F6;
- q25 PR delta `0.0194015`;
- positive PR folds `6/6`;
- median ROC `0.524410`;
- positive Q5-Q1 folds `6/6`;
- V2F6 ROC `0.493102`, therefore independent forward validation remains essential.

Historical frozen V2 HGB reference artifacts:

- summary SHA-256 `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- predictions SHA-256 `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`.

Final frozen V2 refit:

- model SHA-256 `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
- model manifest SHA-256 `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`;
- ranking score is not calibrated probability.

## V3-A Recency — closed

Evaluated exactly ordinals 001-003 on V2F1-F4.

- control equivalence PASS on 84,732 rows with max score/metric differences `0.0`;
- H252: absolute sanity PASS, paired promotion FAIL;
- H504: absolute sanity PASS, paired promotion FAIL;
- deterministic result `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`;
- no recency component survives;
- do not rescue with new half-lives/windows/weight clipping.

Cumulative evaluated count after V3-A: `3`.

## V3-B Structure-Lite — promoted survivor

Frozen candidate = exact V2 25 features plus eight causal geometry features:

1. `structure_support_distance_atr`
2. `structure_resistance_distance_atr`
3. `structure_support_touch_count_60`
4. `structure_resistance_touch_count_60`
5. `structure_nearest_level_age_sessions`
6. `structure_role_reversal_count_120`
7. `structure_breakout_retest_state`
8. `structure_breakout_volume_confirmed`

V3-B F1-F4 result:

- full pytest `252 passed, 0 failed, 3 warnings`;
- cache `216,472` rows / `674` tickers / sessions `20..984`;
- cache SHA `7084759fddaa20e82ec03e50205f2872520e6b3e11ea5f294033589a9c803405`;
- manifest SHA `e428cad0ff24b57977106482cef1478e60c0660adcee6dbf103803516b35aeb2`;
- control equivalence PASS on 84,732 rows, max diff `0.0`;
- paired PR improvement positive 4/4 folds;
- median paired PR improvement `+0.0039258450`;
- q25 `+0.0026897894`;
- worst `+0.0018412974`;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- top-decile lift median change `-0.0036228765` is a retained warning/diagnostic;
- deterministic result `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`.

Independent review PASS checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_REVIEW_PASS.md`

V3-B survives as a component for a later one-shot integration experiment. Its features/parameters are closed and may not be tuned after the viewed result.

Cumulative evaluated count after V3-B: `5`.

## V3-C Regime-Specialization — completed result

Controlling spec:

`docs/RANKING_V3_REGIME_SPEC_V1.md`

- Git blob `2a2f48d68f5d3df839c61191d4a11fa870470b00`.

Independent review addendum:

`docs/RANKING_V3_REGIME_SPEC_REVIEW_ADDENDUM_V1.md`

- Git blob `a13c5ae103908311968e38c6ded233b7a1cbd901`.

Implementation checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_REGIME_IMPLEMENTED_RUN_AUTHORIZED.md`

Local execution handoff:

`coordination/handoffs/IDX-RANKING-V3-REGIME-LOCAL-RUN.md`

### Frozen V3-C question

Does explicit conditional specialization add robust value beyond the exact V2 HGB that already contains continuous market context?

### Frozen state definition

Use outcome-independent market context rebuilt from the full causal primary-liquid frame:

- `market_breadth_return_20_positive`;
- `market_median_close_return_20`;
- `market_median_atr14_over_close`.

For session t, use prior 252 official sessions only, require at least 126 finite prior observations:

- breadth <= prior q25 = stress vote;
- return <= prior q25 = stress vote;
- ATR/close >= prior q75 = stress vote;
- >=2 votes → `STRESS`, otherwise `NORMAL`;
- insufficient causal history → `MISSING_WARMUP`.

### Frozen architecture

Candidate budget exactly:

- ordinal 006 exact V2 global control;
- ordinal 007 one NORMAL exact-V2 HGB expert + one STRESS exact-V2 HGB expert.

Regime is routing metadata only. Both experts use exact V2 25 features, preprocessing, HGB parameters, target and raw-logit score. No Structure-Lite, recency, blending, score alignment, calibration, or fallback is allowed.

Implementation:

- `src/idx_trade/research_v3_regime.py`;
- `src/idx_trade/ranking_v3_regime.py`;
- `tests/test_ranking_v3_regime.py`.

Implementation lineage:

- `b92cb24367bcc675cd2bfba5bab636d239fa384a` regime builder;
- `89ca64393d94bf294a1d437990242bd5d230c96f` initial cache/runner;
- `7409bfc16914ce487fe39e393f1dd0bf62df4b29` focused tests;
- `9c94678b970c271b6a9f85c8943e719a5b651bff` pre-outcome context-alignment correction + expert class guards;
- `3406f835d9d6573bf320daee1edb058e14b1dd77` repeated-market-date regression test.

### Mandatory pre-score fragmentation gate

Every F1-F4 fold must have:

Training each NORMAL/STRESS:

- >=40 dates;
- >=5,000 rows.

Validation each NORMAL/STRESS:

- >=8 dates;
- >=500 rows;
- zero MISSING_WARMUP validation rows.

If this outcome-independent gate fails, V3-C is blocked and the regime definition must not be rescued/tuned.

### Frozen V3-C promotion requirements

Candidate must pass:

1. existing absolute sanity gate;
2. existing overall paired promotion gate;
3. additional regime-specific gate:
   - STRESS median paired PR improvement >= `+0.001`;
   - STRESS nonnegative PR improvement >=3/4 folds;
   - NORMAL median PR improvement >= `-0.001`;
   - worst fold-regime PR improvement >= `-0.005`;
   - median ROC change >= `-0.005` in each regime;
   - median Q5-Q1 change >= `-0.005` in each regime.

Possible deterministic decisions:

- `V3_C_REGIME_BLOCKED_KEEP_V2_CONTROL`;
- `V3_C_REGIME_KILL_KEEP_V2_CONTROL`;
- `V3_C_REGIME_PROMOTE_TWO_STATE_EXPERTS`.

V3-C F1-F4 result:

- run/code commit: `619b511f14d8e929f8f23ed7c001f72fe730566f`;
- full IDX Trade pytest: `264 passed, 0 failed, 3 warnings`;
- cache: `216,472` rows / `674` tickers / sessions `20..984`;
- cache SHA-256: `1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`;
- cache manifest SHA-256: `c4b090de65c291af21ea0a49f63d5d2d0dc1acbd18fff1c995494e1212f1418b`;
- fragmentation gate: PASS for V2F1-V2F4;
- control equivalence: PASS on `84,732` rows, max score/metric diff `0.0` at `1e-12`;
- two-expert absolute sanity: PASS;
- overall paired gate: FAIL;
- regime-specific gate: FAIL, with STRESS median PR improvement `-0.0289647` and NORMAL `-0.0014712`;
- deterministic result: `V3_C_REGIME_KILL_KEEP_V2_CONTROL`;
- candidate verdict: `KEEP_DIAGNOSTIC`;
- cumulative evaluated count: `7`.

V2F5/V2F6 and reserved post-2026-07-31 V2 forward outcomes were not accessed. The
V3-C candidate is closed to rescue, threshold changes, score alignment, blending,
or a second variant.

## Immediate next action

### V2 track

Wait. Do not inspect fresh-forward outcomes until the separately authorized 100-session H10-mature block exists.

### V3 track

Review the completed V3-C result in the dated checkpoint and result handoff.
Do not start V3-D/V3-E, V3 integration, F5/F6, or fresh-forward access without
separate authorization.

Do not start V3-D/V3-E or integration automatically.

## Hard authorization boundary

Do not:

- alter V3-A/B viewed hypotheses;
- tune V3-C thresholds/state definition/candidate/gates;
- include Structure-Lite in V3-C;
- load/score/summarize V2F5/V2F6;
- inspect reserved post-2026-07-31 V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-D/V3-E or integration before separate review/spec;
- calibrate probability, run Stage 6/IDX-VAL-002, execution-PnL, Kelly, paper/live, or merge main.
