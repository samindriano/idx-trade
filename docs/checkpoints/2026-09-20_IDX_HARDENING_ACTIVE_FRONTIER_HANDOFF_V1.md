# IDX-Trade Hardening Active Frontier Handoff V1

Date: 2026-09-20  
Lane: `codex/idx-contract-hardening-20260920`  
Base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Current frontier

`CA/accounting projected-vs-raw state → execution evidence → reconciliation provenance`

## Immediate sequence

1. Compose CA settle/sizing/execution timing with obligation state and restart.
2. Add quantity-bearing execution evidence and structural evaluator replay.
3. Add reconciliation result provenance and typed mismatch detector.
4. Bind identity, exposure/cash causes, and config/artifact lineage into all
   operational consumers and Decision transitions.
5. Complete controller side-effect fault matrix, latest-snapshot controller
   integration, and final independent challenge.

## Do not do yet

- Do not implement post-entry concentration overlay.
- Do not choose dividend tax/net policy.
- Do not add external broker reconciliation.
- Do not add unsupported structural-CA authority.
- Do not touch protected outcomes, production, canonical data, cloud/capture,
  telemetry, scheduler, counters, or incumbent alpha/model science.

## Completed evidence in this lane

- OBLIGATION-V1 source and invariant tests;
- `v4_x1_quantity_obligation_v1.py` SHA-256:
  `bf7c708c1a2be8b5d7519d8728985cc987d966b783d14e58f4e52524e2df19d6`;
- old positive partial BUY regression corrected and passing;
- zero-fill/partial SELL/replacement neighboring tests;
- duplicate fill and cancellation idempotency;
- state hash includes obligations only when the new contract is present;
- old snapshot payloads still load without an obligation section;
- V1 → V2 snapshot chain loads with immutable parent binding;
- legacy classifier returns `UNKNOWN_ORPHANED_PARTIAL` without quantity fabrication;
- `MIGRATION_PROVENANCE-V1` records source artifact/schema, source state hash
  when valid, classification/disposition/reason, UTC decision time, and
  optional runtime lineage; its writer is immutable and idempotent;
- tampered latest snapshot is quarantined and a verified ancestor is recovered;
- valid forked histories remain blocked;
- Decision V2 residual BUY retry works with an existing partial position;
- CA sizing lineage keeps the immutable raw state as `ExecutionOrderPlan.state_hash`
  and records projected total-return sizing separately;
- projected CA state is restricted to cash/ledger changes and a trade-state
  mutation fails closed;
- `EXECUTION_EVIDENCE-V2` now carries per-fill quantities, parent/state hashes,
  state transition replay, turnover, pending, and reconciliation checks;
- `RECONCILIATION_RESULT-V1` now records the internal detector, CA source and
  attestation hashes, evidence hash, typed mismatches, and explicitly marks
  broker reconciliation as not performed;
- identity alias/revision intervals and unresolved lookup are fail-closed;
- execution evidence emits structured exposure/cash cause records with
  remainder and next-action semantics;
- `TRANSITION_BINDING-V1` resolves Decision tickers against caller-supplied
  identity evidence and joins positive-quantity causes to the exact
  same-session obligation, exposing `RETRY_OBLIGATION` without changing
  Decision math;
- `CA_TIMING_MATRIX-V1` classifies payment-before-decision,
  payment-on-decision, payment-on-execution, and later payment boundaries;
  prepared matrices accept only hash-bound additive CA extensions;
- persisted execution replay now rechecks nested evidence, reconciliation,
  timing, and runtime-lineage parents and rejects a recomputed outer hash over
  tampered nested evidence;
- `RUNTIME_LINEAGE-V2` binds implementation/config/entrypoint/artifact hashes,
  and interrupted controller `RUNNING` state fences to `RECOVERY_REQUIRED`;
- operational `BOUND` lineage is persisted and rechecked across synthetic
  prepare/execute/replay, with config mismatch rejected;
- orchestration state loading consumes verified-ancestor snapshot recovery;
- exact base/runtime lineage remains recorded;
- full repository regression: `pytest -q` PASS; only three pre-existing pandas
  `FutureWarning` records, no test failures.

## Remaining evidence before Phase 4

- independent challenge of execution/reconciliation evidence and the new
  migration provenance artifact;
- authorized automatic migration activation/persistence policy (the explicit
  verified-snapshot consumer is implemented);
- operational use of identity evidence and cause joins through every child
  script, including persisted replay/tamper coverage;
- child-process runtime binding and V2 controller crash/recovery parity;
- independent final challenge.
