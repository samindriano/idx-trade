# Execution V1 — Pre Decision V2 Adapter Hard Audit

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`
Audit base after accepted Sizing V1 adapter: `dca239398ddbcf569015418bc1fc05287e7150d7`

## Scope

Audit retained Execution V1 before adapting it from legacy Decision V1 to frozen Decision V2 Minimal. Preserve the already-remediated paper-execution economics unless a concrete defect is found.

## What is already sound and should remain frozen

Retained Execution V1 is the same remediated core that passed the 2026-08-21 hostile audit. Preserve:

- paper-only simulated execution; no broker-fill claim;
- Close(t) sizing reference and Open(t+1) execution base;
- sell-before-buy ordering;
- 15 bps buy fee and 25 bps sell fee;
- 10 bps/side primary slippage assumption;
- Rp10k account-level stamp duty when daily gross turnover is above Rp10m;
- Sizing V1 quantity as a strict BUY upper bound;
- 15% EOD-NAV new-entry cap;
- 1% prior-session regular-market-value BUY and SELL capacity guard;
- whole-lot execution;
- pending transition persistence for missing/zero fills;
- paired replacement BUY blocked until the paired SELL is fully resolved;
- no scientific-shadow mutation to auto-heal paper non-fills;
- state-hash guard between prepared order plan and execution;
- file-backed EOD/Open/CA verification boundary;
- joint fee-aware Open allocator and its low-price/cash-drag remediation.

Historical validation already includes 20k BUY/bootstrap randomized stress plus 10k replacement/exit randomized stress and dedicated partial-exit/capacity/pending tests.

Current Stockbit public fee documentation (checked 2026-08-22) still states 0.15% BUY and 0.25% SELL, and Rp10,000 stamp duty for exchange trade confirmations with total transaction value above Rp10m. Therefore the primary fee/stamp constants are not stale at this audit date.

## Required remediation before E2E execution

### P1 — legacy Decision V1 type/provenance binding

Execution V1 still imports and requires legacy:

- `DecisionPlan`;
- `TradeIntent`;
- `VerifiedDecisionPlan`;
- `_size_entries_for_intents` legacy V1 path;
- config `decision_rule = V4_X1_DECISION_V1`.

Required fix:

- create a Decision-V2-native execution preparation adapter or neutral internal execution-intent contract;
- exact-recompute/verify Decision V2 provenance before execution preparation;
- never project/mislabel a Decision V2 plan as V1;
- keep one execution algorithm rather than duplicate V1/V2 simulators.

### P1 — pending transition reversal is not handled

Current `_merge_effective_intents` correctly retries pending transitions only while they remain aligned with the latest target, but it does not reconcile a target reversal while a transition is pending.

Failure case A:

1. Decision shadow targets A;
2. paper BUY A fails, leaving `pending_buy=A` and no actual A position;
3. next Decision exits/replaces A and emits SELL A;
4. paper has no A shares;
5. current preparation reaches `EXECUTION_V1_EFFECTIVE_SELL_WITHOUT_POSITION`.

Correct paper behavior: cancel the obsolete pending BUY; a shadow-only SELL with no actual shares is already operationally resolved. If a paired replacement BUY points to A, it may proceed subject to normal cash/Open/capacity constraints.

Failure case B:

1. SELL A is pending/partial, so paper still owns A;
2. Decision shadow has already removed A;
3. a later Decision re-enters A and emits BUY A;
4. current execution can attempt BUY while A is already actually held and fail `EXECUTION_V1_BUY_ALREADY_HELD_ACTUAL`.

Correct paper behavior: cancel the obsolete pending SELL and suppress the redundant BUY because actual holdings already satisfy membership. Do not cosmetically top up a partially reduced A position; frozen policy has no HOLD rebalance.

Required regression tests must cover both reversal directions, including paired replacement semantics.

### P1 — paper-state session date is not bound to the Decision session

`PaperPortfolioState.as_of_session_date` is hashed but the base Execution preparation does not require it to equal `decision_session_date`.

A stale/future paper state with coincidentally compatible positions/pending transitions could therefore be prepared against the wrong Decision session.

Required fix:

- validate canonical ISO session date in the base paper-state contract;
- require `paper_state.as_of_session_date == decision_plan.decision_session_date` at prepare time;
- add stale-state and future-state rejection tests.

### P1 E2E evidence blocker — current Open verifier proves file/date, not execution-grade Open semantics

`verify_open_execution_inputs()` currently verifies:

- file existence;
- schema;
- exact execution session date;
- unique ticker rows;
- positive `open` values;
- file SHA.

It does **not** prove that the `open` field came from a frozen source whose semantics are official exchange Open rather than a 09:00 snapshot/first observed trade.

This matters because IDX pre-opening/auction mechanics (IEP/IEV) make a simplistic 09:00 observation semantically unsafe.

The retained `ops/idx-forward-open-archive-v1` archive explicitly writes `execution_grade_promoted = false` and leaves provider selection as a separate frozen-source gate. It therefore must not be silently consumed as Execution-grade Open evidence.

The retained official IDX Stock Summary audit supports positive `OpenPrice` as the only defensible official Open candidate; `FirstTrade` is not an admissible fallback. Historical recovery found positive `OpenPrice` highly consistent with canonical Open but could not recover source rows where official `OpenPrice` was non-positive. For prospective paper this naturally maps non-positive/missing official Open to non-fill/pending semantics.

Required E2E fix:

- bind `VerifiedOpenExecutionInputs` to a source/manifest contract that explicitly certifies official-Open semantics;
- prefer official IDX Stock Summary `OpenPrice` (or another separately frozen equivalent) rather than arbitrary intraday 09:00 data;
- carry provider/source identity and exact artifact/manifest hashes;
- non-positive/missing official Open stays unavailable; never fall back to `FirstTrade` or a nearby tick.

This is a data/provenance admission issue, not a change to the Open-plus-slippage execution model.

### P1 lineage gap — prepared/result artifacts do not yet carry full Decision/Open/CA provenance

`ExecutionOrderPlan` carries EOD artifact/calendar hashes and a state hash, but not an explicit frozen Decision V2 plan identity/hash. `ExecutionResult` records fills and prior-state hash but does not itself carry the exact Open artifact SHA or CA evidence SHA.

For an in-memory unit test this is acceptable; for durable E2E paper evidence it is insufficient if the surrounding orchestrator does not separately bind those identities.

Required integration fix:

- persist exact Decision V2 plan/provenance identity with the prepared order plan;
- bind the verified Sizing V1 plan/config identity;
- persist exact Open source artifact/manifest identity and CA attestation/reconciliation identity with the execution-session manifest/result;
- deterministic rerun must fail closed if any bound input changes.

This may be implemented in the E2E prepared/result envelope rather than by bloating every low-level dataclass, but the provenance must be durable and hash-bound somewhere canonical.

## Downstream accepted components that must be transplanted, not rewritten

The current E2E branch was based on the accepted Decision V2 branch. The later accepted `integration/forward-ca-attestation-v1` branch contains downstream work not yet present here, including:

- hardened forward CA source-chain verification;
- `forward_ca_attestation_v1.py`;
- cash-dividend engine `forward_dividend_v1.py`;
- dividend/CA reconciliation `forward_dividend_execution_v1_1.py`;
- immutable persistent paper runtime `forward_dividend_runtime_v1_1.py`;
- associated regression suites.

These should be selectively transplanted after/alongside the Decision V2 execution adapter. Do not rewrite them from scratch and do not merge the entire divergent branch blindly.

Core Execution V1 itself is the same retained remediated implementation and should remain one simulator.

## Non-blocking / intentional assumptions

- generic errors still use historical `DecisionV1Error` naming;
- 10 bps slippage is explicitly an uncalibrated preregistered paper assumption, not an empirical impact model;
- 1% prior-session value capacity is a conservative feasibility guard, not calibrated market impact;
- same-Open sale proceeds are assumed available as buying power within paper simulation;
- live/manual broker execution is a separate future path and must use actual broker fills, not paper Open fills;
- dividend V1.1 currently records gross paper credit with personal tax treatment unresolved; this is a downstream accounting-policy label, not a core Execution fill bug.

## Audit verdict

Core execution economics/mechanics remain credible and should not be redesigned.

Execution is **not yet E2E-ready** because four concrete remediation areas remain:

1. Decision V2 native provenance/intent adapter;
2. pending-transition reversal reconciliation;
3. exact paper-state/Decision session binding;
4. execution-grade official Open provenance plus durable Decision/Open/CA evidence binding.

Additionally, accepted CA/dividend/runtime components must be selectively transplanted from `integration/forward-ca-attestation-v1`.

`EXECUTION_V1_CORE_RETAIN_ADAPTER_AND_STATE_REVERSAL_FIX_REQUIRED_OFFICIAL_OPEN_PROVENANCE_GATE_REQUIRED_CA_DIVIDEND_TRANSPLANT_REQUIRED`
