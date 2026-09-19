# SUSPSTATE-01 Suspension-Interval Reconciliation — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PARTIAL_PROVENANCE_DIAGNOSTIC / NOT_ADMITTED / NO CANDIDATE`

## Question

How much of the official `NO_TRADE` execution state is explained by the
retained exchange suspension intervals, and are the interval records aligned
to the regular-market execution anchors without hidden many-to-many or timing
contradictions?

This is a provenance/state-semantics audit, not a liquidity alpha test. It
cannot produce IC, ICIR, OOS, P&L, candidate superiority, survivor status, or
candidate/packet admission.

## Sources and registered grain

- Suspension intervals:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\tradability_intervals_1260.csv`.
- Official sessions:
  `D:\Documents\Project\idx-v4-x1-clean-historical-input-stage-r2-20260820\official_exchange_sessions_1260.csv`.
- Regular no-trade anchors:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\execution_1260\idx_stock_summary_no_trade_anchors_1260.csv`.
- Registered interval grain: one `ticker × market × suspension interval`.
- Registered expanded grain: one `ticker × market × official session`.

## Frozen checks

1. Validate interval schema, state/source values, date parsing, effective
   ordering, `announced_at <= effective_from`, open-ended interval handling,
   duplicate/overlap behavior, and official-session expansion.
2. Expand each interval across the frozen official session calendar and report
   market-specific rows separately (`REGULAR`, `CASH`, `NEGOTIATED`).
3. Reconcile expanded `REGULAR` suspension keys to regular `NO_TRADE` anchors:
   exact overlap, interval-covered-but-not-anchor, and anchor-not-covered.
4. Report whether one or multiple interval records map to each expanded key,
   plus open interval and source-reference coverage.
5. Preserve exact hashes and access flags. No target or candidate score is
   read.

## Fail-closed rules

- A suspension interval is not assumed to explain every `NO_TRADE` row, and a
  `NO_TRADE` row is not assumed to mean suspension.
- `CASH` and `NEGOTIATED` intervals must not be silently collapsed into
  `REGULAR` state evidence.
- Publication/knowledge-time and revision/vintage are not inferred from
  `announced_at` alone.
- No imputation, source fallback, event relabeling, candidate ID, packet
  expansion, target access, or production use.

## Decision outcomes

- `PASS_NARROW_RECONCILIATION_GLOBAL_STATE_UNKNOWN`: interval mechanics and
  regular-key reconciliation are internally valid, but state completeness and
  semantics remain partial.
- `SOURCE_BLOCKED`: material date, overlap, source, or grain failure.
