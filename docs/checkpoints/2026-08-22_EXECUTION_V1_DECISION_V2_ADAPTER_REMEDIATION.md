# Execution V1 — Decision V2 Adapter Remediation

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`
Audit anchor: `9890498f38e5a1c116f16b80ca3cd614f688396a`
Validated implementation HEAD: `8d081191ed883954e074e60f1d860e2064c5931e`

## Scope

Remediate the three code-level blockers found in the pre-adapter Execution V1 audit without changing the already hostile-audited Execution V1 economics/mechanics.

## Implemented

### 1. Decision V2-native preparation adapter

Added `src/idx_trade/v4_x1_execution_v1_decision_v2_adapter.py`.

The adapter consumes `VerifiedDecisionV2SizingPlan`, whose provenance is established by exact Decision V2 recomputation in the accepted Sizing adapter. It never relabels or projects a Decision V2 plan as `V4_X1_DECISION_V1`.

Execution mechanics remain the existing `V4_X1_EXECUTION_V1` contract. Decision V2 intents are converted only into the existing mechanical BUY/SELL intent shape after V2 provenance has been verified.

A separate hash-pinned adapter contract is frozen in:

- `config/v4_x1_execution_v1_decision_v2_adapter.json`
- `src/idx_trade/v4_x1_execution_v1_decision_v2_config.py`

This preserves the legacy Execution V1 config/implementation unchanged while making the active V2 compatibility boundary explicit.

### 2. Pending-transition reversal reconciliation

Before preparing paper orders, the V2 adapter now requires:

`DecisionV2.current_shadow_positions == actual positions - pending sells + pending buys`

This makes the scientific shadow / executable-paper relationship explicit and fail-closed.

Two previously broken reversal cases are handled:

- prior BUY pending, Decision later SELLs the never-acquired ticker:
  - stale pending BUY is canceled;
  - no impossible SELL is prepared;
  - if a replacement BUY was paired to that SELL, the absent never-held peer is treated as already operationally resolved so the replacement is not falsely blocked;
- prior SELL pending, Decision later BUYs the still-held ticker:
  - stale pending SELL is canceled;
  - no redundant BUY is prepared;
  - actual holding is retained as-is; there is no cosmetic top-up/rebalance.

Any reversal that is not explainable by the current Decision intent plus persisted pending transition fails closed.

### 3. Exact paper-state / Decision session binding

The V2 execution preparation path now requires:

`paper_state.as_of_session_date == DecisionV2.decision_session_date`

A stale/future paper state cannot be prepared merely because its positions happen to be compatible.

## Regression locks added

`tests/test_v4_x1_execution_v1_decision_v2_adapter.py` covers:

- a real exact-verified Decision V2 bootstrap entering Execution preparation without V1 rule projection;
- stale paper-state session rejection;
- pending BUY -> current SELL reversal;
- paired replacement BUY proceeds when its would-be SELL peer was never actually held;
- pending SELL -> current BUY reversal;
- Decision shadow / paper-plus-pending lineage mismatch rejection.

`tests/test_v4_x1_execution_v1_decision_v2_config.py` locks the adapter contract SHA and semantics.

## Fresh local validation — PASS

Validated on exact branch/head:

- branch: `integration/idx-e2e-baseline-paper-v1`
- HEAD: `8d081191ed883954e074e60f1d860e2064c5931e`
- clean temporary worktree; active checkout untouched
- py_compile/import smoke: **PASS**
- focused tests: **53 passed, 0 failed, 0 skipped**
- `git diff --check`: **PASS**

Explicitly validated:

- legacy Execution V1 regressions: PASS;
- legacy Sizing V1 regressions: PASS;
- Decision V2 sizing adapter regressions: PASS;
- verified Decision V2 -> Execution preparation: PASS;
- pending BUY -> SELL cancellation: PASS;
- pending SELL -> BUY cancellation: PASS;
- paired replacement guard after never-held sell peer: PASS;
- stale/wrong PaperState rejection: PASS;
- Decision shadow lineage guard: PASS;
- adapter config SHA verification: PASS;
- fee/slippage/capacity behavior unchanged: PASS.

No files were modified by validation, no commits/pushes were made, no provider calls were made, and protected forward outcomes were not accessed.

## Explicit non-changes

This remediation does **not** change:

- 15 bps BUY fee;
- 25 bps SELL fee;
- 10 bps/side paper slippage assumption;
- Rp10k stamp duty threshold semantics;
- sell-before-buy;
- joint Open allocator;
- Sizing V1 math or 10%/15% rules;
- 1% prior-session regular-market-value capacity guard;
- missing Open -> pending;
- partial sell capacity behavior;
- base CA semantics;
- paper-only/non-broker-fill status.

The hostile-audited legacy `prepare_execution_v1` core remains intentionally unchanged. E2E Decision V2 must enter through the accepted adapter.

## Still open before whole-stack E2E acceptance

1. **Execution-grade official Open provenance.** Generic file/date verification is not enough; arbitrary 09:00/intraday observations remain inadmissible. Official `OpenPrice` (or separately frozen equivalent) must be source-bound, with missing/non-positive Open remaining unavailable.
2. **Selective transplant of accepted forward CA/cash-dividend/persistent runtime** from `integration/forward-ca-attestation-v1`.
3. **Durable E2E prepared/result envelopes** must bind exact Decision V2, Sizing, Open and CA evidence identities/hashes.

These are integration/evidence tasks. No known core Sizing or Execution algorithm defect remains from this remediation.

## Final verdict

`EXECUTION_V1_DECISION_V2_ADAPTER_LOCAL_VALIDATION_PASS_READY_FOR_OPEN_CA_INTEGRATION`
