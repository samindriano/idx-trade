# Handoff

from: Codex
to: ChatGPT independent review
task_id: IDX-FOREIGN-FLOW-REPRESENTATION-V2-FORWARD
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 5374c238d3ed90823a18c49f1b0b1be4a0583469
branch: integration/foreign-flow-representation-v2-forward-v1
head_commit: 07660db
scope: outcome-blind prospective Foreign Flow Representation V2 producer and immediate Setup State V1 delivery
files_changed:
  - src/idx_trade/forward_foreign_flow_representation_v2.py
  - src/idx_trade/forward_foreign_flow_setup.py
  - tests/test_forward_foreign_flow_representation_v2.py
  - tests/test_forward_foreign_flow_setup.py
  - docs/checkpoints/2026-08-15_FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_PRODUCER.md
  - docs/checkpoints/2026-08-15_FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_SETUP_DELIVERY_REMEDIATION.md
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
  The producer immediately materializes and verifies Setup State beside the
  pair; existing catchup can later consume the Representation V2 pair after
  target capture for canonical session wiring.
- Historical rolling state is replayed from SHA-pinned accepted history and
  extended only by verified canonical forward EOD artifacts.
- Market context uses canonical forward OHLCV plus `session_evidence` official
  `regular_market_value`; no inferred market value is accepted.
- Listing-aware context and same-source-session primary-liquid ranks remain
  delegated to the accepted causal context builder.
- Missing extension sessions, invalid/partial market evidence, duplicate or
  conflicting identities, hash mismatch, non-causal rows, and immutable
  artifact revision conflicts fail closed.
- After the prospective representation pair is verified, the producer now
  immediately calls `enrich_prospective_foreign_flow_setup()` and verifies
  the Setup State pair in the same prospective folder. This requires no
  target session directory, target market/Foreign Flow data, or target EOD
  completion. Existing `run_foreign_flow_catchup()` remains available for
  later canonical-session consumption. No new scheduler, capture system, or
  counter was introduced.
- The prospective Setup State manifest pins the source session, next official
  feature session, calendar path/SHA, Representation V2 parquet/manifest
  SHA, unchanged frozen thresholds, and outcome-blind/prohibited-access flags.
- The prospective verifier does not read target-session files. It fails closed
  on missing/ambiguous provenance, non-causal or non-official dates, duplicate
  keys, source SHA mismatch, and immutable sidecar/manifest revision conflict.

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
- The new prospective Setup State path relies on the Representation V2
  manifest's hash-pinned official calendar identity; this avoids the prior
  target-session dependency while preventing calendar compression or stale
  provenance. The later canonical-session path retains its parent-manifest
  calendar validation.

## Recommended next action

Review the producer and decide whether the existing calendar-sync owner should
expose a full historical-plus-current official session file to the producer.
Only after that review and a complete post-2026-07-31 market/Foreign Flow
context extension should a genuinely new live EOD target be run.

## Remediation validation

- Focused producer/V2/setup/runner suite: `32 passed, 5 warnings`.
- Full repository suite: `117 collected; 116 passed, 1 failed, 5 warnings`.
- The sole failure is the unrelated storage audit-conflict expectation in
  `tests/test_storage.py`; `storage.py` was not changed.
- `git diff --check`: PASS.
- No real runtime run, provider call, outcome access, model work, O2 change,
  scheduler/counter change, free-float/HSC work, or price-state work occurred.
