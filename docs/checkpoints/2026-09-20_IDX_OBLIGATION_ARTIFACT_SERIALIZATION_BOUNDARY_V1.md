# IDX-Trade — Obligation Artifact Serialization Boundary V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: `ARTIFACT_BOUNDARY_AUDITED / OBLIGATION_NOT_BOUND`

This is a read-only source audit of the retained runtime artifact serializers.
It does not modify runtime code or any persisted artifact.

## 1. Exact runtime inspected

- Runtime worktree: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational`
- Commit: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
- Relevant serializers:
  - `e2e_paper_orchestration_v1._execution_plan_payload`
  - `e2e_paper_orchestration_v1._sizing_payload`
  - `e2e_paper_orchestration_v1._execution` body construction
  - `forward_dividend_runtime_v1_1._snapshot_payload`

## 2. Boundary inventory

| Artifact | What it preserves | What it does not preserve |
|---|---|---|
| Prepared execution | sizing entries with planned lots/shares/notional/status; sells; buy intents; target positions; state/input hashes; projected cash/NAV | fill event, stable obligation ID, cumulative filled/remaining quantity, attempt/age, cancellation lineage |
| Completed execution | fill vector with `planned_shares`, `filled_shares`, prices, fees, status; turnover; pending count; runtime snapshot hash | stable link from each fill to a logical obligation; explicit remaining quantity; retry/cancel event history |
| Runtime snapshot | positions, ticker-level pending buys/sells, cash, CA ledger, registry, recursive hashes | fill history, planned-vs-filled relation, remaining quantity, obligation ID, attempt history, explicit cancel/expiry event |
| Runtime state hash | normalized base paper state plus dividend ledger/registry | semantic order history that is not represented in positions or pending rows |

The current design therefore has a useful fill vector in the completed
execution artifact, but the durable snapshot is a lossy projection for
quantity-obligation purposes. The two are hash-connected through the snapshot
file, not logically joined by an obligation identity.

## 3. Consequence for the observed defect

For a positive partial BUY, the completed execution can say
`planned_shares=5,000` and `filled_shares=2,400`, while the durable state only
contains the actual position and no pending BUY. After reload, the runtime hash
can be perfectly equal while the state no longer contains the 2,600-share
remainder or a link back to the fill vector.

For a partial SELL, the snapshot retains a ticker-level pending SELL and the
actual residual position, but still has no remaining quantity, attempt/age, or
event lineage. A later Decision reversal can be deterministic in the adapter
while the completed artifact has no typed cancellation event to connect to the
old obligation.

This is an artifact/state contract gap, not an omission in the prepared sizing
serializer: planned entries are already present there.

## 4. Safest additive direction

If a separately authorized implementation lane is opened, the least
destructive schema direction is:

1. add a versioned `obligations` collection to the durable snapshot;
2. add `obligation_id` and cumulative quantity fields to execution fill records;
3. retain the existing fill vector, pending views, and historical schema for
   backward reading;
4. bind the obligation collection into the runtime/state hash;
5. classify legacy positive partials without a preserved plan as
   `UNKNOWN_ORPHANED_PARTIAL`, never as an inferred remainder;
6. emit typed retry, block, cancel, expiry, and manual-review events.

This direction preserves historical replay evidence while making the new
quantity contract auditable. It is a design recommendation, not an
authorization to patch the active runtime.

## 5. Boundary verdict

`PLANNED_SIZING_SERIALIZATION = PRESENT`

`FILLED_VECTOR_SERIALIZATION = PRESENT`

`DURABLE_OBLIGATION_IDENTITY = ABSENT`

`REMAINING_QUANTITY_AFTER_RELOAD = ABSENT`

`CANCELLATION_LINEAGE = ABSENT`

No provider, protected outcome, production, cloud/capture/telemetry,
canonical-data, or incumbent state was accessed or changed.
