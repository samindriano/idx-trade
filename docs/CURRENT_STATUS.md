# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology read `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, the V3 hypothesis ledger, and the newest dated checkpoint/handoff. If older stage text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed; Stage-5 holdout was consumed and is never rerun;
- Probability V1 remains `PROBABILITY_V1_NOT_READY_DEFERRED`;
- Ranking V2 historical-development champion remains exact `HGB_XS_MARKET`;
- V2 final refit + outcome-blind forward runtime remain frozen;
- V2 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- V3-A Recency: **COMPLETE — CLOSED WITHOUT PROMOTION**;
- V3-B Structure-Lite: **F1-F4 COMPLETE — PROMOTED / ONLY CURRENT V3 SURVIVING COMPONENT**;
- V3-C Regime-Specialization: **F1-F4 COMPLETE — KILLED / REVIEW CLOSED**;
- V3-D Sector-Relative: **PIT DATA GATE BLOCKED; OUTCOME SCORING NOT AUTHORIZED**;
- V3-E True Ranking: not started;
- V2F5/V2F6: **SEALED FOR ONE FUTURE FINAL-V3 LATE-DEVELOPMENT CONFIRMATION**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

Cumulative evaluated V3 candidate count is `7`. V3-D ordinals 008/009 remain unviewed and do not count yet.

Latest V3-D data-gate result: `BLOCKED_PIT_SECTOR_HISTORY`.

- full pytest: `290 passed, 0 failed, 3 warnings` in `26.2 seconds`;
- official current-sector pages and monthly report rows were located, but no
  immutable ticker-level historical PIT sector archive with defensible
  `effective_from`, `effective_to_exclusive`, and `available_at` semantics was
  established;
- current-sector backfill and assumed report-month dates are prohibited;
- no `validate-history`, V3-D prepare, or V3-D score was run;
- result checkpoint:
  `docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PIT_DATA_GATE_BLOCKED.md`;
- result handoff:
  `coordination/handoffs/IDX-RANKING-V3-SECTOR-PIT-DATA-GATE-BLOCKED.md`.

## Mandatory first reads

1. this file;
2. `docs/checkpoints/2026-08-10_RANKING_V3_REGIME_F1_F4_RESULT.md`;
3. `docs/checkpoints/2026-08-10_RANKING_V3_REGIME_REVIEW_PASS_V3D_AMENDED.md`;
4. `coordination/handoffs/IDX-RANKING-V3-SECTOR-PRE-RUN-REVIEW.md`;
5. `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_V1.md`;
6. `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_REVIEW_ADDENDUM_V1.md`;
7. `docs/RANKING_V3_SECTOR_RELATIVE_POST_V3C_AMENDMENT_V1.md`;
8. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`;
9. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
10. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
11. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`.

## Frozen data/model identities

Signal-research source:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Immutable V2 prepared cache:

- SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- 292,633 rows / 737 tickers / sessions `20..1250`.

Historical frozen V2 HGB reference artifacts:

- summary SHA-256 `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- predictions SHA-256 `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`.

Final V2 refit:

- model SHA-256 `5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace`;
- manifest SHA-256 `f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9`;
- ranking score is not calibrated probability.

## V3 results so far

### V3-A Recency — killed

- exact control equivalence PASS on 84,732 F1-F4 rows, max score/metric diff `0.0`;
- H252 and H504 both failed paired promotion;
- result `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`;
- no recency rescue is allowed.

### V3-B Structure-Lite — promoted survivor

Exact V2 25 features + eight causal geometry features.

F1-F4:

- cache `216,472` rows / `674` tickers / sessions `20..984`;
- control equivalence PASS, max diff `0.0`;
- median paired PR improvement `+0.0039258450`;
- q25 `+0.0026897894`;
- worst `+0.0018412974`;
- PR better than control `4/4` folds;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- median top-decile lift change `-0.0036228765` retained as warning;
- result `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`.

Structure-Lite remains the only promoted V3 component so far. Its viewed definition is closed.

### V3-C Regime-Specialization — killed

Authoritative checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_REGIME_F1_F4_RESULT.md`

Final merged-tree validation after preserving concurrent V3-D engineering:

