# Forward Operations / Session Audit V1 Canonical Compatibility Checkpoint

Date: 2026-08-25
Branch: `ops/idx-forward-session-audit-v1`
Parent reviewed head: `a3b7a1c9e528440f76b77557fc80e2c6c8a4c0a1`

## Scope

This is a bounded, outcome-blind compatibility remediation for the existing
read-only session auditor. It does not merge or deploy the auditor, modify the
active E2E runtime, scheduler, models, Decision V2, sizing, execution science,
counter, provider state, or protected outcomes. `TEAM_STATUS.md` remains
MAIN-owned and was not edited on this branch.

## Canonical production-shape decisions

- The ledger remains anchored on execution session `T`; the prepared parent
  supplies decision session `t`.
- Decision V2 is read from the hash-bound `decision_plan` and
  `execution_plan` embedded in `prepared/<t>.json`. `state/decisions/<t>.json`
  is not treated as the Decision artifact.
- Prepared plan hashes, parent file hashes, and the canonical prepared schedule
  binding are verified. The binding proves the observed calendar, schedule
  attestation, source document, and `next_planned_session(schedule, t) == T`.
- Official Open manifest `idx_official_open_evidence_v1_1` and dividend runtime
  snapshot `idx_trade_forward_dividend_runtime_state_v1_1` are validated by
  their own schemas and hashes; a synthetic generic `status` is not required.
- Missing `prepared_at_utc` / `executed_at_utc` is accepted for canonical
  payloads. Timestamp ordering is checked only when a canonical timestamp is
  actually present; the immutable session/hash graph remains mandatory.
- An explicit empty canonical execution plan can be a legitimate no-op, but a
  zero trade/intents field in unrelated metadata cannot create N/A when pending
  orders remain.
- `missed_executions/<T>.json` with
  `MISSED_EXECUTION_NO_CERTIFIED_OPEN`, exact prepared/schedule/runtime parents,
  zero fills/turnover/costs, and no retroactive execution is legitimate
  continuity evidence, reported separately as
  `SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN`.
- Aggregate severity gives `SESSION_IMPLEMENTATION_DEFECT` precedence over
  `SESSION_PROVENANCE_INVALID` when both are present.

## Required regression coverage

The focused suite covers the production-shape cases A–M: status-less Open and
runtime snapshot acceptance; state-decision non-authority; timestamp-optional
prepared/execution; exact prepared/schedule/Open/execution chain; wrong next
session and binding SHA rejection; pending-order no-op protection; missed
execution continuity; exact parent hashes; defect-over-provenance precedence;
and a production-shape offline smoke.

## Validation

- Focused session-audit tests: `41 passed`.
- `py_compile` for auditor, CLI, and focused tests: PASS.
- Relevant E2E/Open/schedule/continuity tests: `150 passed`.
- Full pytest: `801 passed, 0 failed, 3 existing pandas FutureWarnings`.
- CLI production-shape trading smoke: `SESSION_HEALTHY`.
- CLI holiday smoke: `NON_TRADING_SESSION`.
- CLI missed-Open continuity smoke:
  `SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN`.
- CLI outputs used fresh temporary external roots and no provider/runtime
  capture.
- No provider calls, runtime capture, scheduler change, model/Decision change,
  outcome access, or counter mutation.

## Decision

The branch remains review-only. Do not merge or deploy this manual auditor
until independent review accepts the compatibility evidence.
