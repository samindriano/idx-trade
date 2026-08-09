# IDX Trade — Current Status

Date: 2026-08-09 (Asia/Jakarta)

This is the short first-read status layer. For full chronology read
`docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest
checkpoint.

## Current phase

- active branch: `research/idx-stage5-ranking-holdout-v1`
- parent branch: `research/idx-stage4b-calibration-v1`
- Stage-5 PR: #7, draft
- phase: **Stage 5 — one-shot ranking-only locked holdout, implementation ready**
- locked holdout: **still untouched at this checkpoint**
- `holdout_outcome_accessed=false`
- Probability V1: **`PROBABILITY_V1_NOT_READY_DEFERRED`**
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

## Frozen V1 research semantics

Stage 2: `STAGE2_SPEC_GO`.

- signal after session-t close
- reference = `Close_t`
- primary H10 first-touch barrier
- ATR14
- SL = 1.0 ATR
- TP = 1.5 x SL distance
- same-bar ambiguity is not guessed
- primary causal broad-liquid universe
- F1/F2/F3 chronological walk-forward
- H20 purge/embargo
- final 252-session holdout starts session 1009 / `2025-07-15`

## Stage 3 — development ranking

Decision: **`STAGE3_REVIEW_PASS_FOR_BOUNDED_STAGE4_RESEARCH`**.

HGB development PR-AUC:

| fold | base | momentum | logistic | HGB |
|---|---:|---:|---:|---:|
| F1 | 0.3876 | 0.3994 | 0.3962 | 0.4137 |
| F2 | 0.4140 | 0.4098 | 0.4169 | 0.4254 |
| F3 | 0.3253 | 0.3289 | 0.3502 | 0.3649 |

HGB beat base-rate and momentum in F1/F2/F3. Evidence is positive but modest.

## Stage 4 — robustness / attribution / static calibration

Automatic result: **`STAGE4_RANKING_GO_CALIBRATION_BLOCKED`**.

- HGB ranking advancement reproduced in F1/F2/F3;
- Q5 > Q1 in all three folds;
- STRUCTURE was the largest ablation contributor, followed by MOMENTUM;
- static NATIVE / PLATT / ISOTONIC calibration did not beat the probability
  quality gate;
- F3 showed large prevalence/calibration drift while retaining ranking signal.

## Stage 4B — causal calibration-only iteration

Automatic result: **`STAGE4B_CALIBRATION_STILL_BLOCKED`**.

Primary `ISOTONIC_PRIOR_SHIFT_60` remained worse than static base-rate on pooled
Brier/ECE and improved prevalence gap in 0/3 folds. All causal audits were clean.
The holdout remained untouched.

Independent decision after Stage 4B:

- stop calibration rescue for V1;
- freeze `PROBABILITY_V1_NOT_READY_DEFERRED`;
- because PR-AUC is the preregistered primary dimension, allow exactly one
  locked-holdout test of the already-frozen ranking architecture;
- any future Probability V2 must use fresh forward validation strictly after
  `2026-07-31` once the current holdout is consumed.

## Stage 5 — ready, not yet executed

Read `docs/STAGE5_RANKING_HOLDOUT_PLAN_V1.md`.

Frozen mechanics:

- final development ranking-model signal cutoff: session 988;
- sessions 989–1008 are the H20 purge/buffer before holdout;
- final rankers: BASE_RATE, MOMENTUM_20, LOGISTIC_COMPACT, HGB_FULL;
- all models must be serialized and hashed before any holdout labels are read;
- primary H10 holdout signals: sessions 1009–1250;
- H5/H20 are sensitivity-only;
- two predeclared H10 halves: 1009–1129 and 1130–1250;
- primary gate is ranking-only: PR-AUC, ROC-AUC, Q5 vs Q1 and temporal halves;
- no Brier/ECE/calibrated probability claim in Stage 5.

One-shot safety:

- before holdout outcomes are read, the runner writes a durable global marker
  `STAGE5_RANKING_V1_HOLDOUT_ACCESS_STARTED.json` beside the immutable panel;
- if that marker exists, future Stage-5 runs fail closed even if another output
  directory is supplied;
- a failure after marker creation means the holdout is conservatively treated
  as consumed and must not be rerun automatically.

Implementation review:

- latest pre-runtime CI: **206 passed, 0 failed**;
- remaining warnings are existing pandas/NumPy deprecation/future warnings;
- all upstream hashes, numerical environment, model-freeze ordering, and
  one-shot marker semantics are fail-closed.

Next action: one execution-only local runtime of
`python -m idx_trade.stage5_ranking_holdout`, then stop for independent review.
