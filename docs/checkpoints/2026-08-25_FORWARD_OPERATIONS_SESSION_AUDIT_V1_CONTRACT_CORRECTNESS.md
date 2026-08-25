# Forward Operations / Session Audit V1 Contract-Correctness Checkpoint

Date: 2026-08-25
Branch: `ops/idx-forward-session-audit-v1`
Parent reviewed HEAD: `da9560c606950797ef3b640e0bcf6cc4e4ba107b`
Final implementation HEAD: `209d8dc36b32899675c34c29e9a8f5d89916ed6f`
Status: merge-review-ready pending PR #87 CI and independent review

## Scope

This is a final narrow, read-only, outcome-blind contract-correctness pass. It
does not alter the active E2E runtime, scheduler, providers, models, Decision,
sizing, execution science, forward counter, historical E2E, Monte Carlo, or
protected outcomes. `coordination/TEAM_STATUS.md` remains MAIN-owned and is
not edited on this branch.

## Remediation

- Calendar classification is derived from a verified, hash-pinned official
  trading schedule attestation whose coverage contains `T`; JSON
  `is_trading_session`, `HOLIDAY`, and `PASS` labels are not trusted alone.
  Contradictions, tampered path/SHA, malformed attestations, and out-of-range
  dates fail closed. Calendar status is included in overall severity
  aggregation, so it cannot disappear behind passing downstream stages.
- Official Open metadata now requires the canonical schema, authority,
  upstream path, field semantics, fallback policy, execution-grade flag, and
  one of the accepted Direct IDX or Zapi RAW transports.
- Runtime identity requires observed HEAD = expected commit, explicit equality,
  clean checkout, and branch agreement when supplied. Scheduler `PASS`
  requires the exact task/runner/runtime-v2 identity, all five retry triggers
  plus `AtLogOn`, `StartWhenAvailable`, `IgnoreNew`, and network requirement.
- Prepared state and `PaperState(T).previous_snapshot` must identify the same
  verified prior runtime snapshot by path and SHA. Missed execution prior
  snapshot fields are bound to that same parent; unrelated but valid snapshot
  bytes are rejected.
- The static CLI January 2026 timestamp was removed. Omitted timestamps use
  actual current UTC; deterministic replay supplies `--reported-at-utc`.

## Validation

- Session Audit focused suite: `78 passed`.
- Relevant E2E/Open/schedule-binding/missed-continuity suite: `126 passed`.
- Full pytest: `838 passed, 0 failed, 3 existing pandas FutureWarnings`.
- `py_compile` and import smoke: PASS.
- `git diff --check`: PASS.
- CLI synthetic smokes: `SESSION_HEALTHY`, `NON_TRADING_SESSION`,
  `SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN`, and calendar-failure
  `SESSION_FAIL_CLOSED_EXTERNAL`.
- Direct and Zapi RAW canonical transport metadata tests: PASS.
- Prepared/PaperState parent path/SHA and missed-prior lineage tests: PASS.
- Runtime/scheduler completeness tests: PASS.

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

Decision: push to PR #87 for exact-head CI and independent review; do not
merge this audit branch here.
