# IDX Active Frontier Handoff V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`

## Active frontier

**Sizing → Open execution → pending quantity → next-session Decision → restart**

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

## Immediate next questions

1. Can a residual-aware synthetic multi-session harness prove planned/filled/remaining quantity, cash, NAV, turnover, and concentration consistency?
2. Which state/artifact boundary should own filled/remaining quantities, given that planned per-entry sizing is already preserved in the prepared payload?
3. Can the existing failure-recovery/atomic snapshot path preserve a residual obligation once one is explicitly modeled?
4. Can a residual-aware CA timing matrix distinguish actual entitlement from an unmet target quantity without over-entitling?

## Constraints

- No source patch has been applied.
- No production, canonical data, cloud/capture/telemetry, scheduler, or protected outcome access.
- No push or merge.
- New external data acquisition remains owned by another lane.

## Durable references

- Master dossier: `docs/checkpoints/2026-09-20_IDX_SYSTEM_DEEP_DIVE_AND_FULL_HISTORY_V1.md`
- Frontier matrix: `docs/checkpoints/2026-09-20_IDX_SYSTEM_FRONTIER_MATRIX_V1.md`
- Findings/no-retry log: `docs/checkpoints/2026-09-20_IDX_SYSTEM_FINDINGS_NO_RETRY_LOG_V1.md`
