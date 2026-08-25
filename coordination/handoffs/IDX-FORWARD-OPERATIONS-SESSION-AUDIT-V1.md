# Handoff

from: Codex
to: MAIN / ChatGPT independent review
task_id: IDX-FORWARD-OPERATIONS-SESSION-AUDIT-V1-REMEDIATION
model_used: GPT-5
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: 402fca4b27e91cf8c82d21ff1394ba2d6da73656
branch: ops/idx-forward-session-audit-v1
head_commit: pending final commit

## Scope

Manual, read-only, outcome-blind forward operations/session audit. This lane
does not modify the active E2E runtime, scheduler, models, Decision, sizing,
execution science, counter, or protected outcomes. No provider call, capture,
or scheduler wiring was performed.

## Files changed

- `src/idx_trade/forward_session_audit_v1.py`
- `scripts/audit_forward_session_v1.py`
- `tests/test_forward_session_audit_v1.py`
- `docs/FORWARD_SESSION_AUDIT_V1.md`
- `docs/checkpoints/2026-08-25_FORWARD_OPERATIONS_SESSION_AUDIT_V1_REMEDIATION.md`
- `coordination/handoffs/IDX-FORWARD-OPERATIONS-SESSION-AUDIT-V1.md`

## Contract decisions

- Canonical ledger anchor: `execution_session_date = T`.
- Exact prepared parent for `T` is found by declared
  `execution_session_date`; its `decision_session_date = t` binds EOD, score,
  and Decision to `t`.
- Official Open, execution/pending execution, CA/dividend, PaperState, and
  scheduler bind to `T`.
- No calendar-day subtraction is used to infer `t`.
- Prepared self-hash, score parent path/SHA, execution prepared path/SHA, and
  session identity are checked.
- Causal ordering requires Decision/prepare(`t`) before Open(`T`) and Open
  no later than execution processing(`T`).
- Missing Open + no execution remains pending; successful execution without
  certified Open is an implementation defect; stricter existing failures are
  preserved.
- Unknown/malformed statuses fail closed.
- Non-trading is returned only after a valid calendar PASS. Summary counts
  non-trading separately, names the Stockbit-specific failure streak, resets
  it on a healthy trading session, and excludes holidays from PaperState
  continuity evaluation.
- Scheduler action is `scripts/run_official_open_capture.ps1`, whose module
  identity is `idx_trade.official_open_capture_runtime_v2`; the invented v2
  PowerShell action is rejected.

## Evidence and limitations

The auditor reads JSON metadata and hashes declared sibling bytes only. It does
not read parquet values, labels, returns, protected outcomes, or provider
responses. If prepared metadata includes `next_official_session_date`, it must
equal `T`; a complete official schedule-attestation proof requires the caller
to provide that accepted schedule-binding metadata because the base prepared
payload does not persist every schedule object inline.

## Validation

- Session Audit tests: `28 passed`.
- Relevant E2E/Open/Evidence Health/scheduler tests: `75 passed`.
- Full pytest: `788 passed, 0 failed, 3 existing pandas FutureWarnings`.
- py_compile/import smoke: PASS.
- git diff --check: PASS.
- Synthetic CLI valid t→t+1 smoke: `SESSION_HEALTHY`.
- Synthetic CLI valid holiday smoke: `NON_TRADING_SESSION`.

## Guard state

`PROSPECTIVE_OUTCOMES_ACCESSED=FALSE`
`REAL_PROTECTED_LOADER_CALLED=FALSE`
`REAL_OUTCOME_ACCESS_MARKER_WRITTEN=FALSE`
`FORWARD_COUNTER_CHANGED=FALSE`
`MODEL_CHANGED=FALSE`
`MODEL_REFIT=FALSE`
`MODEL_RETUNED=FALSE`
`DECISION_CHANGED=FALSE`
`SIZING_CHANGED=FALSE`
`EXECUTION_SCIENCE_CHANGED=FALSE`
`ACTIVE_RUNTIME_CHANGED=FALSE`
`SCHEDULER_CHANGED=FALSE`
`PROVIDER_CAPTURE_TRIGGERED=FALSE`
`HISTORICAL_E2E_REOPENED=FALSE`
`MONTE_CARLO_REOPENED=FALSE`

recommended_next_action: independent review; do not merge or schedule this
manual auditor from this lane.
