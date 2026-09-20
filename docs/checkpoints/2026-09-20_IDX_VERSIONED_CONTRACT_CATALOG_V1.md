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
hard failure. No current position or ticker membership may be used to infer a
missing planned quantity.

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
| `PAPER_STATE-V2` | Paper state + snapshot | Additive obligation field/hash implemented; explicit snapshot schema pending |
| `EXECUTION_EVIDENCE-V2` | Execution artifact/evaluator adapter | Planned |
| `RECONCILIATION_RESULT-V1` | Internal paper reconciliation | Planned |
| `IDENTITY_CANONICAL-V1` | Security/universe/evaluator boundaries | Planned |
| `EXPOSURE_CAUSE-V1` | State/obligation join | Planned |
| `RUNTIME_LINEAGE-V2` | Config/prepare/execute/snapshot/replay | Planned |
| `CONTROLLER_RECOVERY-V1` | E2E operational controller | Planned |
| `SNAPSHOT_RECOVERY-V1` | Immutable rejection/quarantine | Planned |

No contract may change frozen model features, rank semantics, Decision
thresholds, tax policy, structural-CA authority, or post-entry risk policy
without a separately authoritative policy decision.
