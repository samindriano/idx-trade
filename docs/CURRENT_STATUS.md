# IDX Trade — Current Status

Date: 2026-08-09 (Asia/Jakarta)

This is the short **authoritative first-read status layer**. For full chronology read
`docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest
checkpoint. If an older "current stage" paragraph in the long-lived master or
ledger conflicts with this file, this file plus the newest dated checkpoint
controls the current phase and authorization boundary.

## Current phase

- active branch: `research/idx-stage5-ranking-holdout-v1`
- parent branch: `research/idx-stage4b-calibration-v1`
- Stage-5 PR: #7, draft
- phase: **Stage 5 completed, FAIL; independent review accepts Ranking V1 rejection**
- locked holdout: **consumed for `RANKING_V1_ONLY`; no retry permitted**
- `holdout_outcome_accessed=true`
- Ranking V1: **failed benchmark; not authorized for promotion to Stage 6**
- Probability V1: **`PROBABILITY_V1_NOT_READY_DEFERRED`**
- next authorized scope: **bounded Stage-5 post-mortem / Ranking V2 research design only**
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

HGB beat base-rate and momentum in F1/F2/F3. Evidence was positive but modest and did not survive the final locked holdout robustly.

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

## Stage 5 — ranking-only holdout executed, failed

Read `docs/STAGE5_RANKING_HOLDOUT_PLAN_V1.md` and
`docs/checkpoints/2026-08-09_STAGE5_INDEPENDENT_REVIEW_FAIL.md`.

Frozen mechanics:

- final development ranking-model signal cutoff: session 988;
- sessions 989–1008 are the H20 purge/buffer before holdout;
- final rankers: BASE_RATE, MOMENTUM_20, LOGISTIC_COMPACT, HGB_FULL;
- all models were serialized and hashed before any holdout labels were read;
- primary H10 holdout signals: sessions 1009–1250;
- H5/H20 are sensitivity-only;
- two predeclared H10 halves: 1009–1129 and 1130–1250;
- primary gate is ranking-only: PR-AUC, ROC-AUC, Q5 vs Q1 and temporal halves;
- no Brier/ECE/calibrated probability claim in Stage 5.

Runtime result:

- automatic decision: **`STAGE5_RANKING_HOLDOUT_FAIL`**;
- runtime code commit: `05c2bb549b446da374c13937a41aa6732cf71ec0`;
- H10 holdout: 71,420 resolved primary rows, positive rate 0.4071688603;
- HGB PR-AUC: 0.4073793720 versus base 0.4071688603, delta only +0.0002105118;
- HGB ROC-AUC: 0.4948433255, below the frozen 0.5 gate;
- overall Q5-Q1: +0.0108405246;
- top-decile lift: +0.0251666343;
- HOLDOUT_A: PR-AUC delta vs base +0.0218916273, ROC-AUC 0.5186811460, Q5-Q1 +0.0464755652;
- HOLDOUT_B: PR-AUC delta vs base -0.0105808218, ROC-AUC 0.4810497816, Q5-Q1 -0.0198933303;
- H5/H20 sensitivity remained near-null and cannot rescue H10;
- the holdout is permanently consumed for `RANKING_V1_ONLY`;
- output: `D:\Documents\Project\idx-trade-data-gate-20260808v\stage5_ranking_holdout_v1_20260809`.

Independent review conclusion:

- accept the preregistered FAIL; do not relax the gate after seeing outcomes;
- Ranking V1 is preserved as a **failed benchmark**, not a holdout-passed architecture;
- the divergence between HOLDOUT_A and HOLDOUT_B is evidence of temporal instability, not merely a lower prevalence period, because PR-AUC-vs-base, ROC-AUC, and Q5-Q1 all reverse in B;
- the positive overall top-decile enrichment is only a V2 hypothesis and does not rescue V1;
- no Stage 6 promotion for V1;
- post-hoc use of the consumed holdout is allowed only for bounded diagnosis/V2 hypothesis generation and can never restore independent validation status.

One-shot safety:

- before holdout outcomes were read, the runner wrote a durable global marker
  `STAGE5_RANKING_V1_HOLDOUT_ACCESS_STARTED.json` beside the immutable panel;
- if that marker exists, future Stage-5 runs fail closed even if another output
  directory is supplied;
- both global and local markers were written before holdout labels were read;
- the successful runtime therefore consumed the holdout and must not be rerun.

Implementation review:

- runtime/full pytest: **206 passed, 0 failed**;
- remaining warnings are existing pandas FutureWarnings;
- all upstream hashes, numerical environment, model-freeze ordering, and
  one-shot marker semantics passed.

## Next authorization boundary

Authorized next scope is only a bounded **Stage-5 post-mortem / Ranking V2 research-design** phase. Priority diagnostic questions are why HOLDOUT_A and HOLDOUT_B diverged and whether the apparent top-tail enrichment reflects a causal conditional signal or noise. Candidate V2 hypotheses may include date-relative/cross-sectional normalization, market/sector relative strength, explicit regime conditioning, ranking-native objectives grouped by signal date, and stronger causal support/resistance representations.

Do not repeatedly search alternatives on the consumed Stage-5 outcomes. Any Ranking V2 and any Probability V2 require a **fresh forward evaluation period strictly after `2026-07-31`** for independent validation.

Do not start the previously defined Stage 6, rerun Stage 5, resume Probability V1 calibration rescue, run `IDX-VAL-002`, make execution-PnL claims, paper/live trade, or merge to `main` without a new explicit gate.
