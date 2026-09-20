# IDX Execution State and Paired-Order Identity Audit V1

Date: 2026-09-20  
Audited source lane: detached `runtime/idx-e2e-baseline-paper-v1` at `402fca4b27e91cf8c82d21ff1394ba2d6da73656`  
Documentation lane: isolated `codex/alpha-available-data-20260919`  
Status: **FAIL — EXECUTION IDENTITY/STATE COERCION BOUNDARY**  
Evidence class: synthetic-only, outcome-blind, read-only audit

## Scope and boundary

This audit composes the retained V4-X1 execution contract and dividend-aware runtime loader. The source was inspected and executed in a detached temporary worktree, not in the alpha research worktree or the production/integration checkout. No provider, protected outcome, canonical dataset, capture/cloud runtime, telemetry, or live state was accessed. No runtime source was modified.

## Baseline validation

The exact retained runtime branch passed the existing focused suites:

| Suite | Passed |
|---|---:|
| `test_v4_x1_execution_v1.py` | 8 |
| `test_v4_x1_execution_v1_exit_capacity.py` | 1 |
| `test_v4_x1_execution_v1_allocator_edge.py` | 1 |
| `test_v4_x1_sizing_v1.py` | 7 |
| `test_e2e_paper_orchestration_v1.py` | 21 |
| `test_e2e_paper_operational_controller_v1.py` | 8 |
| `test_e2e_paper_runtime_config_v1.py` | 11 |
| `test_e2e_replay_boundary_v1.py` | 2 |
| **Total** | **59** |

The existing suites cover cash/capacity invariants, partial exits, paired replacement behavior with canonical tickers, runtime orchestration, replay, and restart boundaries. They do not cover fractional position values or noncanonical `replacement_peer` representations.

## Finding A — fractional position coercion changes state

`normalize_state` converts `position.shares` with `int(position.shares)` before enforcing whole-lot validity. A synthetic `PaperPosition("AAA", 100.9)` was accepted and normalized to `{"AAA": 100}`. The whole-lot check then passes, even though the input represented a different holding.

The retained runtime snapshot loader repeats the same behavior at `forward_dividend_runtime_v1_1.py:160` before calling `normalize_state` at line 218. Therefore a malformed persisted numeric share value can be silently truncated during load rather than rejected as a schema error.

This changes portfolio state, not only formatting. A downstream hash is computed from the coerced state, so internal consistency after loading does not prove that the original serialized quantity was valid.

## Finding B — paired replacement can remain pending after a full sell because of alias identity

The execution contract normalizes order/position tickers through `ticker()`, which removes `.JK`, but it preserves `replacement_peer` as raw text in `normalize_pending` and in `_merge_effective_intents`.

Synthetic execution used:

- current holding: `AAA`, 5,000 shares;
- target replacement: `BBB`;
- sell intent: `AAA`;
- buy intent: `BBB` with `replacement_peer="AAA.JK"`;
- sufficient reference-day capacity for the entire `AAA` exit;
- valid Open for both names and `NO_RELEVANT_EVENTS` CA attestation.

Observed result:

```json
{
  "sell_filled_shares": 5000,
  "sell_status": "SIMULATED_FILLED_EXIT_CAPACITY_GUARDED",
  "buy_filled_shares": 0,
  "buy_status": "BLOCKED_BY_UNRESOLVED_PAIRED_SELL_PENDING",
  "positions": [],
  "pending_buys": [{"ticker": "BBB", "replacement_peer": "AAA.JK"}],
  "pending_sells": []
}
```

The paired buy checks `sell_resolution.get(intent.replacement_peer, False)` at `v4_x1_execution_v1.py:328`. The completed sell is keyed as `AAA`, while the lookup asks for `AAA.JK`; the buy is therefore treated as blocked even though the paired sell completed. This is a liveness/underinvestment defect and can create stale pending state. It is conservative rather than an unsafe extra buy, but it violates the intended replacement transition.

## Exact implementation evidence

- `v4_x1_execution_v1_contract.py:107-108` — ticker normalization removes `.JK` from the ticker key.
- `v4_x1_execution_v1_contract.py:139-160` — state normalization casts shares to `int` and then checks whole-lot validity; pending replacement peers are not normalized.
- `v4_x1_execution_v1.py:83-111` — pending intents are merged without canonicalizing `replacement_peer`.
- `v4_x1_execution_v1.py:210-406` — execution applies sell resolution and paired-buy gating.
- `v4_x1_execution_v1.py:328-336` — raw replacement-peer lookup gates the buy.
- `forward_dividend_runtime_v1_1.py:136-160` — persisted position shares are cast with `int()` during reload.
- `forward_dividend_runtime_v1_1.py:218` — reloaded state is validated only after coercion.

Source hashes at audit time:

| File | SHA-256 |
|---|---|
| `src/idx_trade/v4_x1_execution_v1_contract.py` | `0208800825E6F2F91AF9D224D7540E829828379CA332F6630889789C936CF1FE` |
| `src/idx_trade/v4_x1_execution_v1.py` | `010567BFD6C9156D5C088A96ECB251ED2074C461CC5C326FCF9C98789AB76FC9` |
| `src/idx_trade/forward_dividend_runtime_v1_1.py` | `98EBC637340757F03E36C3C8B876F134022CA1282B9BAD35CF573B4B784ECA23` |
| `tests/test_v4_x1_execution_v1.py` | `ABFD3F2C73155C90E1E5B23ED8FE662AF2DA440C0A1958AF90F1CF3DBF6F66E1` |

## Risk interpretation

The retained E2E stack is substantially stronger than a component-only reading: 59 focused tests pass and the normal canonical paired-order scenario behaves correctly. The new probes show that state schema validation and identity normalization are not uniform across all fields. A safe execution design must reject fractional quantities before coercion and use one canonical issuer identity for every relationship field, not only primary ticker keys.

This evidence does not justify changing the incumbent runtime in place. It is a structural finding from accepted typed inputs and synthetic artifacts.

## Hardening proposal — not applied

If implementation is later authorized:

1. Validate that serialized shares are numeric integers before any cast; reject fractional, nonfinite, and bool-like values.
2. Normalize and validate `replacement_peer` at the same boundary as ticker keys, then reject self/unknown/mismatched pair identities.
3. Add full-fill and partial-fill tests with `AAA`/`AAA.JK` permutations.
4. Add a persisted-snapshot round-trip test proving malformed quantities cannot change silently during reload.

Any fix must be made and reviewed in a separate runtime lane. No source change was applied here.

## Verdict

**FAIL — EXECUTION IDENTITY/STATE COERCION BOUNDARY**

No production mutation, canonical-data mutation, cloud/capture action, telemetry action, provider call, or protected-outcome access occurred.
