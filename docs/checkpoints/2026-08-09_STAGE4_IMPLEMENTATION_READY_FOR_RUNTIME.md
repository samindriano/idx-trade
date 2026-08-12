# Stage 4 implementation ready for bounded runtime

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage4-v1`
Parent: reviewed Stage-3 branch `research/idx-stage3-v1`
Draft PR: #5, base `research/idx-stage3-v1`

## Decision

**STAGE4_IMPLEMENTATION_READY_FOR_RUNTIME**

All Stage-4 V1 design and implementation work that can be completed without the external runtime artifacts is complete.

The next action is execution-only against the frozen Stage-3 development artifacts. No Stage-4 outcome has been inspected yet.

## Frozen Stage-4 objective

Stage 4 is bounded to three questions:

1. feature-family attribution;
2. chronological/cross-sectional/regime ranking stability;
3. calibration comparison restricted to NATIVE / PLATT / ISOTONIC.

No broad model search, hyperparameter tuning, label rescue, universe change, or holdout access is authorized.

## Frozen runtime inputs

Required exact SHA-256:

- Stage-3 primary model table:
  `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189`
- Stage-3 development feature table:
  `f16d77caa6642d0aba8c0a39eda5b2d32e53f17717b149f5f0637eeacac80772`
- Stage-3 runtime summary:
  `979c56be43e2fdc5c0502e1b1625d74dbcab6ba28f097338575479739baa029f`

Stage-3 summary must still prove:

- `holdout_outcome_accessed=false`;
- locked holdout starts at session 1009 / 2025-07-15.

## Frozen Stage-4 variants

HGB ranking model hyperparameters remain exactly Stage 3.

Ablation variants:

- HGB_FULL
- HGB_NO_STRUCTURE
- HGB_NO_MOMENTUM
- HGB_NO_VOLUME_LIQUIDITY
- HGB_NO_VOLATILITY
- HGB_NO_HISTORY

Ablations use the Stage-3 Platt probability mapping for probability diagnostics; primary attribution uses PR-AUC.

Calibration candidates for HGB_FULL only:

- NATIVE
- PLATT
- ISOTONIC

No other calibrator is allowed in V1.

## Diagnostics implemented

- Stage-3 reference metrics reproduction;
- HGB feature-family ablation fold metrics;
- directional feature attribution summary;
- within-date deterministic score quintiles;
- Q5-vs-Q1 ranking gate;
- causal training-derived trend tertile regimes;
- causal training-derived volatility tertile regimes;
- regime metrics with low-sample flag;
- calibration fold metrics;
- pooled OOF calibration metrics;
- frozen calibrator selection rule;
- frozen probability-readiness gate;
- explicit runtime decision state;
- artifact/spec/dependency hashes;
- `holdout_outcome_accessed=false` summary field.

## Implementation files

- `docs/CURRENT_STATUS.md`
- `docs/STAGE4_RESEARCH_PLAN_V1.md`
- `docs/STAGE4_IMPLEMENTATION_PLAN_V1.md`
- `src/idx_trade/research_stage4.py`
- `src/idx_trade/stage4_development.py`
- `tests/test_research_stage4.py`

`AGENTS.md` now routes new work through `docs/CURRENT_STATUS.md` first so stale early master-context bootstrap language cannot silently override the latest phase state.

## Validation

GitHub Actions after Stage-4 code/tests:

- **192 passed**
- **0 failed**
- existing pandas/NumPy deprecation/future warnings only

A subsequent documentation-only implementation-freeze commit also passed CI.

## Numerical environment requirement

The real Stage-4 runtime must preserve Stage-3 numerical environment:

- Python 3.13.5
- NumPy 2.4.2
- pandas 2.3.3
- pyarrow 23.0.1
- scikit-learn 1.8.0
- seed 42

If the local environment differs, STOP before real outcomes are produced.

## Runtime command

The implemented entry point is:

`python -m idx_trade.stage4_development`

It requires:

- `--model-table`
- `--feature-table`
- `--stage3-summary`
- `--calendar`
- `--output-dir`
- `--code-commit`

Runtime output must stay outside Git.

## Decision states emitted by the runner

- `STAGE4_RANKING_AND_CALIBRATION_FREEZE_READY`
- `STAGE4_RANKING_GO_CALIBRATION_BLOCKED`
- `STAGE4_RANKING_REVIEW_REQUIRED`
- runtime admission failures are treated as `STAGE4_RUNTIME_BLOCKED` operationally and must stop the run.

Regardless of automatic status, independent ChatGPT review is mandatory before any Stage-5 authorization.

## Permanent prohibitions

No locked-holdout inspection, no Stage 5, no `IDX-VAL-002`, no execution-PnL claim, no Open synthesis, no Kelly/sizing, no paper/live trade, and no merge to `main` in the Stage-4 runtime task.
