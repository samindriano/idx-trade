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

## Immediate next questions

1. Can a residual-aware synthetic multi-session harness prove planned/filled/remaining quantity, cash, NAV, turnover, and concentration consistency?
2. Which artifact should own planned/filled/remaining quantities so restart and replay cannot erase the obligation?
3. How should a residual buy interact with Decision V2 shadow state and the 10-seat capacity rule?
4. Does CA payment/settlement state interact with a residual order obligation across sessions?

## Constraints

- No source patch has been applied.
- No production, canonical data, cloud/capture/telemetry, scheduler, or protected outcome access.
- No push or merge.
- New external data acquisition remains owned by another lane.

## Durable references

- Master dossier: `docs/checkpoints/2026-09-20_IDX_SYSTEM_DEEP_DIVE_AND_FULL_HISTORY_V1.md`
- Frontier matrix: `docs/checkpoints/2026-09-20_IDX_SYSTEM_FRONTIER_MATRIX_V1.md`
- Findings/no-retry log: `docs/checkpoints/2026-09-20_IDX_SYSTEM_FINDINGS_NO_RETRY_LOG_V1.md`
