# IDX-Trade — Obligation Artifact Migration Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Status: `MIGRATION_AUDIT_PASS / RUNTIME_NOT_IMPLEMENTED`

This is a read-only, outcome-blind migration audit. It uses a standard-library
spec harness and synthetic payloads shaped like the current execution
transaction and dividend-aware snapshot artifacts. It does not import or patch
the runtime, rewrite historical artifacts, or access provider/protected outcome
data.

## 1. Contract audited

The current completed execution artifact can retain `fills[]` rows with
`side`, `ticker`, `planned_shares`, `filled_shares`, and `status`. The current
snapshot can retain positions and ticker-level `pending_buys`/
`pending_sells`, but not a logical obligation identity or remaining quantity.

The harness assigns a deterministic compatibility ID only in its audit output:

`LEGACY_EXECUTION::<session>::<ticker>::<side>::<fill-index>`

That ID is not written to any production artifact.

## 2. Fail-closed classification rules

| Retained evidence | Classification | Remaining quantity |
|---|---|---:|
| Fill vector has `planned_shares == filled_shares` | `COMPLETE_HISTORICAL_FILL` | `0` |
| Fill vector has `0 < filled_shares < planned_shares` | `RECOVERABLE_PARTIAL_WITH_FILL_VECTOR` | `planned - filled` |
| Fill vector has `filled_shares == 0` plus pending status/row | `EXPLICIT_ZERO_LOT_PENDING` | `planned` |
| Snapshot has a position but no preserved fill/plan quantity | `UNKNOWN_ORPHANED_PARTIAL` | `UNKNOWN` |
| `filled_shares > planned_shares`, malformed quantity, or zero fill without pending evidence | `REQUIRES_RECONCILIATION` | `UNKNOWN` |

The audit never derives a remainder from position size alone. A snapshot-only
`BBCA:2,400` therefore stays `UNKNOWN_ORPHANED_PARTIAL`; it is not converted
into a fabricated 2,600-share residual.

## 3. Focused evidence

Harness: `research/idx_obligation_artifact_migration_audit_v1.py`
Tests: `tests/test_idx_obligation_artifact_migration_audit_v1.py`

Focused result: `6 passed`.

Covered cases:

1. complete 5,000/5,000 fill;
2. recoverable 5,000/2,400 positive partial with 2,600 derived only from
   the preserved fill vector;
3. explicit 5,000/0 pending with a pending intent/status;
4. snapshot-only 2,400-share position with no plan/fill evidence;
5. quantity inversion 2,400 planned versus 5,000 filled, fail-closed as
   `REQUIRES_RECONCILIATION`;
6. direct assertion that snapshot position alone never supplies a remainder.

The harness also passed `py_compile` and does not modify production source or
persisted state.

## 4. Boundary verdict

`MIGRATION_AUDIT = PASS`

`RUNTIME_MIGRATION = NOT_IMPLEMENTED`

`LEGACY_POSITIVE_PARTIAL_WITH_FILL_VECTOR = RECOVERABLE_IN_AUDIT_ONLY`

`LEGACY_POSITIVE_PARTIAL_SNAPSHOT_ONLY = UNKNOWN_ORPHANED_PARTIAL`

`HISTORICAL_ORACLE = PRESERVED`

The result narrows the safe migration boundary: retained execution fill vectors
can support a deterministic compatibility record, while snapshot-only history
cannot. Implementing this boundary in the runtime remains a separately
authorized schema/replay task.

No provider, protected outcome, production, cloud/capture/telemetry,
canonical-data, scheduler, or incumbent state was accessed or changed.
