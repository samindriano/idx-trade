# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-REPRESENTATION-V2-STRUCTURAL-AUDIT
model_used: GPT-5 / Luna xhigh orchestration profile
reasoning_level: xhigh
source_repository: C:\\Users\\Sam\\.codex\\worktrees\\idx-financial-representation-v2
source_commit: 1a9bf7267728d9beec2a975ac4b4e931d0be16d0
branch: research/idx-financial-representation-v2
head_commit: pending commit
scope: outcome-blind Financial PIT compact-representation structural census
files_changed:
  - src/idx_trade/financial_representation_v2.py
  - tests/test_financial_representation_v2.py
  - docs/checkpoints/2026-08-16_FINANCIAL_REPRESENTATION_V2_STRUCTURAL_AUDIT.md
  - coordination/handoffs/IDX-FINANCIAL-REPRESENTATION-V2-STRUCTURAL-AUDIT.md
findings:
  - support rows: 277244; support tickers: 729
  - selected financial bundle rows: 70931; selected bundle tickers: 415
  - CORE3 available rows: 70520
  - CORE3 plus yoy_revenue available rows: 34412
  - CORE3 plus yoy_total_assets available rows: 34412
  - both YoY candidates are completely absent from V2F4 training
  - same-bundle violations: 0
  - selected knowledge-time violations: 0
  - selected provenance-incomplete rows: 0
decisions_made:
  - recommend CORE3 as the widest structurally admissible outcome-blind representation
  - do not admit either YoY candidate before a separate contract decision
  - keep Financial Alpha V2 unrun and unauthorized
decisions_needed:
  - ChatGPT review of CORE3 admission and whether a preregistered Alpha V2 experiment is warranted
blocking_risks:
  - full repository pytest has one unrelated existing storage revision-conflict failure
  - 19549 support rows have unresolved exact period-boundary evidence and remain excluded
validation_run:
  - focused pytest: 3 passed
  - full pytest: 64 passed, 1 failed; unrelated storage test
  - deterministic external runs run2/run3: all artifacts byte-identical
  - no labels, predictions, models, performance metrics, providers, O2, or protected outcomes accessed
recommended_next_action: independent ChatGPT review; do not start Financial Alpha V2 until explicitly authorized
