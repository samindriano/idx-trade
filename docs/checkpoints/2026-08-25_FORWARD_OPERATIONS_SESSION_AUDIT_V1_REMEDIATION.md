# Forward Operations / Session Audit V1 Remediation Checkpoint

Date: 2026-08-25
Branch: `ops/idx-forward-session-audit-v1`
Parent reviewed head: `d18add369b77dbb2a70d00e09a67451263c6a47d`

## Scope and isolation

This remediation remains a manual, deterministic, outcome-blind observability
lane. It does not modify or deploy the active E2E runtime, Windows Task
Scheduler, models, Decision, sizing, execution science, forward counter, or
protected outcomes. No provider call or scheduler wiring was performed.

The canonical coordination status file was not edited on this branch because
root policy reserves `coordination/TEAM_STATUS.md` for MAIN.

## Canonical causal contract

The ledger anchor is `execution_session_date = T`. The auditor finds the exact
prepared parent whose declared `execution_session_date` is `T` and derives
`decision_session_date = t` from that parent. It then binds:

- EOD capture, V4-X1 score, and Decision V2 to `t`;
- Official Open, execution/pending execution, CA/dividend operational
  metadata, PaperState, and scheduler evidence to `T`.

The auditor never derives `t` by subtracting one calendar date. Prepared
payload self-hash, prepared parent path/SHA, score manifest path/SHA and
decision-session identity are checked before the chain is considered valid.
If `next_official_session_date` is present in prepared metadata, it must equal
`T`; a full schedule-attestation proof still requires the caller to provide
the corresponding accepted schedule-binding metadata.

For a successful execution the strongest available causal chain is:

`Decision/prepare(t) < Official Open(T) <= execution processing(T)`.

Prepared-after-Open, Open-after-execution, execution-before-prepared, wrong
session, wrong prepared parent, stale/backdated Open, and retroactive execution
are rejected.

## Severity and rolling summary

Cross-stage validation is monotonic: `FAIL_CLOSED_EXTERNAL`,
`PROVENANCE_INVALID`, and `IMPLEMENTATION_DEFECT` cannot be downgraded to
`PASS` or `PENDING_EXPECTED`. Unknown or malformed statuses are
`PROVENANCE_INVALID`. A missing Open with a prepared order and no execution is
`PENDING_EXPECTED`; a successful execution without certified Open is an
`IMPLEMENTATION_DEFECT`.

The rolling metric is explicitly
`consecutive_stockbit_provider_failures`. A later healthy trading session
resets it to zero. `NON_TRADING_SESSION` is counted separately, is not a
healthy trading session, and does not break applicable PaperState continuity.

## Scheduler identity

The accepted task action is `scripts/run_official_open_capture.ps1`; that
runner internally invokes `idx_trade.official_open_capture_runtime_v2`.
The invented `run_official_open_capture_v2.ps1` action is rejected. Scheduler
metadata must expose the runtime module identity as well as the action if the
module binding is to be certified.

## Changes

- hardened `src/idx_trade/forward_session_audit_v1.py` for causal t→T
  mapping, immutable parent/hash checks, monotonic severity, unknown-status
  rejection, Open retroactive/backdated rejection, actual scheduler identity,
  no-op resolution, and summary semantics;
- added `--prepared-metadata` to the read-only CLI;
- replaced the invalid same-date synthetic fixture with a valid t→t+1
  lifecycle and adversarial causal/provenance tests;
- documented the contract and metadata-only schedule-attestation limitation.

## Validation

- focused Session Audit suite: `28 passed`;
- relevant E2E/Open/Evidence Health/scheduler regression suite: `75 passed`;
- full pytest: `788 passed, 0 failed, 3 existing pandas FutureWarnings`;
- `python -m py_compile src/idx_trade/forward_session_audit_v1.py
  scripts/audit_forward_session_v1.py`: PASS;
- `git diff --check`: PASS;
- CLI valid t→t+1 smoke: `SESSION_HEALTHY`;
- CLI valid holiday smoke: `NON_TRADING_SESSION`;
- all smokes used synthetic temporary metadata only.

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

Final state: ready for independent review; do not merge or schedule this
manual auditor from this lane.
