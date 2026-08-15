# Handoff

from: Codex
to: ChatGPT independent review
task_id: IDX-FOREIGN-FLOW-REPRESENTATION-V2-FORWARD
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: d204a8fd3edaacef91aacbe90ac39f0e1969e420
branch: integration/foreign-flow-representation-v2-forward-v1
head_commit: 84ad72dd65e5108ecaaa9a703672663e06cb6337
scope: outcome-blind prospective Foreign Flow Representation V2 producer and minimal Setup State catchup wiring
files_changed:
  - src/idx_trade/forward_foreign_flow_representation_v2.py
  - tests/test_forward_foreign_flow_representation_v2.py
  - docs/checkpoints/2026-08-15_FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_PRODUCER.md
  - coordination/handoffs/IDX-FOREIGN-FLOW-REPRESENTATION-V2-FORWARD.md

## Findings

- Exact accepted V2 builder/formulas are reused; no feature/window/threshold
  redesign was made.
- Each output target is `feature_session=t+1` from one prior official
  `flow_through_session=t`.
- The remediation now accepts a completed source session `t` only; target
  `t+1` market/flow rows and target session directory are not required.
- Prospective pairs live under
  `forward_monitoring/prospective/foreign_flow_representation_v2/<t+1>/`.
  Existing catchup consumes that pair after target capture and passes explicit
  paths to the existing Setup State consumer.
- Historical rolling state is replayed from SHA-pinned accepted history and
  extended only by verified canonical forward EOD artifacts.
- Market context uses canonical forward OHLCV plus `session_evidence` official
  `regular_market_value`; no inferred market value is accepted.
- Listing-aware context and same-source-session primary-liquid ranks remain
  delegated to the accepted causal context builder.
- Missing extension sessions, invalid/partial market evidence, duplicate or
  conflicting identities, hash mismatch, non-causal rows, and immutable
  artifact revision conflicts fail closed.
- After the prospective representation pair is verified, the existing
  `run_foreign_flow_catchup()` is called. It consumes the pair once the target
  session is complete and materializes Setup State V1. No new scheduler,
  capture system, or counter was introduced.

## Decisions made

- No real target was executed in this task; 2026-08-11/12 were not
  retroactively enriched or synthetically backfilled.
- The local runtime calendar is currently sparse (2026-08-10..12). The
  producer therefore refuses to run until the existing official calendar sync
  provides a complete path/SHA matching the target session manifest.
- Read-only audit confirms 2026-08-10 is incomplete (962 rows versus
  `recordsTotal=963` and no raw/Foreign Flow sidecar), while 2026-08-11/12
  are verified but must remain immutable. The pinned historical market panel
  ends 2026-07-31 and the separate 2026-08-03..11 calendar extension is
  blocked. No producer run was attempted.
- The unrelated storage test failure was not changed.

## Validation

- Focused producer + V2 + setup + runner tests: 26 passed, 5 warnings.
- Full repository pytest: 111 collected; 110 passed, 1 failed, 5 warnings.
- Failure: existing `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`; it expects one conflict while current storage returns independent `raw_close` and `vendor_adj_close` conflicts.
- `git diff --check`: PASS.

## Blocking risks / review points

- Existing EOD automation must pass a complete official calendar (not the
  currently sparse local calendar) and invoke the new producer for a new
  target session. This task intentionally did not edit or create a scheduler.
- The producer's source trigger is the completed source EOD session; the
  feature target is the next official date and may not yet have a session
  folder. A session-local and prospective pair together fail closed as
  ambiguous.
- Setup State creation still relies on the existing parent-manifest calendar
  identity; this is deliberate to prevent calendar compression or stale
  provenance.

## Recommended next action

Review the producer and decide whether the existing calendar-sync owner should
expose a full historical-plus-current official session file to the producer.
Only after that review should a genuinely new live EOD target be run.
