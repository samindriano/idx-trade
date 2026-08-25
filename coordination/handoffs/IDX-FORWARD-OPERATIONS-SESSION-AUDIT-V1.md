# Handoff

from: Codex
to: MAIN / ChatGPT independent review
task_id: IDX-FORWARD-OPERATIONS-SESSION-AUDIT-V1-CANONICAL-COMPATIBILITY
model_used: GPT-5
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: da9560c606950797ef3b640e0bcf6cc4e4ba107b
branch: ops/idx-forward-session-audit-v1
head_commit: 209d8dc36b32899675c34c29e9a8f5d89916ed6f

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
- `docs/checkpoints/2026-08-25_FORWARD_OPERATIONS_SESSION_AUDIT_V1_CANONICAL_COMPATIBILITY.md`
- `docs/checkpoints/2026-08-25_FORWARD_OPERATIONS_SESSION_AUDIT_V1_FINAL_HARDENING.md`
- `docs/checkpoints/2026-08-25_FORWARD_OPERATIONS_SESSION_AUDIT_V1_CONTRACT_CORRECTNESS.md`
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
- Official Open and dividend runtime snapshots are accepted through their
  canonical schema/hash contracts without invented generic status fields.
- Decision V2 comes from prepared `decision_plan`/`execution_plan`; state
  decisions are optional lineage metadata only.
- Prepared schedule binding is verified against the official schedule source
  and `next_planned_session(schedule, t) == T`.
- Canonical missed execution is a separate legitimate continuity state, not a
  successful execution; implementation defects take precedence over
  provenance-invalid status in aggregate output.
- Simultaneous `executions/<T>.json` and `missed_executions/<T>.json` is an
  `IMPLEMENTATION_DEFECT` with causal note
  `EXECUTION_AND_MISSED_EXECUTION_BOTH_EXIST`.
- A missed execution with a certified Official Open manifest is
  `PROVENANCE_INVALID`; the clean missed overall status is emitted only by an
  explicit predicate where the Open absence is the sole expected pending
  condition and all other required stages pass.
- Runtime snapshot parent bytes/SHA/schema/date ordering and detectable
  self/cycle metadata are checked. Terminal execution and missed artifacts
  cross-bind their runtime snapshot path/SHA to the audited PaperState stage.
- Calendar classification is independently derived from the hash-pinned
  official schedule attestation for `T`; calendar failures are included in
  overall aggregation and cannot be hidden by downstream PASS stages.
- Official Open metadata requires the canonical schema and an allowed Direct
  IDX or Zapi RAW transport in addition to the accepted field/authority/path/
  policy/execution-grade contract.
- Runtime identity requires observed HEAD/expected commit equality and clean
  checkout; scheduler PASS requires complete task, runner, runtime-v2,
  trigger, start-when-available, IgnoreNew, and network metadata.
- Prepared state and `PaperState(T).previous_snapshot` must bind the exact
  same prior runtime snapshot path/SHA. Missed execution prior-runtime
  references are checked against that same parent.
- CLI omitted `--reported-at-utc` uses actual current UTC; deterministic
  replay supplies an explicit timestamp.

## Evidence and limitations

The auditor reads JSON metadata and hashes declared sibling bytes only. It does
not read parquet values, labels, returns, protected outcomes, or provider
responses. If prepared metadata includes `next_official_session_date`, it must
equal `T`; the canonical schedule-binding metadata now provides the complete
schedule-attestation proof without date subtraction.

The calendar input must carry
`execution_schedule_attestation_path` and
`execution_schedule_attestation_sha256`; a JSON holiday/trading label without
that verified schedule proof is not sufficient.

## Validation

- Session Audit tests: `78 passed`.
- Relevant E2E/Open/schedule-binding/missed-continuity tests: `126 passed`.
- Full pytest: `838 passed, 0 failed, 3 existing pandas FutureWarnings`.
- py_compile/import smoke: PASS.
- git diff --check: PASS.
- Synthetic CLI valid t→t+1 smoke: `SESSION_HEALTHY`.
- Synthetic CLI valid holiday smoke: `NON_TRADING_SESSION`.
- Synthetic CLI missed-Open continuity smoke:
  `SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN`.
- Synthetic CLI calendar-failure smoke: `SESSION_FAIL_CLOSED_EXTERNAL`.

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

recommended_next_action: open/update a clean PR against the accepted E2E
integration lineage, obtain CI on the exact final HEAD, and wait for
independent review; do not merge or schedule this manual auditor from this
lane.
