# IDX-Trade — Quantity-Obligation State Contract V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: `DESIGN_PROPOSAL / NOT_IMPLEMENTED`

This checkpoint converts the current cross-component evidence into a minimal
state contract for future hardening. It is a design result, not a source patch,
production policy, or admission decision.

## 1. Why a new state owner is required

The retained runtime already preserves planned sizing inside the prepared
execution payload and records planned/filled fields in each `FillRecord`. The
semantic loss occurs afterward:

- a positive partial BUY becomes an actual position without a residual BUY
  obligation;
- Decision V2 and risk-facing state reason over ticker membership, not target
  quantity;
- partial SELLs carry a ticker-level pending intent but no remaining quantity,
  age, or attempt history;
- dividend settlement changes cash while pending execution remains unchanged;
- target reversal can intentionally cancel pending transitions, but the output
  has no typed cancellation lineage.

The state contract therefore needs a first-class logical order obligation. A
ticker-keyed pending row is not sufficient as the authoritative owner.

## 2. Proposed authoritative obligation

Each logical order should have a stable `obligation_id` independent of a single
execution attempt. The minimum fields are:

| Field | Required meaning |
|---|---|
| `obligation_id` | Stable identity across retries, reload, and replay |
| `canonical_ticker` | Normalized security identity; never an alias-only relationship |
| `side` | `BUY` or `SELL` |
| `replacement_group_id` | Optional logical pairing for sell-before-buy transitions |
| `planned_shares` | Quantity requested by the accepted sizing plan |
| `filled_shares` | Cumulative confirmed paper fills |
| `remaining_shares` | Outstanding quantity still authorized/retryable |
| `relinquished_shares` | Explicitly canceled/expired quantity; default zero |
| `status` | `PLANNED`, `PARTIAL`, `BLOCKED`, `FILLED`, `CANCELED`, `EXPIRED`, or `MANUAL_REVIEW` |
| `created_session_date` | Session in which the logical obligation was created |
| `last_attempt_session_date` | Most recent execution attempt |
| `attempt_count` | Number of deterministic execution attempts |
| `last_reason` / `reason_history` | Capacity, Open, fee, pairing, reversal, or policy reason |
| `parent_state_hash` | Exact state from which the attempt was prepared |

Compatibility `pending_buys` and `pending_sells` can remain as derived views,
but they must not be the only persisted representation.

## 3. Core invariants

For each logical obligation:

```text
planned_shares = filled_shares + remaining_shares + relinquished_shares
```

All three quantities are non-negative whole lots. A retry may change the
attempt record, but may not create a second logical obligation for the same
unresolved quantity.

For each ticker and session, the actual paper position must reconcile with
opening position plus cumulative BUY fills minus cumulative SELL fills. A
target membership match is not sufficient evidence of quantity completion.

For each Decision plan, expose at least:

```text
target_shares
actual_shares
remaining_buy_shares
remaining_sell_shares
residual_notional
exposure_state_reason
```

`capacity_state=FULL` is permitted only when all target quantity obligations
are either filled or explicitly relinquished under a declared policy. A full
ticker set alone cannot produce `FULL`.

## 4. Event semantics across components

### 4.1 Execution and retry

- `ORDER_PLANNED` creates one obligation.
- `FILL_APPLIED` increments `filled_shares` and reduces
  `remaining_shares` atomically with the paper-state update.
- `BLOCKED` records the attempt reason without deleting the obligation.
- A later attempt reuses `obligation_id` and increments `attempt_count`.
- `FILLED` is valid only when `remaining_shares == 0`.

### 4.2 Corporate actions

Dividend entitlement uses actual shares held at the cum-date state. A future
BUY `remaining_shares` must not receive a prior dividend merely because the
target plan intended those shares. A future SELL obligation also must not erase
an already recorded cum-date entitlement.

Payment settlement changes cash and ledger state exactly once. It must either:

1. explicitly emit a `SETTLEMENT_AVAILABLE_FOR_REPLAN` transition and bind the
   next plan to the settled parent hash; or
2. explicitly declare that settlement does not trigger re-planning.

The current runtime demonstrates option 2 behavior, but does not encode this
as a typed obligation policy.

### 4.3 Reversal and expiry

A target reversal must emit a typed event such as
`CANCELED_BY_TARGET_REVERSAL`, retaining the canceled quantity and the parent
obligation ID. Capacity starvation must have a declared expiry/escalation rule
(`EXPIRED`, `MANUAL_REVIEW`, or indefinitely retryable). Removing a pending row
without one of these events is not an auditable lifecycle transition.

### 4.4 Restart and replay

The durable runtime hash and snapshot lineage must include the obligation
ledger, not only positions and ticker-level pending views. Replaying an already
applied attempt must return the same state and must not increment fills,
settlements, or attempts twice.

## 5. Risk and accounting projections

Risk/accounting consumers should distinguish:

| Quantity | Meaning |
|---|---|
| actual exposure | Marked value of confirmed paper positions |
| target exposure | Marked value requested by the current Decision/sizing plan |
| residual exposure | Authorized target quantity not yet filled |
| free cash | Spendable cash after fees and settled CA cash |
| reserved cash | Cash held back by an explicit outstanding obligation, if policy says so |
| unexplained gap | Difference not covered by an active obligation or declared policy |

This prevents a partial seat, an intentional Decision vacancy, a capacity
block, and a risk-held cash balance from collapsing into the same “FULL” or
“cash” interpretation.

## 6. Evidence-driven acceptance matrix

| Scenario | Required result |
|---|---|
| BUY 5,000, fill 2,500 | `PARTIAL`, remaining 2,500, retry identity preserved |
| SELL 5,000, fill 1,000 over three sessions | cumulative fills and remaining quantity exact; attempt history retained |
| zero capacity after partial fill | obligation remains or escalates under explicit policy; no silent disappearance |
| CA cum date while BUY residual exists | entitlement uses actual shares only |
| CA payment while replacement is pending | exactly-once settlement plus explicit replan/no-replan policy |
| Decision reverses pending pair | typed cancellation retains obligation lineage and canceled quantity |
| process restart after any event | state/hash/replay are equal without duplicate fill or payment |
| risk snapshot with underfilled seat | target, actual, residual, and exposure reason are separately visible |
| projected CA state enters sizing | execution parent hash binds the same projected/raw-state policy |

## 7. Boundary and implementation disposition

This proposal does not authorize changing the frozen Decision V2 policy,
reopening protected outcomes, acquiring data, or modifying production/runtime
code. Implementation should be a separately reviewed isolated hardening lane
with migration/replay tests for the historical partial-sell and zero-lot-buy
contracts. Until then, the existing system remains `NO-GO` for claiming
quantity-complete portfolio semantics.

Evidence references:

- `2026-09-20_IDX_SIZING_EXECUTION_PARTIAL_BUY_AUDIT_V1.md`
- `2026-09-20_IDX_PARTIAL_BUY_TRIGGER_MATRIX_V1.md`
- `2026-09-20_IDX_PENDING_CA_REVERSAL_MATRIX_V1.md`
- `2026-09-20_IDX_CROSS_COMPONENT_PARTIAL_FILL_CA_MATRIX_V1.md`
- `2026-09-20_IDX_RISK_CONCENTRATION_HOLDING_AUDIT_V1.md`
