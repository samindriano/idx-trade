# Handoff
from: EXPERIMENT / LOCAL RUNTIME EXECUTION
to: MAIN / ChatGPT REVIEW
task_id: IDX-STAGE4B-CALIBRATION-RUNTIME
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: 607fc8045711892960bad68135da842289222700
branch: research/idx-stage4b-calibration-v1
head_commit: pending documentation commit
scope: Execute the frozen Stage-4B causal prior-shift calibration runtime against exact existing Stage-3/Stage-4 artifacts only.
files_changed: docs/CURRENT_STATUS.md; docs/PROJECT_LEDGER.md; docs/checkpoints/2026-08-09_STAGE4B_CALIBRATION_RUNTIME.md; coordination/handoffs/IDX-STAGE4B-CALIBRATION-RUNTIME.md
findings: Full pytest passed 198/198 with three existing pandas/NumPy warnings. Numerical versions matched Stage 3/4 exactly. All frozen input hashes and parent holdout guards matched. The runtime completed once with automatic status STAGE4B_CALIBRATION_STILL_BLOCKED. ISOTONIC_PRIOR_SHIFT_60 beat CAUSAL_PRIOR_ONLY_60 on pooled Brier but failed static base-rate, static isotonic, pooled ECE, and prevalence-gap gates. All 60- and 126-session causal prior audits passed; each had 378 dates, exact t-10 maturity, and zero source-after-cutoff rows.
decisions_made: Keep the Stage-4B primary decision blocked. Treat the 126-session result as sensitivity-only. Do not change the prior window, use future labels, refit HGB, tune, or reinterpret the result as holdout evidence.
decisions_needed: Independent ChatGPT review of whether this bounded prior-shift hypothesis is rejected or whether a separately authorized research iteration is warranted. Runtime status never authorizes holdout access or Stage 5.
blocking_risks: Primary 60-session shift remains worse than static base-rate and static isotonic on pooled Brier, worse than static base-rate on pooled ECE, and improves prevalence gap in zero folds. Holdout remains locked and strict execution-grade Open history remains incomplete.
validation_run: Python 3.13.5; NumPy 2.4.2; pandas 2.3.3; pyarrow 23.0.1; scikit-learn 1.8.0; seed 42; python -m pytest => 198 passed, 0 failed; all six external Stage-4B artifact hashes verified against the runner summary.
recommended_next_action: Review the pushed checkpoint and external artifact hashes. Stop; do not start Stage 5, inspect the locked holdout, run IDX-VAL-002, tune, use external data, or merge to main without a separate authorization.
