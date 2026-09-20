# IDX Dividend Sizing and Execution State-Hash Audit V1

Date: 2026-09-20  
Audited source lane: detached `runtime/idx-e2e-baseline-paper-v1` at `402fca4b27e91cf8c82d21ff1394ba2d6da73656`  
Documentation lane: isolated `codex/alpha-available-data-20260919`  
Status: **FAIL — PROJECTED CA SIZING STATE IS NOT EXECUTION-PARENT-COMPATIBLE**  
Evidence class: synthetic-only, outcome-blind, read-only audit

## Scope and boundary

This audit tests the interaction between dividend lifecycle settlement, projected state used for sizing, prepared execution parent hashes, and next-session execution. It does not use provider data, protected outcomes, canonical datasets, capture/cloud state, telemetry, or production state. No runtime source was changed.

## Existing design path

The orchestration intentionally projects corporate-action lifecycle state for sizing without persisting it immediately:

1. `_state_for_dividend_sizing` calls `process_dividend_eod` on the raw runtime state.
2. `prepare_execution_v1_1_from_decision_v2` builds the base execution plan from that projected state.
3. Orchestration replaces only the outer dividend-aware state/ledger hashes with hashes of the raw persisted state.
4. Next-session execution receives the raw persisted state and calls the legacy execution engine, which checks `base_plan.state_hash`.

This is intended to keep the prepared artifact bound to the raw snapshot while allowing already-earned receivables to affect NAV/sizing. The base execution state hash must therefore be explicitly compatible with the state that will actually be executed.

## Synthetic reproduction

Input state at decision session `2026-08-31`:

- cash: `1,000,000.0`;
- no positions;
- one valid BBCA-style cash-dividend ledger shape for `AAA`;
- receivable: `5,000.0` due on `2026-08-31`;
- next execution session: `2026-09-01`;
- one synthetic `AAA` buy intent;
- valid synthetic EOD/Open/CA-attestation objects.

The projected sizing state correctly settled the receivable:

```json
{
  "raw_cash": 1000000.0,
  "projected_cash": 1005000.0,
  "base_plan_state_hash": "da10491c7d96f97ae4a614088b501b88b31cabb21b510561baf695e26cbd7a52",
  "raw_state_hash": "96459c8d82722b43345bfcfff61f39becb55155cb96010e29152b8d65a859ebb"
}
```

After rebinding the outer dividend-aware hashes exactly as orchestration does, `execute_open_v1_1` was called with the raw state. It failed before any fill:

```text
DecisionV1Error: EXECUTION_V1_STATE_HASH_MISMATCH
```

Thus the path “payment settles on the decision session, projected cash is used for sizing, then the prepared plan executes against the raw state” is not composable. The failure is fail-closed, but it prevents the intended transition and leaves the system without a valid prepared/executable pair for that timing case.

## Exact implementation evidence

- `src/idx_trade/e2e_paper_orchestration_v1.py:629-643` — projected CA state is created for sizing.
- `src/idx_trade/e2e_paper_orchestration_v1.py:1288-1303` — production execution path sizes from `sizing_state`, then rebinds only outer dividend hashes to raw `state`.
- `src/idx_trade/forward_dividend_v1.py:739-780` — dividend-aware preparation builds the base plan from the supplied state's base state and preserves its base state hash.
- `src/idx_trade/forward_dividend_v1.py:784-803` — execution verifies outer hashes, then delegates to `execute_open_v1`.
- `src/idx_trade/v4_x1_execution_v1.py` — delegated execution checks the base plan's `state_hash` against the actual state before fills.
- `src/idx_trade/forward_dividend_execution_v1_1.py:817-851` — reconciled orchestration executes first and advances dividend lifecycle afterward; it does not repair the base-plan state hash before delegation.

Source hashes at audit time:

| File | SHA-256 |
|---|---|
| `src/idx_trade/e2e_paper_orchestration_v1.py` | `D10ACE3F01E407ED8198460D5571F26E92107F681F3268AD60BE1D42CC081EEC` |
| `src/idx_trade/forward_dividend_v1.py` | `16FA3857514A9903CA6A3E048A3CDB2A04DC5E43FB993B399B3E4C5564703E7B` |
| `src/idx_trade/forward_dividend_execution_v1_1.py` | `38D56FDEE14A38A7864F22BC5FC5C0A1D1FCD28B976B72D3AB6F73F3BDD2A0C5` |

## Risk interpretation

The prior belief that “receivables are included in NAV but not spendable cash” is correct in isolation, and unit tests correctly verify that separation. The new finding is cross-component: once a payment is actually due at the decision boundary, the projected-state sizing optimization and raw-state execution-parent binding disagree. The system fails closed rather than overspending, but the valid payment timing case is operationally blocked.

This is not evidence of live accounting loss or of a current production incident. It is a structural integration defect in the accepted E2E design.

## Hardening proposal — not applied

One of these explicit policies must be chosen and tested in a separate runtime lane:

1. Persist the lifecycle transition before preparing execution, then bind both sizing and execution to the settled state; or
2. Keep the raw state immutable but build the executable plan against raw-state hash while carrying a separately auditable projected-cash/sizing adjustment; or
3. Block preparation when projected CA state differs from the execution parent, with an explicit retry/next-session policy.

Silently rebinding only the outer hash is insufficient. Any fix must include payment-on-decision-date, payment-before-decision-date, and payment-on-execution-date scenarios plus restart/idempotency checks.

## Verdict

**FAIL — PROJECTED CA SIZING STATE IS NOT EXECUTION-PARENT-COMPATIBLE**

No source, data, provider, cloud, capture, telemetry, or production mutation was performed.
