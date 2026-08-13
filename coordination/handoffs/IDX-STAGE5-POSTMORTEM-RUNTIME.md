# Handoff
from: MAIN / ChatGPT REVIEW
to: EXPERIMENT / LOCAL RUNTIME EXECUTION
task_id: IDX-STAGE5-POSTMORTEM-RUNTIME
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: f51f9778a6657b52752d2423dbde8499c693bf70
branch: research/idx-stage5-postmortem-v1
head_commit: verify latest remote branch HEAD before execution; no production-code change is authorized after `f51f9778a6657b52752d2423dbde8499c693bf70`
scope: Execute the frozen bounded descriptive Stage-5 post-mortem once against the already-consumed Stage-5 artifacts.
files_changed: docs/STAGE5_POSTMORTEM_PLAN_V1.md; src/idx_trade/stage5_postmortem.py; tests/test_stage5_postmortem.py; docs/CURRENT_STATUS.md; docs/checkpoints/2026-08-09_STAGE5_POSTMORTEM_READY.md
findings: Stage-5 Ranking V1 failed overall ROC and temporal stability. Post-mortem scope is frozen to feature drift, feature/outcome relation drift, six fixed temporal blocks, market/regime drift, and HGB deciles by half.
decisions_made: No model/feature/label/threshold/calibration search is permitted. Consumed holdout is diagnostic research data only. Ranking V1 remains rejected and Probability V1 remains deferred.
decisions_needed: After factual runtime, ChatGPT independently interprets the fixed diagnostics and decides which, if any, V2 hypotheses deserve a separately frozen development plan.
blocking_risks: Do not treat any post-hoc subgroup or feature as independently validated. Do not rerun Stage 5. Do not use this holdout as V2 validation.
validation_run: GitHub CI on substantive code commit f51f9778a6657b52752d2423dbde8499c693bf70 -> 211 passed, 0 failed, 15 pre-existing warning instances/classes; post-mortem fixture warning flood removed.
recommended_next_action: Resolve the exact existing local Stage-5 input artifacts by path/hash, run `python -m idx_trade.stage5_postmortem` once into a new empty output directory, preserve all CSV/JSON artifacts, document factual results only, and STOP for ChatGPT review. No V2 implementation in the same run.

## Local runtime constraints

Use the exact Stage-3/4/5 numerical environment:

- Python 3.13.5
- NumPy 2.4.2
- pandas 2.3.3
- pyarrow 23.0.1
- scikit-learn 1.8.0

Known exact paths:

- signal panel:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`
- Stage-5 predictions:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\stage5_ranking_holdout_v1_20260809\stage5_h10_ranking_holdout_predictions.parquet`
- Stage-5 summary:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\stage5_ranking_holdout_v1_20260809\stage5_ranking_holdout_summary.json`

Resolve the exact calendar and security-master paths from the preserved Stage-5 inputs/command or the same frozen research artifacts. Do not recreate, redownload, substitute, or guess them. Required hashes:

- calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- security master: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`

Required consumed Stage-5 hashes:

- predictions: `9d850776c98c07e069b32d606ad510d94a26435659da86997f5302d765d8ee8c`
- summary: `1a38171eead5a9c72de62da4f6ef486f35e3fba2e962c3b0bccac9fea033acd0`

Recommended new output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\stage5_postmortem_v1_20260809`

Run:

```text
python -m idx_trade.stage5_postmortem ^
  --panel "<EXACT_PANEL_PATH>" ^
  --calendar "<EXACT_CALENDAR_PATH>" ^
  --security-master "<EXACT_SECURITY_MASTER_PATH>" ^
  --stage5-predictions "<EXACT_STAGE5_PREDICTIONS_PATH>" ^
  --stage5-summary "<EXACT_STAGE5_SUMMARY_PATH>" ^
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\stage5_postmortem_v1_20260809" ^
  --code-commit "f51f9778a6657b52752d2423dbde8499c693bf70"
```

If admission/hash/environment/input resolution fails, STOP and report. A pure implementation bug may be reviewed because this phase does not create a new independent holdout, but do not change diagnostic semantics after seeing partial diagnostic outcomes.

After successful runtime, report all fixed-block rows, all feature-drift rows sorted by absolute SMD, all feature relation rows with A/B side-by-side, all A/B regime summaries, both decile curves, artifact hashes, and summary SHA. Do not recommend or implement V2; stop for ChatGPT review.