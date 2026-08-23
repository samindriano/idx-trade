# Handoff

from: Codex
to: MAIN / ChatGPT review
task_id: STOCKBIT-R2-LONG-TERM-RETENTION-V1
model_used: gpt-5.6-luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 75a23a8e034fb4fd0936a2163778cfef0606ae8f
branch: fix/stockbit-r2-retention-v1
head_commit: pending
scope: Remove the project-owned 180-day Stockbit R2 delete rules and retain all research payloads indefinitely.
files_changed:
  - config/stockbit_r2_retention_v1.json
  - scripts/configure_stockbit_r2_retention_v1.py
  - tests/test_stockbit_r2_retention_v1.py
  - docs/checkpoints/2026-08-23_STOCKBIT_STREAM_R2_RETENTION_V1.md
  - coordination/handoffs/STOCKBIT-R2-LONG-TERM-RETENTION-V1.md
findings:
  - The prior config generated delete rules for raw/ and normalized/ after 180 days.
  - The new config generates no delete rules and pins the exact retired project-owned IDs.
  - The preflight preserves unrelated lifecycle rules verbatim and fails closed on ownership ambiguity.
  - Remote activation is pending; no R2 object has been listed, read, deleted, or overwritten.
decisions_made:
  - Keep raw, normalized, manifests, and universe_inputs indefinitely for now.
  - Defer storage-tier migration to a separate task.
decisions_needed:
  - Review and approve one manual remote lifecycle apply/verify run after merge.
blocking_risks:
  - Remote activation must fail closed if a retired ID is changed, duplicated, or an unowned delete rule targets raw/normalized.
validation_run: Focused retention tests, py_compile, and git diff --check pending final run; no provider/object data access.
recommended_next_action: Merge the policy change, dispatch the manual workflow once, verify both retired IDs are absent, then record the final remote rule set and payload hash.