- `277 passed, 0 failed, 3 warnings in 18.52 s`;
- no V3-D cache/outcome was run during that validation.

V3-C cache:

- `216,472` rows / `674` tickers / sessions `20..984`;
- SHA-256 `1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`;
- manifest SHA-256 `c4b090de65c291af21ea0a49f63d5d2d0dc1acbd18fff1c995494e1212f1418b`;
- fragmentation gate PASS all F1-F4;
- exact control equivalence PASS on 84,732 rows, max diff `0.0`.

Two-expert result:

- absolute sanity PASS;
- overall paired promotion FAIL;
- regime-specific gate FAIL;
- overall median PR improvement `-0.0123171892`;
- overall median ROC change `-0.0087919123`;
- overall median Q5-Q1 change `-0.0207539272`;
- NORMAL median PR improvement `-0.0014712226`;
- STRESS median PR improvement `-0.0289646749`;
- result `V3_C_REGIME_KILL_KEEP_V2_CONTROL`.

Interpretation: reject the tested explicit sample-fragmenting two-expert architecture. Do not rescue with new regime thresholds, more experts, rescaling, blending, or fallback.

## V3-D Sector-Relative — amended pre-outcome architecture

Primary candidate is unchanged:

- ordinal 008 exact V2 global control;
- ordinal 009 exact V2 25 features + six PIT sector-relative features;
- one global HGB.

Six features:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

Implementation:

- `src/idx_trade/research_v3_sector.py` — PIT interval validation/assignment and six-feature builder;
- `src/idx_trade/ranking_v3_sector.py` — F1-F4 cache prepare, base runner, control equivalence, sector diagnostics;
- `src/idx_trade/ranking_v3_sector_amended.py` — mandatory post-V3-C regime robustness wrapper;
- `tests/test_ranking_v3_sector.py`;
- `tests/test_ranking_v3_sector_amended.py`.

Post-V3-C amendment is frozen in:

`docs/RANKING_V3_SECTOR_RELATIVE_POST_V3C_AMENDMENT_V1.md`

The exact V3-C regime cache is used **only as an evaluation partition**, not as a model feature/router. Final V3-D promotion requires all original gates plus:

- NORMAL median paired PR >= `-0.005`;
- STRESS median paired PR >= `-0.005`;
- NORMAL/STRESS median ROC change each >= `-0.005`;
- NORMAL/STRESS median Q5-Q1 change each >= `-0.005`;
- worst fold/state PR improvement >= `-0.015`.

Top-decile lift remains diagnostic only.

### PIT sector prerequisite

No V3-D outcome may run until a defensible historical sector artifact contains:

- `ticker`, `sector_code`;
- `effective_from`, `effective_to_exclusive`;
- `available_at`;
- `source_id`, `source_sha256`.

`usable_from = max(effective_from, available_at date)`.

Current-sector backfill is prohibited. Every source hash must be tied to real immutable source bytes or a trusted immutable archive identity and independently verified.

Pre-score gate per F1-F4 train/validation:

- PIT assignment >=90%;
- all six feature finite rates >=80%;
- validation >=8 sectors;
- exact recomputed V2 25-feature equality <=1e-12;
- no invalid assignment or row drop;
- max materialized session <=984;
- F5/F6 absent;
- outcome metrics not computed.

## Immediate next action

Execute **only** `coordination/handoffs/IDX-RANKING-V3-SECTOR-PRE-RUN-REVIEW.md`:

1. full pytest on the amended tree;
2. locate/build and independently verify real PIT sector history;
3. run PIT validator;
4. build outcome-independent V3-D cache through session 984;
5. report coverage/provenance/cache hashes;
6. STOP for ChatGPT review.

Do not create final V3-D outcome authorization yet and do not score V3-D.

## Hard boundary

Do not:

- alter/reopen viewed V3-A/B/C hypotheses;
- use current-sector backfill;
- change V3-D six-feature candidate or post-V3-C guard after outcome access;
- score V3-D without separate final authorization;
- load/score/summarize V2F5/V2F6;
- inspect reserved post-2026-07-31 V2 forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-E/integration/calibration/Stage6/IDX-VAL-002/execution/PnL/Kelly/paper/live/main automatically.
