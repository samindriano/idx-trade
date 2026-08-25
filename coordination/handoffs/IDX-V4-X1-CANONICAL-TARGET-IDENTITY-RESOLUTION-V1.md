# Handoff

from: Codex
to: ChatGPT / MAIN
task_id: IDX-V4-X1-CANONICAL-TARGET-IDENTITY-RESOLUTION-V1
model_used: GPT-5
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: `2be7160f20184e489f7a9f82a0d6aac890622c7e` (origin/main at audit start)
branch: `research/idx-v4-x1-prospective-evaluation-protocol-v1`
head_commit: `b7567af74bb9f90a6ca5e61413cf0cebcac9ccf5` (code-pinning implementation head; publication commit follows)
scope: Outcome-blind resolution of PR #83 canonical V4-X1 target identity and historical metric reconciliation.
files_changed:
  - config/v4_x1_prospective_evaluation_contract_v1.json
  - config/v4_x1_prospective_evaluation_code_pin_v1.json
  - config/v4_x1_canonical_target_spec_v1.json
  - src/idx_trade/v4_x1_canonical_target_v1.py
  - src/idx_trade/prospective_evaluation_gate_v1.py
  - tools/evaluate_prospective_v4_x1.py
  - tests/test_v4_x1_target_identity_v1.py
  - tests/test_prospective_evaluation_preflight_v1.py
  - docs/checkpoints/2026-08-25_V4_X1_CANONICAL_TARGET_PROVENANCE_GRAPH_V1.json
  - docs/checkpoints/2026-08-25_V4_X1_CANONICAL_TARGET_IDENTITY_RESOLUTION_V1.md
  - this handoff
findings:
  - Canonical target semantics are proven from pinned retained lineage.
  - The target is Open(t+1) to Close(t+5)/Close(t+10), percentile-ranked within session with average ties and 50/50 consensus.
  - Historical IC values are different named statistics/support presentations, not evidence of different target semantics.
  - Exact provenance of 0.0980538834688018 remains unresolved and is retained as context-only.
decisions_made:
  - Resolve target_identity independently from historical_point_estimate.
  - Bind target identity to target-spec SHA and construction source commit/blob/SHA.
  - Keep real protected access blocked.
decisions_needed:
  - Independent review of the provenance graph and final PR #83 readiness.
blocking_risks:
  - Exact source/support for historical point estimate 0.0980538834688018 is not proven.
  - No protected outcome access is authorized by this handoff.
validation_run:
  - `18 passed` target identity tests
  - `7 passed` preflight tests
  - `56 passed` gate tests
  - `19 passed` prospective evaluator tests
  - `py_compile` PASS
  - `git diff --check` PASS
  - evaluator status-only returned `PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT`
recommended_next_action: Independently review Package A, then continue the separate forward-reliability audit from current origin/main without opening protected outcomes.
