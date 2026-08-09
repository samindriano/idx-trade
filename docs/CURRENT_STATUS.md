# IDX Trade — Current Status

Date: 2026-08-09 (Asia/Jakarta)

This is the short **authoritative first-read status layer**. For full chronology read
`docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest
checkpoint. If an older "current stage" paragraph conflicts with this file,
this file plus the newest dated checkpoint controls the current phase and
authorization boundary.

## Current phase

- active branch: `research/idx-stage5-postmortem-v1`
- parent branch: `research/idx-stage5-ranking-holdout-v1`
- Ranking V1: **failed benchmark; rejected as a holdout-passed architecture**
- Stage-5 holdout: **consumed for `RANKING_V1_ONLY`; no retry permitted**
- `holdout_outcome_accessed=true`
- Probability V1: **`PROBABILITY_V1_NOT_READY_DEFERRED`**
- current phase: **bounded Stage-5 post-mortem complete; interpretation pending**
- current post-mortem plan: `docs/STAGE5_POSTMORTEM_PLAN_V1.md`
- Stage 6: not authorized
- Ranking V2 implementation: not authorized yet
- Probability V2: not authorized yet
- `IDX-VAL-002`: not started
- merge to `main`: not authorized
- paper/live trading: not authorized

## Data foundation

Strict execution-grade OHLCV:

- 126 sessions: PASS
- 504 sessions: FAIL because historical Open evidence is incomplete
- 1260 sessions: FAIL for the same execution-grade reason

Signal-research HLCV:

- 1260 sessions: **GO**
- window: `2021-04-29 -> 2026-07-31`
- 979 required common stocks
- 981,940 ACTIVE research rows
- H/L/C/Volume coverage: 100%
- nullable Open rows: 446,843; no synthetic Open
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- manifest SHA-256: `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`
- manifest valid=true, 15/15

## Frozen V1 semantics

- signal after session-t close;
- reference = `Close_t`;
- primary H10 first-touch barrier;
- ATR14, SL=1.0 ATR, RR=1.5;
- same-bar ambiguity not guessed;
- primary causal broad-liquid universe;
- chronological development folds with H20 purge/embargo;
- final locked holdout began at session 1009 / `2025-07-15`.

## Stage 3 / 4 / 4B summary

- Stage 3: `STAGE3_REVIEW_PASS_FOR_BOUNDED_STAGE4_RESEARCH`;
- Stage 4: `STAGE4_RANKING_GO_CALIBRATION_BLOCKED`;
- Stage 4B: `STAGE4B_CALIBRATION_STILL_BLOCKED`;
- Probability V1 calibration rescue stopped permanently after two bounded failures.

Development HGB ranking evidence was positive but modest and did not survive the final locked holdout robustly.

## Stage 5 — final ranking holdout

Read:

- `docs/STAGE5_RANKING_HOLDOUT_PLAN_V1.md`;
- `docs/checkpoints/2026-08-09_STAGE5_RANKING_HOLDOUT_RUNTIME.md`;
- `docs/checkpoints/2026-08-09_STAGE5_INDEPENDENT_REVIEW_FAIL.md`.

Automatic result: **`STAGE5_RANKING_HOLDOUT_FAIL`**.

Primary H10:

- 71,420 resolved rows;
- base/prevalence: 0.4071688603;
- HGB PR-AUC: 0.4073793720, delta only +0.0002105118;
- HGB ROC-AUC: 0.4948433255;
- overall Q5-Q1: +0.0108405246;
- top-decile lift: +0.0251666343.

Temporal split:

- HOLDOUT_A: PR-AUC delta vs base +0.0218916273; ROC-AUC 0.5186811460; Q5-Q1 +0.0464755652;
- HOLDOUT_B: PR-AUC delta vs base -0.0105808218; ROC-AUC 0.4810497816; Q5-Q1 -0.0198933303.

Independent review accepts the FAIL. Ranking V1 is preserved only as a failed benchmark. H5/H20 are near-null sensitivities and cannot rescue V1. The consumed holdout cannot be reused as independent evidence.

## Current bounded post-mortem

The post-mortem scope was frozen **before additional diagnostics**. It asks only why A and B diverged, under five descriptive hypotheses:

1. frozen feature distribution drift;
2. feature/outcome relationship drift;
3. gradual/localized score degradation across six fixed 40/41-session blocks;
4. causal market/regime environment drift;
5. broad-ranking failure versus top-tail behavior by temporal half.

Implementation added on this branch:

- `docs/STAGE5_POSTMORTEM_PLAN_V1.md`;
- `src/idx_trade/stage5_postmortem.py`;
- `tests/test_stage5_postmortem.py`.

The runner is read-only with respect to market/model artifacts. It requires the exact consumed Stage-5 summary and prediction hashes, exact signal panel/security master, and the durable consumed-holdout marker. It does **not** fit or select a model, change features, alter labels, search thresholds, or recalibrate probability.

Required external outputs are descriptive CSV/JSON artifacts only and must be hashed. After one factual post-mortem runtime, stop for ChatGPT interpretation before any Ranking V2 design is frozen.

Post-mortem runtime result:

- status: **`DESCRIPTIVE_DIAGNOSTIC_COMPLETE`**;
- substantive code commit: `f51f9778a6657b52752d2423dbde8499c693bf70`;
- resolved H10 rows: 71,420 across 12 frozen features;
- largest absolute A/B feature SMDs: `atr14_over_close` 0.5584,
  `security_age_sessions_exact` 0.5538, `distance_low_60_atr` -0.4936,
  `observed_session_count` 0.3902, and `close_return_20` -0.2277;
- factual Q5-Q1 sign reversals: `atr14_over_close`,
  `log_regular_value_relative_20`, `observed_session_count`,
  `relative_volume_20`, and `security_age_sessions_exact`;
- six fixed blocks show positive HGB PR-AUC deltas in A1/A2/A3 and near-zero
  B1, then negative deltas in B2/B3;
- output directory:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\stage5_postmortem_v1_20260809`;
- summary SHA-256:
  `9f6c60ea3602673ad500adc99def8b1ecdfb7006c47c750dd52b2cf89984cad1`.

These are descriptive post-mortem findings only. They do not validate a
feature, regime, subgroup, cutoff, or Ranking V2 architecture.

## Authorization boundary

Allowed next action: independent ChatGPT interpretation of the completed
bounded post-mortem artifacts.

Do not:

- rerun Stage 5;
- rescue/tune V1 against consumed outcomes;
- start Stage 6;
- implement Ranking V2 before post-mortem review;
- resume Probability V1 calibration;
- validate Ranking/Probability V2 on the consumed holdout;
- run `IDX-VAL-002`;
- make execution-PnL claims;
- paper/live trade;
- merge to `main`.

Any future Ranking V2 and Probability V2 require fresh forward independent evaluation strictly after `2026-07-31`.
