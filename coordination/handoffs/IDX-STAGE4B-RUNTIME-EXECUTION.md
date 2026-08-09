# Handoff
from: MAIN / ChatGPT REVIEW
to: EXPERIMENT / RUNTIME EXECUTION
task_id: IDX-STAGE4B-RUNTIME-EXECUTION
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: d08247d04c46562c5c8ed4348116fcf0dd9305fd
branch: research/idx-stage4b-calibration-v1
head_commit: pending latest documentation commit
scope: Execute the frozen Stage-4B causal prior-shift calibration runner against exact existing Stage-3/Stage-4 runtime artifacts only.
files_changed: docs/STAGE4B_CALIBRATION_PLAN_V1.md; src/idx_trade/research_stage4b.py; src/idx_trade/stage4b_development.py; tests/test_research_stage4b.py; docs/CURRENT_STATUS.md; docs/checkpoints/2026-08-09_STAGE4_REVIEW_STAGE4B_READY.md; coordination/handoffs/IDX-STAGE4B-RUNTIME-EXECUTION.md
findings: Stage 4 ranking evidence remains positive but modest; HGB beat base+momentum in 3/3 folds and Q5>Q1 in 3/3, while static calibration failed. F3 calibration drift supports one bounded causal prior-shift hypothesis. Stage-4B code does not refit HGB and requires a causal prior-only comparator.
decisions_made: Freeze primary Stage-4B hypothesis as STATIC_ISOTONIC adjusted by a causal 60-official-session TP-vs-SL prior ending at the H10 maturity cutoff. 126-session window is sensitivity-only. Primary must beat static base-rate, static isotonic, and causal-prior-only pooled Brier plus the frozen ECE/prevalence gates.
decisions_needed: After factual runtime, independent ChatGPT review decides whether probability architecture is ready for a separate Stage-5 holdout-freeze review. Runtime status alone never authorizes holdout access.
blocking_risks: Calibration may remain blocked; target remains conditional TP_FIRST vs SL_FIRST on resolved binary rows; ranking is not fully monotonic across all quintiles; strict execution-grade Open history remains incomplete.
validation_run: GitHub CI after Stage-4B implementation -> 198 passed, 0 failed; no real Stage-4B outcome inspected.
recommended_next_action: Run `python -m idx_trade.stage4b_development` once under the exact Stage-3/4 numerical environment using frozen input hashes. Keep runtime artifacts outside Git, document factual result, and stop before Stage 5 or holdout access.
