# IDX Sizing-to-Execution Partial-Buy Audit V1

Date: 2026-09-20  
Audited source lane: detached `runtime/idx-e2e-baseline-paper-v1` at `402fca4b27e91cf8c82d21ff1394ba2d6da73656`  
Documentation lane: isolated `codex/alpha-available-data-20260919`  
Status: **FAIL — POSITIVE PARTIAL BUY IS NOT PERSISTED AS PENDING**  
Evidence class: synthetic-only, outcome-blind, cross-component audit

## Scope and baseline

This audit composes Sizing V1, Open execution, pending-order accounting, next-session Decision inputs, and runtime snapshot reload. It does not access protected outcomes, provider data, canonical datasets, capture/cloud state, telemetry, or production state. No runtime source was modified.

The retained runtime's focused execution/sizing/E2E suites passed **59 tests**:

- execution/sizing: 17;
- orchestration/controller/replay/runtime-config: 42.

Those tests cover zero-lot pending, partial sells, cash/capacity invariants, and canonical paired replacements, but they do not assert that a positive partial buy becomes a pending buy.

## Reproduction

Synthetic input:

- NAV/cash: IDR 50,000,000;
- EOD reference close for `AAA`: IDR 1,000;
- sizing target: 10% NAV, therefore 5,000 planned shares / 50 lots;
- reference-day liquidity: high enough not to bind;
- next-session Open: IDR 2,000;
- valid `NO_RELEVANT_EVENTS` CA attestation.

Observed execution result:

```json
{
  "sizing_planned_shares": 5000,
  "sizing_planned_lots": 50,
  "filled_shares": 2500,
  "fill_status": "SIMULATED_FILLED_JOINT_LOT_CAPACITY_GUARDED",
  "pending_buy_tickers": [],
  "state_positions": [["AAA", 2500]],
  "target_positions": ["AAA"]
}
```

The positive partial fill is not classified as pending. The state-level check only compares ticker membership: because `AAA` exists in `positions`, `target - positions` is empty and no pending buy is required.

## Multi-session and reload blast radius

On the next session, the Decision/execution input held `AAA` as current and target with no new buy intent. The next execution therefore generated no retry and preserved 2,500 shares:

```json
{
  "second_buy_intents": [],
  "second_pending": [],
  "second_position": [["AAA", 2500]]
}
```

The malformed economic state also survived a runtime snapshot round-trip:

```json
{
  "written_position": [["AAA", 2500]],
  "written_pending": [],
  "loaded_position": [["AAA", 2500]],
  "loaded_pending": [],
  "runtime_hash_equal": true
}
```

This is not detected as corruption by the hash chain because the persisted state is internally self-consistent. The defect is semantic: the system lost the residual order obligation before persistence.

## Origin and trigger

1. Sizing uses the EOD reference price and creates `EntrySizing.shares=5000`.
2. Open execution uses `joint_open_allocation`, which recalculates affordable lots at the actual Open/effective price and returns 25 lots.
3. The execution loop creates a pending buy only for `shares <= 0`; it does not compare `shares` with `entry.shares`.
4. The final pending invariant checks only target/position ticker membership, not target quantity or residual planned quantity.

The same trigger can arise from a cash reduction, fee/stamp-duty interaction, or capacity constraint that leaves a positive but incomplete buy fill.

## Defect classification and blast radius

- Classification: **CROSS-COMPONENT DEFECT**, **ECONOMIC / EXECUTION RISK**, and **OBSERVABILITY GAP**.
- Origin: Sizing-to-Open price/capacity mismatch combined with ticker-only pending reconciliation.
- Affected state: position quantity, pending-buy ledger, fill status, residual cash, and future Decision shadow/paper interpretation.
- Behavior: fail-open semantically; no unsafe overspend occurred, but the portfolio silently underinvests.
- Downstream consumers: runtime snapshot/reload, Decision state reconstruction, next-session execution, turnover/fill metrics, NAV/exposure/risk reporting.
- Restart/replay: preserves the wrong but internally hashed state; no automatic repair.
- Existing tests: green but incomplete; no positive-partial-buy assertion.
- Configuration/artifact hashes: do not detect it because all artifacts remain internally consistent.

## Exact implementation evidence

- `src/idx_trade/v4_x1_sizing_v1.py:236-257` — EOD reference price determines desired lots/shares.
- `src/idx_trade/v4_x1_execution_v1_allocator.py:33-146` — Open-price/cash/capacity-aware allocation can return fewer lots than the sizing entry.
- `src/idx_trade/v4_x1_execution_v1.py:353-386` — only zero-share allocation creates `pending_buys`; positive partial allocation is recorded as filled.
- `src/idx_trade/v4_x1_execution_v1.py:417-425` — pending invariant compares ticker sets, not planned versus filled quantity.
- `src/idx_trade/v4_x1_execution_v1.py:426-442` — persisted state stores the partial position without the residual obligation.

Source hashes at audit time:

| File | SHA-256 |
|---|---|
| `src/idx_trade/v4_x1_sizing_v1.py` | `A49C828DCA4E68E18A2260F047CF2BD7647C8FDFBDAB6D59707A014281AD25A9` |
| `src/idx_trade/v4_x1_execution_v1_allocator.py` | `6E315B47B6C87D2D9A921BF1C5142FE3F2E685EE443A20F43171317BEDCA0481` |
| `src/idx_trade/v4_x1_execution_v1.py` | `010567BFD6C9156D5C088A96ECB251ED2074C461CC5C326FCF9C98789AB76FC9` |
| `tests/test_v4_x1_execution_v1.py` | `ABFD3F2C73155C90E1E5B23ED8FE662AF2DA440C0A1958AF90F1CF3DBF6F66E1` |

## Hardening proposal — not applied

The execution state needs a quantity-aware residual contract. At minimum:

1. Treat `0 < filled_shares < planned_shares` as a pending buy with explicit remaining shares/lots.
2. Persist planned, filled, and remaining quantities in the order/fill ledger.
3. Make the final invariant compare target quantity obligations, not only ticker membership.
4. Reconcile residual buys before Decision treats a partially held ticker as complete.
5. Add price-gap, capacity-limited, fee-limited, restart, and replay tests.

Do not patch the incumbent runtime from this lane. Any implementation must be isolated and must preserve the distinction between Decision target membership and execution quantity completion.

## Verdict

**FAIL — POSITIVE PARTIAL BUY IS NOT PERSISTED AS PENDING**

No source, data, provider, cloud, capture, telemetry, or production mutation was performed.
