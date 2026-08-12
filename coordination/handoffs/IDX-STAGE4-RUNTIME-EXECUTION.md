# Handoff
from: MAIN / ChatGPT REVIEW
to: EXPERIMENT / LOCAL RUNTIME EXECUTION
task_id: IDX-STAGE4-RUNTIME-EXECUTION
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: idx-trade
source_commit: `7e1e75b9bc68464c85910363c12d129b8d691142`
branch: `research/idx-stage4-v1`
head_commit: verify remote HEAD before execution
scope: Execute the frozen Stage-4 V1 development-only runner against the exact Stage-3 development artifacts. No redesign or holdout access.
files_changed: runtime artifacts outside Git; after factual completion update only continuity/checkpoint/handoff documentation.
findings: Stage 3 passed the pre-registered ranking advancement rule but probability calibration was not ready. Stage 4 design/code is frozen to feature-family attribution, within-date ranking diagnostics, causal regime diagnostics, and HGB calibration comparison limited to NATIVE/PLATT/ISOTONIC.
decisions_made: Keep H10/ATR14/SL1.0/RR1.5/universe/folds/H20 gaps/HGB hyperparameters unchanged. Ablation and regime probability diagnostics use Stage-3 Platt reference. Calibration comparison changes only the probability mapping of HGB_FULL. Locked holdout remains inaccessible.
decisions_needed: After runtime, independent ChatGPT review decides whether status is ranking+calibration freeze ready, ranking-go/calibration-blocked, or ranking review required. Automatic runner status does not authorize Stage 5.
blocking_risks: Wrong Stage-3 artifact hash, numerical-environment drift, locked-holdout access, non-finite metrics, schema drift, or any attempt to tune after seeing Stage-4 outcomes must stop the task.
validation_run: GitHub CI for Stage-4 code/tests passed 192 tests, 0 failed before the final documentation-only checkpoint. Re-run full local pytest before real runtime.
recommended_next_action: Verify exact Stage-3 artifact hashes and Stage-3 numerical environment, run `python -m idx_trade.stage4_development` once into a new external output directory, document factual outputs, push documentation only, and stop for ChatGPT review.

## Exact runtime inputs

- primary model table SHA-256: `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189`
- development feature table SHA-256: `f16d77caa6642d0aba8c0a39eda5b2d32e53f17717b149f5f0637eeacac80772`
- Stage-3 runtime summary SHA-256: `979c56be43e2fdc5c0502e1b1625d74dbcab6ba28f097338575479739baa029f`
- exact Stage-3 official 1260-session calendar

## Required numerical environment

- Python 3.13.5
- NumPy 2.4.2
- pandas 2.3.3
- pyarrow 23.0.1
- scikit-learn 1.8.0
- seed 42

If different: STOP before model execution.

## Runtime prohibitions

No holdout inspection, no hyperparameter tuning, no feature additions, no label/universe changes, no external data, no synthetic Open, no execution-PnL claim, no Stage 5, no `IDX-VAL-002`, no paper/live trading, and no merge to `main`.
