# IDX-Trade Versioned Contract and Invariant Catalog V1

Date: 2026-09-20  
Implementation base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## OBLIGATION-V1 — initial contract

Canonical owner: `src/idx_trade/v4_x1_quantity_obligation_v1.py`.

Required fields:

- stable `obligation_id`;
- canonical security identity and `side` (`BUY`/`SELL`);
- optional `replacement_group_id`;
- `planned_shares`, `filled_shares`, `remaining_shares`,
  `relinquished_shares`;
- lifecycle `status`;
- creation/latest-attempt session and attempt count;
- typed event/reason history for block, retry, fill, cancel, and relinquish;
- parent state/lineage identity.
- optional Decision rank provenance for deterministic compatibility retry.

Mandatory invariant:

```text
planned_shares = filled_shares + remaining_shares + relinquished_shares
```

All quantities are nonnegative whole lots. Duplicate event IDs are idempotent
only when the replayed event bytes are identical. A conflicting duplicate is a
hard failure. Obligation payload deserialization replays the canonical payload
builder and rejects extra or coercible fields. No current position or ticker
membership may be used to infer a missing planned quantity.

## State ownership rules

1. The obligation ledger owns quantity completion.
2. `pending_buys`/`pending_sells` are compatibility projections only.
3. A position is not evidence that its obligation is complete.
4. A Decision seat is economically complete only when its obligation is
   `FILLED` or explicitly `RELINQUISHED`/`CANCELED` under an existing policy.
5. Legacy snapshots without plan/fill evidence remain `UNKNOWN_ORPHANED_PARTIAL`
   when a positive partial cannot be proven complete.

## Other versioned contracts to follow

| Contract | Owner | Current state |
|---|---|---|
| `PAPER_STATE-V2` | Paper state + snapshot | V2 schema, V1→V2 parent chain, additive hash, and canonical payload replay implemented; recovery open |
| `MIGRATION_PROVENANCE-V1` / `MIGRATION_ACTIVATION-V1` | Legacy-state migration provenance and activation decision | Source/hash/classification/disposition/reason/time binding plus immutable policy-gated activation decision and verified-snapshot consumer implemented locally; external policy adoption remains open |
| `CA_SIZING_LINEAGE-V1` | Dividend-aware sizing/execution wrapper | Raw execution parent, projected NAV-only sizing, `CA_TIMING_MATRIX-V1`, and persisted replay gates implemented locally |
| `CA_TIMING_MATRIX-V1` | Prepared/execution CA timing boundary | Before-decision, on-decision, on-execution, and later payment rows; canonical row/semantic verification and additive-only extension are enforced |
| `EXECUTION_EVIDENCE-V2` | Execution artifact/evaluator adapter | Quantity-bearing artifact, structural evaluator, and nested replay parent gate implemented locally; independent challenge open |
| `RECONCILIATION_RESULT-V1` | Internal paper reconciliation | Typed internal detector result, validated CA/evidence provenance, coverage gate, and nested replay parent gate; independent challenge open |
| `IDENTITY_CANONICAL-V1` | Security/universe/evaluator boundaries | Alias/revision interval contract plus Decision identity binding implemented locally; authoritative source/child replay open |
| `EXPOSURE_CAUSE-V1` | State/obligation join | Quantity/exposure/cash cause records with explicit bound-zero transitions plus cause-to-obligation retry binding implemented locally; child replay matrix open |
| `TRANSITION_BINDING-V1` | Decision identity and cause/obligation transitions | Hash-bound Decision resolutions and recomputed same-session cause/obligation joins; operational source binding open |
| `RUNTIME_LINEAGE-V2` | Config/prepare/execute/snapshot/replay | Hash-bound canonical envelope with binding-status validation implemented; operational child binding and replay matrix open |
| `CONTROLLER_RECOVERY-V1` | E2E operational controller | Durable `RUNNING` crash fence to `RECOVERY_REQUIRED`; side-effect fault matrix open |
| `SNAPSHOT_RECOVERY-V1` | Immutable rejection/quarantine | Local quarantine/recovery is consumed by orchestration state loading; independent controller challenge open |

No contract may change frozen model features, rank semantics, Decision
thresholds, tax policy, structural-CA authority, or post-entry risk policy
without a separately authoritative policy decision.
