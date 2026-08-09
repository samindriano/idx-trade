# IDX Trade — Current Status

Date: 2026-08-09 (Asia/Jakarta)

This is the short first-read status layer. For full chronology read `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, and the newest checkpoint.

## Current phase

- active branch: `research/idx-stage4b-calibration-v1`
- parent Stage-4 branch: `research/idx-stage4-v1`
- Stage-4B PR: #6, draft, base `research/idx-stage4-v1`
- phase: **Stage 4B — bounded causal calibration research**
- locked holdout: **untouched**
- `holdout_outcome_accessed=false`
- Stage 5: not authorized
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
- final 252-session holdout locked from session 1009 / `2025-07-15`

## Stage 3 result

`STAGE3_REVIEW_PASS_FOR_BOUNDED_STAGE4_RESEARCH`.

HGB development PR-AUC:

| fold | base | momentum | logistic | HGB |
|---|---:|---:|---:|---:|
| F1 | 0.3876 | 0.3994 | 0.3962 | 0.4137 |
| F2 | 0.4140 | 0.4098 | 0.4169 | 0.4254 |
| F3 | 0.3253 | 0.3289 | 0.3502 | 0.3649 |

HGB beat base-rate and momentum in F1/F2/F3. Ranking evidence is positive but modest; calibration was not yet trustworthy.

## Stage 4 result

Runtime code: `ad2098c7932a187555ac7c9ec8b77372bdf622e5`.

Automatic result: **`STAGE4_RANKING_GO_CALIBRATION_BLOCKED`**.

Key evidence:

- pytest 192/192;
- HGB ranking advancement reproduced in F1/F2/F3;
- within-date Q5 > Q1 in all three folds;
- structure removal mean PR-AUC delta: -0.013006;
- momentum removal mean PR-AUC delta: -0.007881;
- volatility/history/volume-liquidity were directionally supportive but much smaller in magnitude;
- selected static calibrator: ISOTONIC;
- calibration readiness failed because pooled Brier and ECE did not beat base-rate and prevalence-gap improvement occurred in only 1/3 folds;
- F3 `TREND_MID` and `VOLATILITY_HIGH` showed severe overprediction while retaining PR-AUC above prevalence.

Interpretation: ranking survives; the remaining blocker is specifically probability-level adaptation under prevalence drift. Do not describe all feature families as equally important, and do not claim fully monotonic ranking: for example F2 Q2 exceeded Q5 even though Q5 > Q1.

## Independent review decision

**`STAGE4_REVIEW_PASS_FOR_STAGE4B_CALIBRATION_ONLY`**.

Do not open the holdout. Stage 4B is allowed only as a tightly bounded calibration hypothesis prompted by the observed prevalence drift.

## Stage 4B frozen hypothesis

Read `docs/STAGE4B_CALIBRATION_PLAN_V1.md`.

Primary hypothesis:

- retain exact Stage-4 ISOTONIC OOF probabilities;
- estimate current TP-vs-SL prior from the previous 60 official signal sessions whose H10 labels are already fully mature at prediction time;
- apply deterministic prior-probability-shift correction in odds space;
- compare against both STATIC_ISOTONIC and a mandatory `CAUSAL_PRIOR_ONLY_60` baseline;
- 126 sessions is sensitivity-only and cannot rescue a failed 60-session primary hypothesis.

Frozen runtime inputs:

- Stage-3 model table SHA: `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189`
- Stage-4 calibration OOF predictions SHA: `964d3bdbb39b3069deb8328b981150a634d9c2ba780759e9294baccd2e1869b5`
- Stage-4 summary SHA: `1d904314e01c1a03b1ffce1cdb6ff5cec4be4caa8723ae0b7413927258be3155`

Implementation CI after Stage-4B code/tests: **198 passed, 0 failed**.

Stage 4B remains development-only. No HGB refit, feature change, model search, label/universe change, holdout access, external data, execution-PnL, synthetic Open, Kelly/sizing, Stage 5, `IDX-VAL-002`, or main merge is authorized.
