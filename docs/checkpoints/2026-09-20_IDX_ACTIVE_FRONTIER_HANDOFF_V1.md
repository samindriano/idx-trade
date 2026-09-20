# IDX Active Frontier Handoff V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`

## Active frontier

**Quantity-obligation contract → historical replay compatibility → isolated remediation harness**

## Current hypothesis

The system tracks target membership but not target quantity obligations. A positive partial buy can therefore look complete to execution, persistence, Decision, risk, and evaluation layers even though the requested notional was not delivered.

## Evidence completed

- Exact retained runtime source commit audited: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`.
- Existing focused execution/sizing/E2E suite: 59 passed.
- Synthetic positive partial buy: planned 5,000, filled 2,500, pending empty.
- Next session: no retry intent, position remains 2,500.
- Snapshot round-trip: same partial position, no pending, runtime hash equal.
- Durable checkpoint: `2026-09-20_IDX_SIZING_EXECUTION_PARTIAL_BUY_AUDIT_V1.md`.
- Trigger matrix: capacity/Open change, fee boundary, stamp-threshold boundary,
  and resolved paired replacement all produced positive underfill with empty
  pending state and no next-session retry.
- Durable checkpoint: `2026-09-20_IDX_PARTIAL_BUY_TRIGGER_MATRIX_V1.md`.
- Decision V2 ten-seat probe: one 2,400/5,000 partial seat plus nine full seats
  still produced `FULL`, zero unfilled slots, and no retry on the next plan.
- Positive underfill composed with synthetic cash-dividend lifecycle: actual
  1,200 shares received IDR 30,000 entitlement/settlement versus IDR 125,000
  planned-share hypothetical; CA replay remained exactly-once.
- Existing dividend-aware runtime snapshot reload preserved `AAA:1,200`, empty
  pending buys, and equal runtime hash; this is faithful persistence, not
  residual recovery.
- Serializer probe was a negative result: prepared execution payloads preserve
  per-entry planned sizing; the unresolved owner is filled/remaining quantity
  linkage in execution state and pending obligations.
- Full orchestration staged recovery returned identical execution/snapshot hashes
  after deleting both outputs, but preserved `T00:2,400` and empty pending buys.
- Historical archaeology confirmed an entry/exit asymmetry: positive partial
  sells were explicitly made pending in `d8d34b79`, while positive partial buys
  remained membership-complete in the earlier `e1531b3c` contract and replay
  oracle `ce91d60a`.
- New four-session synthetic matrix: repeated partial exits reduced `AAA`
  5,000 → 4,000 → 3,000 → 2,000, then zero capacity left the sell/buy pair
  pending; no age, attempt, or remaining-share field existed in the pending
  schema.
- CA composition: the original 5,000-share cum-date entitlement settled
  IDR125,000 exactly once; cash changed while the pending replacement remained
  unchanged.
- Target reversal: the Decision V2 adapter explicitly recognized shadow `BBB`
  → target `AAA`, produced no effective orders or fills, and removed both
  pending rows. No typed cancellation event or obligation lineage was emitted,
  leaving expiry/escalation and audit policy unresolved.
- Durable checkpoint: `2026-09-20_IDX_PENDING_CA_REVERSAL_MATRIX_V1.md`.
- Evidence-driven design checkpoint: `2026-09-20_IDX_QUANTITY_OBLIGATION_STATE_CONTRACT_V1.md`.
- Historical compatibility checkpoint: `2026-09-20_IDX_OBLIGATION_HISTORICAL_COMPATIBILITY_AUDIT_V1.md`.

## Immediate next questions

1. Can an isolated versioned replay harness prove one obligation identity across partial fill, retry, CA payment, reversal, and restart?
2. Which migration fixture classes can be handled as complete, zero-lot pending, or `UNKNOWN_ORPHANED_PARTIAL` without fabricating quantity?
3. Which recovery invariant should reconcile the obligation ledger after restart or interrupted execution?
4. Can the new oracle remain compatible with immutable historical replay results while adding residual assertions?
5. What evidence would justify moving the proposal from design-only to a separately authorized implementation lane?

## Constraints

- No source patch has been applied.
- No production, canonical data, cloud/capture/telemetry, scheduler, or protected outcome access.
- No push or merge.
- New external data acquisition remains owned by another lane.

## Durable references

- Master dossier: `docs/checkpoints/2026-09-20_IDX_SYSTEM_DEEP_DIVE_AND_FULL_HISTORY_V1.md`
- Frontier matrix: `docs/checkpoints/2026-09-20_IDX_SYSTEM_FRONTIER_MATRIX_V1.md`
- Findings/no-retry log: `docs/checkpoints/2026-09-20_IDX_SYSTEM_FINDINGS_NO_RETRY_LOG_V1.md`
