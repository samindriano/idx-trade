# IDX Trade — Current Status

Date: 2026-08-09 (Asia/Jakarta)

This file is the short first-read status layer. It overrides stale status wording in older sections of `PROJECT_CONTEXT_MASTER.md` when chronology differs. The master context remains the comprehensive history; the ledger remains the causal chronology.

## Current branch / phase

- active research branch: `research/idx-stage4-v1`
- parent Stage-3 branch: `research/idx-stage3-v1`
- Stage-3 PR: #4, draft, base `data/idx-data-002c`
- current phase: **Stage 4 — bounded model research / robustness / calibration design**
- locked holdout: **untouched**
- `holdout_outcome_accessed=false`
- `IDX-VAL-002`: not started
- merge to `main`: not authorized
- paper/live trading: not authorized

## Data status

Strict execution-grade OHLCV:

- 126 sessions: PASS
- 504 sessions: FAIL because historical Open evidence is incomplete
- 1260 sessions: FAIL for the same execution-grade reason

Signal-research HLCV:

- 1260 sessions: **GO**
- window: `2021-04-29 -> 2026-07-31`
- official IDX sessions: 1260
- required common stocks: 979
- ACTIVE research rows: 981,940
- H/L/C/Volume coverage: 100%
- nullable Open rows: 446,843; no synthetic Open
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- manifest SHA-256: `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`
- manifest: valid=true, 15/15

## Stage 2

`STAGE2_SPEC_GO`.

Frozen V1 research semantics include:

- signal timestamp after session-t close;
- `Close_t` is a signal reference, not an execution-price claim;
- primary H10 first-touch barrier label;
- ATR14 normalization;
- SL distance = 1.0 ATR;
- TP distance = 1.5x SL distance;
- ambiguous same-bar TP/SL is not guessed;
- primary broad-liquid causal universe;
- exact F1/F2/F3 chronological walk-forward;
- H20 purge/embargo protection;
- final trailing 252-session holdout locked.

## Stage 3 result

`STAGE3_RUNTIME_COMPLETE_ADVANCEMENT_RULE_MET` and independent review decision:

**STAGE3_REVIEW_PASS_FOR_BOUNDED_STAGE4_RESEARCH**.

Runtime code commit:
`4c484b087aff592234dbe9905213e9d83b2f2611`

Stage-3 development runtime:

- pytest: 184 passed, 0 failed
- full-valid H10 resolved binary rows: 512,959
  - TP_FIRST: 197,910
  - SL_FIRST: 315,049
- primary broad-liquid H10 model rows: 208,375
  - TP_FIRST: 80,038
  - SL_FIRST: 128,337
- development OOF rows: 81,365

PR-AUC by fold:

| fold | base | momentum | logistic | HGB |
|---|---:|---:|---:|---:|
| F1 | 0.3876 | 0.3994 | 0.3962 | 0.4137 |
| F2 | 0.4140 | 0.4098 | 0.4169 | 0.4254 |
| F3 | 0.3253 | 0.3289 | 0.3502 | 0.3649 |

Pooled development OOF PR-AUC:

- base rate: 0.35838
- momentum: 0.35328
- logistic compact: 0.36465
- HistGradientBoosting: 0.37435

Frozen advancement rule:

- logistic compact met on F2/F3;
- HGB met on F1/F2/F3.

Interpretation:

- there is positive but modest evidence of **ranking signal**;
- this is development OOF evidence, not final holdout evidence;
- probability calibration is not yet trustworthy: challenger Brier/ECE did not consistently beat the base-rate predictor, especially during F3 prevalence drift;
- no execution-profitability claim is valid because strict execution-grade Open history remains incomplete.

## Stage 4 authorization boundary

Stage 4 is authorized only as a bounded development-only research phase.

Its purpose is to answer three pre-specified questions before the holdout can ever be considered:

1. **Attribution:** which frozen feature families are responsible for the ranking edge?
2. **Stability:** does the edge survive across the existing chronological folds and causally defined market regimes?
3. **Calibration:** can probability quality be improved with a small pre-registered calibration family without changing labels, universe, folds, or model hyperparameters?

Stage 4 must not become a model zoo or post-hoc rescue exercise.

Permanent prohibitions during Stage 4:

- no locked-holdout inspection;
- no label/horizon/RR/ATR/universe-threshold change;
- no broad hyperparameter search;
- no AutoML;
- no new external data;
- no synthetic Open;
- no execution-PnL claim;
- no Kelly/sizing;
- no Stage 5 in the same task;
- no merge to `main`.

Read next:

1. `docs/STAGE4_RESEARCH_PLAN_V1.md`
2. newest Stage-4 checkpoint under `docs/checkpoints/`
3. `docs/PROJECT_CONTEXT_MASTER.md`
4. `docs/PROJECT_LEDGER.md`

## Stage 4 runtime result

Date: 2026-08-09 (Asia/Jakarta). Branch: `research/idx-stage4-v1`. Code head:
`ad2098c7932a187555ac7c9ec8b77372bdf622e5`.

The frozen Stage-4 development runtime completed once against the exact
Stage-3 artifacts. Numerical environment matched Stage 3 exactly and full
pytest passed **192/192**, with three existing pandas/NumPy warnings. All
input hashes matched; `holdout_outcome_accessed=false`; locked holdout starts
at index 1009 / `2025-07-15`.

Automatic result: **STAGE4_RANKING_GO_CALIBRATION_BLOCKED**. HGB reproduced
the Stage-3 advancement rule in F1/F2/F3, and the within-date quintile gate
had Q5 > Q1 in all three folds. The selected calibrator was ISOTONIC, but
calibration readiness failed: pooled Brier and weighted ECE did not beat the
base-rate comparator, and prevalence-gap improvement occurred in only 1/3
folds. No Stage 5, holdout inspection, `IDX-VAL-002`, modelling, or main merge
was started. The full factual record is in the new Stage-4 checkpoint.
