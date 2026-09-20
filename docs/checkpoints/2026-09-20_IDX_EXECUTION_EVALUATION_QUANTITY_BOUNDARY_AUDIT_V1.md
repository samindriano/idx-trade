# IDX Execution-to-Evaluation Quantity Boundary Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`

## Verdict

`FAIL / UNKNOWN — EXECUTION_QUANTITY_EVALUATION_NOT_CERTIFIED`

The prospective evaluation gate validates an aggregate, session-keyed
execution frame, not the planned-to-filled quantity contract. It can check
finite gross buy/sell notionals and NAV chronology, but it cannot establish
that the intended shares were filled, that a positive residual was persisted,
or that execution state agrees with target positions.

## Exact evidence

The read-only probe
`research/idx_execution_evaluation_quantity_boundary_probe_v1.py` was pinned
to:

| Source | SHA-256 |
|---|---|
| `src/idx_trade/prospective_evaluation_gate_v1.py` | `41a5ca7987b529675bc1ef1858b50b763467d3d5651f92178e4d74275f09052a` |
| `src/idx_trade/prospective_evaluation_v1.py` | `98658814531367cf779af71698c2db77ae454900c1f86b84dddf1db0ca834108` |

The gate's protected execution schema is exactly:

`session_date`, `gross_buy_notional`, `gross_sell_notional`, `nav_prev`.

The validator and `_state_reconstructable` guard contain no planned, filled,
remaining, or target-position quantity field. The order diagnostic only checks
the relationship between `requires_open_decision` and
`pending_due_to_unavailable_open`.

Synthetic counterexample:

- planned BUY notional: IDR5,000,000;
- filled BUY notional: IDR2,500,000;
- prior NAV: IDR50,000,000;
- aggregate frame accepted by the gate: IDR2,500,000 buy notional;
- reported turnover: `5%`;
- planned turnover: `10%`;
- a history carrying no plan quantity produces the identical accepted row.

The probe did not call the protected gate, open outcomes, or write any artifact.
It proves a schema/validator limitation, not that a protected evaluation was
actually accepted.

## System impact

This composes the earlier positive-partial-BUY and obligation-state findings
with the scientific evaluator. A valid aggregate execution frame can be
internally consistent while economic exposure, planned turnover, residual
repair, and cost interpretation are incomplete. A passing hash or session
coverage check cannot recover quantity semantics that were never admitted into
the evaluation input contract.

Classification: `CROSS-COMPONENT DEFECT / SCIENTIFIC INTERPRETATION RISK /
OBSERVABILITY GAP`.

Reopen only with an authorized versioned execution-evidence contract joining
Decision target, planned quantity, filled quantity, remaining/relinquished
quantity, position snapshot, pending lifecycle, and cost accounting. Do not
fabricate planned quantities from aggregate notional or protected results.

Validation: focused probe `1 passed`; standalone probe and compilation passed;
no runtime, canonical, provider, cloud, capture, telemetry, scheduler,
incumbent, or protected state was mutated.
