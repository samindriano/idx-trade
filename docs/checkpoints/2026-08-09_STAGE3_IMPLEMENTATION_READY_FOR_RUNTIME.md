# Stage 3 implementation ready for bounded development runtime

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage3-v1`
Base: approved `STAGE2_SPEC_GO` on `data/idx-data-002c`

## Decision

**STAGE3_IMPLEMENTATION_READY_FOR_RUNTIME**

The Stage-3 causal label, feature, temporal-validation, calibration, baseline,
reporting, and bounded runtime paths are implemented and regression-tested.
No real development outcome from the immutable 981,940-row research panel has
been inspected by this checkpoint.

The next action is a bounded local execution against the already-created
`SIGNAL_RESEARCH_HLCV` runtime artifacts. This requires local filesystem access
to the external research workspace and is not a reason to redesign the Stage-3
pipeline.

## Immutable input contract

- exact research window: `2021-04-29 -> 2026-07-31`, 1,260 official IDX sessions;
- research panel rows: 981,940;
- panel SHA-256:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- research manifest SHA-256:
  `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a`;
- manifest baseline: valid=true, 15/15 artifacts;
- strict execution-grade 1260 remains FAIL;
- `SIGNAL_RESEARCH_HLCV` remains GO.

## Implemented Stage-3 modules

- `src/idx_trade/research_labels.py`
  - causal ATR14 first-touch barrier labels;
  - primary H=10, `k_sl=1.0`, RR=1.5;
  - explicit TP_FIRST / SL_FIRST / AMBIGUOUS_SAME_BAR /
    NO_BARRIER_HIT / UNRESOLVED_PATH / UNRESOLVED_HORIZON_END /
    INVALID_BARRIER;
  - H5/H20 sensitivity support;
  - hard signal/future official-session access boundaries.

- `src/idx_trade/research_features.py`
  - frozen compact causal feature family;
  - exact-session liquidity history rule;
  - causal top-100/top-300 sensitivity ranks;
  - Open prohibited from primary feature registry;
  - pre-window security age is not fabricated: exact in-window age or explicit
    left-censored missingness only.

- `src/idx_trade/research_validation.py`
  - exact frozen 1,260-calendar boundary assertions;
  - F1/F2/F3 definitions;
  - H=20 purge/embargo assertions;
  - chronological 80/20 fit/calibration split with H=20 maturity gap;
  - hard holdout-access and label-overlap rejection.

- `src/idx_trade/research_baselines.py`
  - base-rate baseline;
  - fixed 20-observation momentum baseline;
  - compact logistic baseline;
  - bounded HistGradientBoosting challenger;
  - training-only imputation/scaling;
  - chronological Platt calibration;
  - PR-AUC / ROC-AUC / Brier / ECE.

- `src/idx_trade/research_reporting.py`
  - candidate coverage by date;
  - explicit primary drop-reason ledger;
  - reliability bins;
  - pooled out-of-fold metrics;
  - MFE/MAE/normalized-return/research-R summaries;
  - fold-boundary audit.

- `src/idx_trade/stage3_development.py`
  - hash-checks frozen panel;
  - hash-checks and re-verifies frozen signal-research manifest;
  - hashes frozen Stage-2/Stage-3 specification documents;
  - records dependency versions and seed;
  - requires Parquet filter and refuses unfiltered panel fallback;
  - reads at most signal session 942 and future source session 962;
  - locked holdout begins at 1009 and is therefore physically outside the
    permitted development read boundary;
  - writes deterministic development artifacts and their SHA-256 hashes;
  - records `holdout_outcome_accessed=false`.

## Frozen baseline parameters

See `docs/STAGE3_IMPLEMENTATION_PLAN_V1.md`.

Primary label:

- H=10;
- ATR14 simple mean;
- SL=`1.0 * ATR14`;
- TP=`1.5 * SL distance`;
- reference=`Close_t`, label reference only.

Models:

- Logistic Regression: C=1.0, lbfgs, max_iter=1000, seed=42;
- HistGradientBoosting: learning_rate=0.05, max_iter=200,
  max_leaf_nodes=31, l2_regularization=1.0, seed=42;
- no hyperparameter search.

## Validation result before real runtime

GitHub Actions on the implementation PR passed:

- **184 tests passed**;
- **0 tests failed**;
- warnings are existing pandas/NumPy deprecation/future warnings and are not
  Stage-3 gate failures.

Synthetic regression tests cover barrier ordering, ambiguity, path gaps,
horizon/access bounds, causal-feature future invariance, liquidity windows,
left-censored age, frozen fold boundaries, purge overlap, holdout rejection,
baseline execution, runtime admission helpers, candidate/drop reporting,
reliability bins, and pooled OOF aggregation.

## Runtime boundary

The immutable panel and related runtime artifacts are outside Git under the
existing local research workspace. GitHub-only review cannot execute the real
folds without those files.

The next task must therefore be execution-only:

1. use this exact branch/head after CI success;
2. do not redownload market data;
3. do not change label/universe/model parameters after seeing outcomes;
4. locate the exact frozen panel, manifest, calendar, and security master from
   the existing 1260 research workspace;
5. run full pytest locally;
6. run `python -m idx_trade.stage3_development ...` once for the frozen
   development folds;
7. preserve runtime outputs outside Git;
8. report outcome prevalence, ambiguity/unresolved rates, primary-universe
   coverage, F1/F2/F3 and pooled OOF metrics, calibration diagnostics, and the
   pre-registered advancement decision;
9. do not inspect the locked holdout;
10. stop for independent ChatGPT review before any Stage-4 decision.

## Permanent prohibitions

No main merge, no `IDX-VAL-002`, no locked-holdout inspection, no execution-PnL
claim, no Open synthesis, no label/barrier/liquidity threshold rescue after
seeing V1 development results, and no Stage-4 modelling expansion in the same
runtime task.
