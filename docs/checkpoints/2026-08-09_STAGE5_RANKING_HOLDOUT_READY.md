# Stage-5 V1 Ranking Holdout — Ready for One-Shot Runtime

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage5-ranking-holdout-v1`
Parent factual runtime: Stage-4B final commit `92d5f6c03a2f266bd613db2b1cb6e210a28e0715`

## Decision

**`STAGE5_RANKING_HOLDOUT_IMPLEMENTATION_READY`**

This checkpoint authorizes exactly one execution of the frozen Stage-5
**ranking-only** locked holdout. It does not pre-judge PASS/MIXED/FAIL and does
not authorize paper/live trading, execution-PnL, Probability V2 development,
`IDX-VAL-002`, or main merge.

## Why Stage 5 is ranking-only

Stage 3/4 produced positive but modest ranking evidence:

- HGB beat base-rate and momentum PR-AUC in F1/F2/F3;
- Q5 > Q1 in F1/F2/F3;
- structure and momentum are the clearest feature-family contributors.

Probability research did not pass:

- Stage 4: `STAGE4_RANKING_GO_CALIBRATION_BLOCKED`;
- Stage 4B: `STAGE4B_CALIBRATION_STILL_BLOCKED`;
- static and causal prior-shift probability candidates did not beat the frozen
  proper-score / calibration gate.

Further calibrator search before holdout would be post-hoc rescue. Therefore:

`PROBABILITY_V1_NOT_READY_DEFERRED`

is frozen, while the preregistered primary ranking question receives one
independent holdout test.

## Frozen inputs

- SIGNAL_RESEARCH panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- research manifest SHA-256:
  `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`
- official 1,260-session calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Stage-4B runtime summary SHA-256:
  `f9cbce089c21debd6420943ebf5cd647fc41942e4f210964ddbb5d165d10ebb7`

Stage-4B parent must remain:

- decision = `STAGE4B_CALIBRATION_STILL_BLOCKED`;
- `holdout_outcome_accessed=false`.

## Frozen boundaries

- locked holdout begins session 1009 / `2025-07-15`;
- final development refit signal cutoff = session 988;
- sessions 989–1008 = H20 purge/buffer;
- primary H10 holdout signals = sessions 1009–1250;
- H5 sensitivity = 1009–1255;
- H20 sensitivity = 1009–1240;
- temporal halves are fixed at 1009–1129 and 1130–1250.

## Frozen models and metrics

Final rankers are fixed before holdout access:

- BASE_RATE;
- MOMENTUM_20;
- LOGISTIC_COMPACT;
- HGB_FULL.

HGB_FULL uses the exact frozen Stage-3 feature registry and tree
hyperparameters. No ablated feature subset, calibrator, new model, external
data, threshold, label, RR, ATR, horizon, or universe change is allowed.

Stage-5 primary metrics are ranking-only:

- PR-AUC;
- ROC-AUC;
- Q1–Q5 / top-decile ranking diagnostics;
- two predeclared temporal halves.

Probability proper scores are deliberately not part of this gate.

## One-shot ordering and durable lock

The runtime is valid only in this order:

1. verify environment and all frozen input hashes;
2. verify the global holdout marker does not exist;
3. read development data only;
4. build final development features / labels;
5. fit final rankers;
6. serialize and SHA-256 hash models + training table;
7. write `stage5_preholdout_model_freeze.json`;
8. write durable global
   `STAGE5_RANKING_V1_HOLDOUT_ACCESS_STARTED.json` beside the immutable panel,
   plus a local mirror in the output directory;
9. only then read/generate holdout outcomes.

The global marker blocks a second invocation even with a new output directory.
If the process fails after marker creation, the holdout is conservatively
considered consumed. Do not automatically rerun it.

## Implementation review

Latest substantive Stage-5 code/test CI before this documentation checkpoint:

- **206 passed, 0 failed**;
- 15 existing pandas/NumPy deprecation/future warnings;
- the initial Stage-5 fixture warning flood was removed;
- runner CLI is imported by tests;
- final refit boundary and holdout halves are regression-tested;
- ranking decision PASS/MIXED/FAIL logic is regression-tested;
- model-freeze-before-label guard is regression-tested;
- global one-shot marker path is regression-tested.

## Holdout status at this checkpoint

- holdout has **not** been opened;
- `holdout_outcome_accessed=false`;
- `holdout_consumed=false`;
- Probability V1 remains disabled.

## Next action

Execute the frozen local Stage-5 runner exactly once. After factual output is
written, stop for independent review regardless of whether the automatic result
is PASS, MIXED, FAIL, or BLOCKED.

If ranking passes, the natural next phase is forward shadow evaluation of the
ranking architecture; Probability V2 remains a separate future architecture
requiring fresh forward validation after `2026-07-31`.
