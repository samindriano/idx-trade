# EXECSTATE-01 Official Execution-State Surface — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PARTIAL_SOURCE_DIAGNOSTIC / NOT_ADMITTED / NO CANDIDATE`

## Question

Does the official IDX execution-anchor sidecar add a coherent, distinct
regular-market state surface—especially `NO_TRADE` with non-regular activity—
that is worth preserving for future research, or is the state label only a
restatement of missing/zero regular activity?

This is a source-capability and target-free state-semantics audit. It cannot
produce IC, ICIR, OOS, P&L, candidate superiority, survivor status, or a C5
admission.

## Sources and grain

- Combined anchors:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\execution_1260\idx_execution_anchors.csv`.
- Regular-trade anchors:
  `idx_stock_summary_regular_trade_anchors_1260.csv`.
- No-trade anchors:
  `idx_stock_summary_no_trade_anchors_1260.csv`.
- Session report: `idx_execution_session_report.csv`.
- Raw composition fields are reconciled to the already-audited official
  stock-summary cache; panel and frozen official sessions are comparison
  controls only.
- Expected grain: one `(ticker,as_of_date)` regular-market state row.

## Frozen checks

1. Validate file inventory, schema, key uniqueness, non-null required fields,
   allowed market/state/source/evidence values, official-session coverage, and
   session-report status/row reconciliation.
2. Reconcile combined/active/no-trade state keys to raw stock-summary rows and
   verify the declared state rules:
   `ACTIVE` has positive regular volume/frequency/value and `NO_TRADE` has
   zero regular volume/frequency/value.
3. Count the preregistered diagnostic cell
   `NO_TRADE & (nonregular_volume > 0 or nonregular_frequency > 0)` and the
   corresponding `ACTIVE & nonregular_activity` cell. Do not clip or interpret
   these as a probability/share.
4. Reconcile to the frozen panel and report panel-only/cache-only rows,
   ticker breadth, date breadth, and state transitions per ticker. State
   transition counts are descriptive capability evidence only.
5. Preserve exact source/code hashes and explicit access flags.

## Fail-closed rules

- `NO_TRADE` is not assumed to mean suspended, unavailable, unlisted, or
  missing; its exchange semantics remain an open question.
- A source endpoint/date reference is not a row-level publication or
  knowledge-time contract. No revision/vintage or population completeness is
  inferred.
- No security identity, issuer/ISIN continuity, or listing transition is
  inferred from ticker/date keys.
- No target, outcome, provider, candidate ID, imputation, forward fill,
  parameter sweep, packet expansion, or production use is permitted.

## Decision outcomes

- `SOURCE_PARTIAL_STRUCTURAL_SIGNAL`: internal state/reconciliation checks
  pass and the diagnostic cell is non-empty, but semantics/PIT remain partial.
- `SOURCE_BLOCKED`: grain, state, session, source, or reconciliation checks
  materially fail.
- `SOURCE_REDUNDANT`: state adds no distinct information after reconciliation.
