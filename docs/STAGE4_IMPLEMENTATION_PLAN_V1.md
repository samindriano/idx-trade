# Stage 4 Implementation Plan V1

Status: **FROZEN BEFORE REAL STAGE-4 RUNTIME**
Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage4-v1`
Parent: reviewed Stage-3 runtime on `research/idx-stage3-v1`

## Runtime inputs

Stage 4 consumes only already-created Stage-3 development artifacts plus the frozen official calendar. It does not read the full raw market panel.

Required exact inputs:

- Stage-3 primary model table:
  `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189`
- Stage-3 development feature table:
  `f16d77caa6642d0aba8c0a39eda5b2d32e53f17717b149f5f0637eeacac80772`
- Stage-3 runtime summary:
  `979c56be43e2fdc5c0502e1b1625d74dbcab6ba28f097338575479739baa029f`
- exact official 1260-session calendar used by Stage 3.

The Stage-3 summary must prove `holdout_outcome_accessed=false` and holdout start index 1009.

## Environment reproducibility

The real Stage-4 runtime must use the same numerical environment as the successful Stage-3 runtime unless an explicit reproducibility review approves otherwise:

- Python 3.13.5
- NumPy 2.4.2
- pandas 2.3.3
- pyarrow 23.0.1
- scikit-learn 1.8.0
- random seed 42

If the local environment differs, STOP before running real Stage-4 outcomes. Do not silently upgrade/downgrade and compare the result as if it were the same experiment.

GitHub CI may use a different supported dependency version for regression testing; CI success proves implementation compatibility, not numerical parity with the Stage-3 runtime.

## Model and calibration mapping

### Reference ranking model

`HGB_FULL` uses exactly the Stage-3 HGB configuration:

- learning rate 0.05
- max iterations 200
- max leaf nodes 31
- L2 regularization 1.0
- seed 42
- training-only median imputation with missing indicators

No hyperparameter search.

### Ablation probability diagnostics

All HGB feature-family ablations use **Platt calibration** fitted on the same chronological calibration tail used by Stage 3.

Reason: attribution should vary the feature family only. It must not confound a feature removal with a different probability mapping.

Primary attribution metric remains PR-AUC; Brier/ECE are diagnostics.

### Regime probability diagnostics

Regime diagnostics also use `HGB_FULL + PLATT`, matching the Stage-3 reference probability architecture.

Regimes never enter model fitting as Stage-4 features.

### Calibration experiment

Only the calibration block compares:

- `NATIVE`
- `PLATT`
- `ISOTONIC`

All three use the identical `HGB_FULL` ranking model fit. Only the probability mapping changes.

## Fold boundaries

Reuse exactly F1/F2/F3 and the existing chronological internal split:

`model-fit -> H20 maturity gap -> calibration tail -> outer H20 gap -> validation`

No random split.

No signal or source row from the locked holdout may be loaded.

## Cross-sectional quintiles

Quintiles are assigned within each validation signal date from `HGB_FULL` raw score.

Tie/order handling is deterministic using raw score then ticker.

This diagnostic is ranking-only and has no execution threshold.

## Regime thresholds

For each outer fold independently:

- compute daily cross-sectional metrics from all primary-liquid feature rows;
- derive tertile cut points from fold training dates only;
- apply the frozen training thresholds to validation dates.

Resolved future labels are not used to construct the regime metric or its threshold.

## Output policy

Runtime output is outside Git. Git may contain only factual documentation/checkpoints/handoffs after the run.

Expected Stage-4 runtime outputs include:

- reference fold metrics;
- reference pooled metrics;
- ablation fold metrics and OOF predictions;
- feature attribution table;
- cross-sectional quintile rows and summary;
- calibration fold/pooled metrics and OOF predictions;
- regime thresholds and regime metrics;
- summary JSON with input/spec hashes and `holdout_outcome_accessed=false`.

## Review boundary

The runner's automatic status is not permission to inspect the final holdout.

After runtime, independent ChatGPT review must inspect:

- reproduction of Stage-3 ranking evidence;
- quintile ordering;
- attribution consistency;
- weak/adverse regime slices;
- selected calibrator and probability-quality gate;
- artifact hashes and holdout proof.

Only a later explicit Stage-5 authorization may open the locked holdout.
