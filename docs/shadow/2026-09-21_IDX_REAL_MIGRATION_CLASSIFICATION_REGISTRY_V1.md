# IDX-Trade Real Migration Classification Registry V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **NO REAL PAPER-STATE ROW CLASSIFIED / INPUT-ONLY EVIDENCE EXPANDED**

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
| CA event registry | Yes; 38 IDX rows / 35 tickers, 18 certified-window rows | REAL_CA_EVENT_REGISTRY / NOT_A_LEDGER | retained as source evidence; no entitlement, payment, receivable, or position migration |
| Execution-anchor input | Yes; 479,471 `REGULAR` anchors across 504 `OK` session reports; 425,340 active, 54,131 no-trade, zero duplicate keys | REAL_EXECUTION_ANCHOR_INPUT / NOT_A_FILL_VECTOR | retained as source evidence; no transaction/fill/paper-state migration |
| Historical calendar input | Yes; 516 available / 504 target sessions | REAL_CALENDAR_INPUT / LINEAGE_PARTIAL | retained as calendar evidence; no embedded historical manifest hash matched these candidates |
| Official Open archive | Yes; one run metadata file plus eight logs | REAL_OPEN_CAPTURE_ARCHIVE / NOT_EXECUTION_STATE | retained as operational evidence; no activation or replay |

The absence of paper-state rows is the result of the bounded real artifact
census, not an inference from model behavior. The newly admitted CA,
execution, calendar, and Official Open classes are input/operational evidence,
not paper-state. No fabricated envelope, synthetic row, or
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
