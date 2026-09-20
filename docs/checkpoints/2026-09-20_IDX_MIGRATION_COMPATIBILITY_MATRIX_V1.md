# IDX-Trade Migration and Compatibility Matrix V1

| Historical evidence shape | Migration result | Allowed interpretation |
|---|---|---|
| Complete plan and complete fill vector | `RECOVERABLE_COMPLETE` | Reconstruct filled obligation with zero remaining |
| Explicit zero-lot pending BUY/SELL | `RECOVERABLE_ZERO_FILL_PENDING` | Preserve planned quantity and open remainder |
| Positive partial with preserved plan/fill vector | `RECOVERABLE_PARTIAL` | Reconstruct exact filled and remaining quantities |
| Snapshot-only positive position with no plan evidence | `UNKNOWN_ORPHANED_PARTIAL` | Do not infer planned or remaining quantity |
| Quantity inversion/negative/malformed vector | `REQUIRES_RECONCILIATION` | Halt normal migration; retain evidence and reason |
| Conflicting duplicate event bytes | `REQUIRES_RECONCILIATION` | Never silently choose last event |
| Old snapshot with no obligation section and no positive partial proof | `LEGACY_POSITION_ONLY` | Load only under explicit legacy mode; no quantity completion claim |

Compatibility rules:

- old artifacts remain byte-immutable;
- old hashes are not rewritten;
- the current lane has additive obligation serialization in the retained V1.1
  runtime; an explicit new snapshot schema/version and migration classifier
  are still open and must be added before this matrix can be called complete;
- migration output must record source artifact hash and classification;
- no current position, target membership, or seat count fabricates a missing
  plan/fill/remainder;
- a migration failure blocks normal execution until manual/reconciled state is
  supplied.
