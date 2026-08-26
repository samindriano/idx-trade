# Handoff

from: Codex
to: ChatGPT
task_id: IDX-E2E-CLOUD-PRODUCER-PROVENANCE-PIN-REMEDIATION-V1
model_used: GPT-5
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: f38ef328e90857d94daa27d01655e095b7a0acca
branch: integration/e2e-cloud-first-orchestration-v1
head_commit: f38ef328e90857d94daa27d01655e095b7a0acca (implementation; see
  pushed branch tip for the documentation update)
scope: >-
  Remediate the cross-workflow Official Open provenance mismatch by binding
  scheduled producer evidence to one explicit, repinnable accepted producer
  implementation SHA while preserving all existing timing, capture-only,
  authority, hash, manual-capture, and no-retroactive gates.
files_changed:
  - src/idx_trade/e2e_paper_cloud_runtime_v1.py
  - scripts/run_e2e_paper_cloud_v1.py
  - tests/test_e2e_paper_cloud_runtime_v1.py
  - .github/workflows/e2e-paper-cloud-orchestration.yml
  - docs/checkpoints/2026-08-26_E2E_CLOUD_PRODUCER_PROVENANCE_PIN_REMEDIATION_V1.md
  - coordination/handoffs/IDX-E2E-CLOUD-PRODUCER-PROVENANCE-PIN-REMEDIATION-V1.md
decisions_made:
  - >-
    Require a 40-hex producer commit SHA as expected_capture_code_ref; branch
    names and mutable refs are rejected at the admission boundary.
  - >-
    Source both producer checkout and downstream expected ref from the single
    repository variable IDX_TRADE_OFFICIAL_OPEN_CAPTURE_CODE_REF, with an
    explicit producer pre-check that fails closed when unset or malformed.
  - >-
    Retain scheduled-event, capture window, capture-only, child hash,
    authority, guard, manual-dispatch, late/future, and no-retroactive gates.
  - >-
    Do not set the repository variable or merge either PR in this task.
decisions_needed:
  - >-
    Independent review of the implementation and the final PR #92 SHA;
    after acceptance, the authorized integrator must perform the deployment
    pin sequence documented in the checkpoint.
blocking_risks:
  - >-
    Until PR #92 and #93 are merged and the repository variable is set to the
    same accepted producer SHA, live producer/consumer admission remains
    intentionally blocked.
  - >-
    Private R2 input provisioning, live conditional-store smoke, and one live
    cloud session remain unproven.
validation_run: >-
  Focused cloud tests 36 passed; E2E/Official Open regression 149 passed; full
  pytest 879 passed, 0 failed, 0 skipped, with 3 pre-existing FutureWarnings;
  all changed Python entrypoints compiled/imported, both workflow YAML files
  parsed, and git diff --check passed.
recommended_next_action: >-
  Review the final PR #92/#93 diffs and validations. If accepted, merge #92,
  obtain its integration merge SHA, repin #93 and the producer variable to the
  exact accepted producer implementation, then separately authorize live
  proof.
