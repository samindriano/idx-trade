# Handoff

from: Codex
to: ChatGPT independent review
task_id: IDX-CANONICAL-EOD-CALENDAR-PARENT-ATTESTATION-V1-TEMPORAL-REMEDIATION
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: a3e54c965ea5c417d58472365926f5356a924a8b
branch: integration/canonical-eod-calendar-parent-attestation-v1
head_commit: pending until push
scope: Remediate only temporal dependencies in the legacy canonical EOD calendar-parent attestation verifier/writer.
files_changed:
  - src/idx_trade/canonical_eod_calendar_parent_attestation.py
  - tests/test_canonical_eod_calendar_parent_attestation.py
  - docs/checkpoints/2026-08-15_CANONICAL_EOD_CALENDAR_PARENT_ATTESTATION_V1_TEMPORAL_REMEDIATION.md
  - coordination/handoffs/IDX-CANONICAL-EOD-CALENDAR-PARENT-ATTESTATION-V1-TEMPORAL-REMEDIATION.md
findings:
  - Audit-time mutable calendar SHA is retained as evidence but is not a future verification invariant.
  - Audit-time global absence of the old SHA is retained as evidence but later recovery is accepted.
  - Canonical manifest path/SHA and declared calendar path/SHA remain strict immutable anchors.
  - Runtime preflight remains read-only for 2026-08-11 and 2026-08-12.
decisions_made:
  - Do not recapture or rewrite canonical EOD sessions.
  - Do not materialize the real runtime attestation.
  - Do not rerun Price State smoke.
  - Use exclusive same-directory temporary-file plus hard-link publication for immutable creation.
decisions_needed:
  - Independent review/authorization for one real 2026-08-11 runtime attestation write.
blocking_risks:
  - Full pytest retains one unrelated storage conflict-count assertion failure.
  - The original 2026-08-11 calendar bytes remain an audit-time unavailable parent; the attestation does not claim byte identity with the bridge calendar.
validation_run:
  - Focused: python -m pytest tests/test_canonical_eod_calendar_parent_attestation.py tests/test_forward_price_trend_context_bridge.py -q — 15 passed.
  - Full: python -m pytest -q — 86 passed, 1 failed, 87 collected; only unrelated storage assertion failed.
  - git diff --check — passed.
  - Read-only runtime preflight — 11 unrecovered audit-time parent; 12 direct parent recovered; no runtime writes.
recommended_next_action: ChatGPT review only; if accepted, authorize exactly one 2026-08-11 attestation write before any Price State smoke.
