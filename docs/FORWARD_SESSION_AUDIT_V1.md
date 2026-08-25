# IDX Forward Operations / Session Audit V1

Status: remediation-ready-for-review, outcome-blind, read-only

## Purpose

`forward_session_audit_v1` audits one prospective session as an operational
evidence ledger. It answers whether the expected capture, scoring, decision,
Open certification, execution, corporate-action, continuity, and scheduler
artifacts are present, correctly identified, and causally ordered.

The auditor never starts a capture, scorer, executor, scheduler, or provider
client. It reads JSON metadata and hashes declared sibling bytes only. It does
not open parquet values, labels, returns, an outcome vault, or a protected
forward artifact.

The ledger is anchored on the execution session `T`, not the decision session.
For `T`, the auditor finds the prepared parent whose declared
`execution_session_date` is `T`, derives decision session `t` from that parent,
and then binds EOD, score, and Decision to `t`. Official Open, execution,
corporate-action metadata, PaperState, and scheduler evidence remain bound to
`T`. The relationship is read from verified metadata; the auditor never
guesses `t` by subtracting one calendar day.

The audit is deliberately separate from the model and counter contracts. A
`PASS` means that the declared operational evidence passed the checks in this
version; it is not a performance result and does not authorize a model or
counter update.

## Stage ledger

Each ledger has one row for each stage, in this order:

1. `official_trading_calendar`
2. `runtime_identity`
3. `stockbit_scheduled_capture`
4. `canonical_eod_capture`
5. `v4_x1_scoring`
6. `decision_v2`
7. `prepared_order`
8. `official_open_evidence`
9. `paper_execution`
10. `ca_dividend`
11. `paperstate_continuity`
12. `forward_evidence_health`
13. `scheduler_task`

The stage status vocabulary is:

- `PASS`: metadata, identity, declared hashes, and stage-specific checks pass.
- `LEGITIMATE_NOOP`: the stage explicitly records a valid no-trade/no-session
  outcome.
- `PENDING_EXPECTED`: an upstream stage is not ready yet, or a required
  expected artifact is not present.
- `FAIL_CLOSED_EXTERNAL`: the stage cannot be certified because an external
  dependency failed.
- `PROVENANCE_INVALID`: wrong session, malformed guard, stale artifact,
  mismatched hash, protected path, or contract mismatch.
- `IMPLEMENTATION_DEFECT`: an internally impossible ordering or duplicate
  execution condition is observed.
- `NOT_APPLICABLE`: the stage is not required, for example on a holiday or
  after a legitimate zero-trade decision.
- `NOT_READ`: the caller did not declare the optional metadata input.

Overall statuses are `NON_TRADING_SESSION`, `SESSION_HEALTHY`,
`SESSION_HEALTHY_LEGITIMATE_NOOP`, `SESSION_PENDING_EXPECTED`,
`SESSION_FAIL_CLOSED_EXTERNAL`, `SESSION_PROVENANCE_INVALID`, and
`SESSION_IMPLEMENTATION_DEFECT`.

## Fail-closed checks

The auditor checks exact session identity wherever it is declared, timezone-
aware timestamps, declared sibling SHA-256 values, stale/retroactive flags,
execution duplicates, parent path/SHA bindings, and prepared-before-executed
ordering. It refuses paths
whose components contain protected outcome/label/realized/vault tokens and
requires explicit outcome-blind guards when a source declares them.

The official Open stage accepts only this contract:

```text
authority       = IDX
upstream_path   = TradingSummary/GetStockSummary
field_semantics = IDX_OFFICIAL_OPENPRICE
transport_policy= DIRECT_IDX_THEN_ZAPI_RAW_V1
fallback_policy = NONE
execution_grade = true
```

`FirstTrade`, `IEP`, `IEV`, generic OHLC, duplicate source keys, missing
declared raw/normalized bytes, or a relabelled transport are rejected. The
auditor does not parse raw rows to reconstruct Open values; the existing
official Open verifier remains the value-level authority.

On a non-trading session, all downstream stages are `NOT_APPLICABLE`, but only
after the official calendar itself passes. When a decision is an explicit
legitimate no-op, order and execution stages are not required. When an order
exists but official Open is unavailable, execution is `PENDING_EXPECTED`; it is
never treated as certified merely because an execution-shaped JSON file exists.
If a successful execution is present without certified Open, the audit reports
`IMPLEMENTATION_DEFECT`. A stricter existing failure is never downgraded by a
later cross-stage check. Unknown or malformed statuses are
`PROVENANCE_INVALID`, never `PASS`.

## Metadata-only boundary

`forward_evidence_health_v1` is reused for the hash/identity health summary.
The session auditor intentionally does not invoke value verifiers that would
load `model_input.parquet`, labels, realized returns, or protected forward
outcomes. A future value-level audit must be a separately authorized tool with
its own contract.

The summary contains only operational counts: healthy trading sessions,
non-trading sessions, incomplete/fail-closed/provenance/implementation
defects, latest healthy trading session, a specifically named consecutive
Stockbit provider-failure streak, official Open transport distribution,
missing-stage frequency, and PaperState continuity for applicable trading
sessions. A later healthy trading session resets the Stockbit streak; a
holiday neither counts as healthy nor breaks PaperState continuity. No return,
IC, PnL, target, or score metric is emitted.

The accepted scheduler action is `scripts/run_official_open_capture.ps1`; that
runner internally invokes `idx_trade.official_open_capture_runtime_v2`. The
audit rejects the invented `run_official_open_capture_v2.ps1` action and also
requires an explicit runtime-module identity when scheduler metadata is used.
If a caller supplies only task-action metadata, the module binding cannot be
proven and the scheduler stage remains fail-closed.

The prepared payload's persisted execution date is the authoritative parent
identity. If a caller additionally supplies `next_official_session_date`, it
must equal that execution date. This metadata-only auditor does not infer a
next session from a date subtraction; a complete schedule-attestation proof
requires the caller to provide the corresponding prepared/schedule-binding
metadata from the accepted E2E contract.

## CLI examples

Audit one session into an external runtime directory:

```powershell
$env:PYTHONPATH = "C:\path\to\idx-trade\src"
python scripts/audit_forward_session_v1.py `
  --session-date 2026-08-27 `
  --forward-monitoring-root "D:\external\forward_monitoring" `
  --e2e-runtime-root "D:\external\e2e_runtime" `
  --calendar-metadata "D:\external\calendar\2026-08-26.json" `
  --runtime-identity "D:\external\runtime\2026-08-26.json" `
  --stockbit-capture "D:\external\stockbit\2026-08-26.json" `
  --ca-dividend "D:\external\ca\2026-08-27.json" `
  --scheduler-metadata "D:\external\scheduler\2026-08-27.json" `
  --prepared-metadata "D:\external\e2e_runtime\prepared\2026-08-26.json" `
  --output "D:\external\audit\2026-08-26.json"
```

The command is manual and read-only. It must not be added to a scheduled task
without a separately reviewed operational change.
