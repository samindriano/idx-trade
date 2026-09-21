# IDX-Trade Real Migration Classification Registry V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **NO REAL ROW CLASSIFIED / BLOCKED BY ABSENT MIGRATABLE STATE**

## Registry result

| Real artifact class | Real candidate located | Classification | Disposition |
|---|---|---|---|
| Paper portfolio state | No | NOT_AVAILABLE | no migration run |
| Prepared execution parent | No | NOT_AVAILABLE | no activation |
| Execution/fill vector | No | NOT_AVAILABLE | no reconstruction |
| Pending obligation ledger | No | NOT_AVAILABLE | no pending recovery |
| CA entitlement/settlement ledger | No | NOT_AVAILABLE | no CA composition |
| Reconciliation chain | No | NOT_AVAILABLE | no recovery chain |
| Session/model input files | Yes; 29 session packages / 232 files | NOT_A_PAPER_STATE / LINEAGE_PARTIAL | not classified as state; 27 input-level passes, 2 calendar-boundary failures, and replay blocked by historical calendar reconciliation |

The absence is the result of the bounded real artifact census, not an
inference from model behavior. No fabricated envelope, synthetic row, or
position-to-obligation reconstruction was added to this registry.

## Synthetic classifier context

The preceding adoption packet records the candidate classifier's local shape
matrix as `11/11 PASS`, including complete, pending, partial, orphan,
conflict, malformed, legacy, stale-ancestor, and fork cases. That is useful
implementation evidence only. It is not a real migration classification.

## Gate

`REAL_MIGRATION = BLOCKED`.

Real migration cannot start until a separately authorized immutable input root
contains a real state artifact with verified schema, lineage, identity, and
CA authority. The active writable runtime remains untouched.
