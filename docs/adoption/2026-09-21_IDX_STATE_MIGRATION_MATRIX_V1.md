# State and Artifact Migration Matrix V1

Date: 2026-09-21

Migration is a shadow-only design. No real runtime artifact is read, copied,
rewritten, or activated by this branch.

The granular rows below are executable through
src/idx_trade/v4_x1_migration_compatibility_v1.py. That classifier accepts
only a canonical caller-supplied evidence envelope and returns a typed
classification; it never constructs a V2 state. The existing
v4_x1_migration_provenance_v1.py remains the immutable artifact/provenance
writer for verified runtime snapshots.

| Historical shape | Classification | Allowed action | Proof required |
|---|---|---|---|
| Complete plan and complete fill vector | RECOVERABLE_COMPLETE | reconstruct filled obligation with zero remaining | exact source hash, plan/fill conservation, provenance |
| Explicit zero-lot pending BUY/SELL | RECOVERABLE_ZERO_FILL_PENDING | preserve planned quantity and open remainder | explicit pending row and session/identity binding |
| Positive partial with preserved plan/fill vector | RECOVERABLE_PARTIAL | reconstruct exact filled and remaining quantities | full fill vector, event lineage, parent hash |
| Snapshot-only positive position with no plan evidence | UNKNOWN_ORPHANED_PARTIAL | block normal activation; manual review only | absence itself is not permission to infer |
| Inverted, negative, or malformed quantity vector | REQUIRES_RECONCILIATION | retain source immutable; no V2 state | typed reason and source hash |
| Conflicting duplicate event bytes | REQUIRES_RECONCILIATION | reject conflict; never last-write-wins | both event bytes and conflict hash |
| V1 snapshot with no obligation section and no positive partial proof | LEGACY_POSITION_ONLY | load only under explicit legacy mode | caller policy and migration provenance |
| Prepared artifact with missing config/lineage hash | REQUIRES_RECONCILIATION | reject before execution | exact config and parent identity |
| Stale latest snapshot with verified ancestor | RECOVERABLE_FROM_ANCESTOR | quarantine latest and recover exact ancestor | canonical filename, ancestry, fork check |
| Valid non-ancestor competing snapshot | REQUIRES_RECONCILIATION | reject fork; never choose arbitrarily | ancestry proof |

## Migration artifact chain

The rehearsal must emit the following immutable chain:

    OLD STATE
      -> CLASSIFICATION
      -> MIGRATION_PROVENANCE-V1
      -> ACTIVATION DECISION
      -> PAPER-STATE-V2
      -> RELOAD
      -> REPLAY

Each output binds source artifact hash, source schema, classification,
disposition, reason, decision time, and optional runtime-lineage hash.
Create-only/idempotent same-bytes writes are permitted in synthetic roots.

## Invariants

- no position drift;
- no cash drift;
- no duplicate obligation;
- no fabricated residual;
- no lost pending transition;
- no CA double settlement;
- no state-hash ambiguity;
- no silent identity normalization.

Migration remains BLOCKED for any real artifact until the user authorizes a
separate immutable input root and a shadow-only run.
