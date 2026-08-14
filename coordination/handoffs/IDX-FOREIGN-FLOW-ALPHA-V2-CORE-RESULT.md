# Handoff

from: Codex/Foreign-Flow-Core-Alpha-V2
to: ChatGPT reviewer / MAIN
task_id: IDX-FOREIGN-FLOW-ALPHA-V2-CORE
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 4adc9484bc33febf240752c3e904a93aca9bae82
branch: research/idx-foreign-flow-alpha-v2-core
head_commit: 5867fd8377eb717659abef4caa01ae01a15df3e5
scope: One preregistered Clean V2 versus Clean V2 plus all eight Foreign Flow V2 core features historical-development experiment.
files_changed: |
  src/idx_trade/foreign_flow_alpha_v2.py
  tests/test_foreign_flow_alpha_v2.py
  docs/checkpoints/2026-08-15_FOREIGN_FLOW_ALPHA_V2_CORE_PREREGISTRATION.md
  docs/checkpoints/2026-08-15_FOREIGN_FLOW_ALPHA_V2_CORE_RESULT.md
  coordination/handoffs/IDX-FOREIGN-FLOW-ALPHA-V2-CORE-RESULT.md
findings: |
  Common support is 292631 rows, 737 tickers, 1231 sessions. The eight-feature
  challenger has 266498 complete rows, 25873 partial rows and 260 all-missing
  rows. All flow keys joined without changing support identity and all flow
  feature rows passed exact previous-official-session causality.
decisions_made: |
  The one-shot gate failed. Verdict is FOREIGN_FLOW_V2_CORE_NO_SURVIVOR.
  No subset, alternate-window, rescue, provider, forward, O2, or protected
  outcome work was performed after the run.
decisions_needed: |
  Independent review of the exact external manifest and result. No follow-up
  experiment is proposed in this lane.
blocking_risks: |
  Full repository pytest retains one unrelated pre-existing failure in
  tests/test_storage.py: the current storage contract emits two revision
  conflicts while the test expects one. This experiment did not touch storage.
validation_run: |
  Focused alpha V2 tests: 4 passed. Full pytest: 67 passed, 1 failed. git
  diff --check: passed. Result manifest SHA-256:
  23275d2a673ac99dc0928a5a6c0956a0059c82c80a13eea83b4e5db4c4252852.
recommended_next_action: Independent ChatGPT review; retain the exact Clean V2 control and do not run rescue/subset/alternate-window experiments in this lane.
