# Handoff

from: Codex
to: MAIN / ChatGPT review
task_id: IDX-E2E-PREOPEN-CA-WORKFLOW-ACTIVATION-V1
model_used: GPT-5
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: 740a6e0db2caf544e6f9333dae1d2d3e60061f0f
branch: codex/e2e-preopen-ca-activation-v1
head_commit: see final branch HEAD; do not use this field as a self-reference
scope: Activate the accepted V3 cloud runner and durable PREOPEN_CA phase in the existing E2E workflow.
files_changed:
  - .github/workflows/e2e-paper-cloud-orchestration.yml
  - tests/test_e2e_paper_cloud_activation_v1.py
  - docs/checkpoints/2026-08-27_E2E_PREOPEN_CA_WORKFLOW_ACTIVATION.md
  - coordination/handoffs/IDX-E2E-PREOPEN-CA-WORKFLOW-ACTIVATION-V1.md
findings:
  - Main workflow previously invoked V2 and had no PREOPEN_CA schedule or phase mapping.
  - Accepted V3 runner is pinned at 6e1bf4a1e47a2abff365b35c19687444cf3f0596 and enforces the 09:02 Asia/Jakarta cutoff.
  - PREOPEN_CA, PREOPEN, and POST_EOD use separate serialized concurrency groups so a CA retry cannot queue-block PREOPEN.
decisions_made:
  - Add weekday PREOPEN_CA retries at 08:30, 08:45, and 08:55 Asia/Jakarta.
  - Preserve existing PREOPEN and POST_EOD schedules and phase behavior.
  - Use the accepted V3 runner without modifying its code or scientific semantics.
decisions_needed:
  - Review, CI, and merge this narrow workflow activation PR.
  - Observe the first genuine scheduled PREOPEN_CA/PREOPEN/POST_EOD cycle.
blocking_risks:
  - GitHub scheduled events can be delayed; the V3 cutoff remains fail-closed and a late CA event cannot perform capture.
validation_run:
  - Static workflow tests and YAML validation are required on this branch.
  - Existing accepted V3 focused tests cover dispatch and cutoff/continuity behavior.
recommended_next_action: Run focused/full validation, merge if clean, then verify merged main workflow bytes and monitor the next scheduled cycle.
