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
- synthetic two-session partial SELL retry reloads the V2 snapshot before
  retry, then completes the paired replacement BUY with both quantity
  obligations reaching `FILLED`;
- duplicate fill and cancellation idempotency;
- state hash includes obligations only when the new contract is present;
- obligation deserialization replays the canonical payload builder and rejects
  hash-valid/noncanonical field extensions;
- old snapshot payloads still load without an obligation section;
- V1 → V2 snapshot chain loads with immutable parent binding;
- legacy classifier returns `UNKNOWN_ORPHANED_PARTIAL` without quantity fabrication;
- `MIGRATION_PROVENANCE-V1` records source artifact/schema, source state hash
  when valid, classification/disposition/reason, UTC decision time, and
  optional runtime lineage; its writer is immutable and idempotent;
- tampered latest snapshot is quarantined and a verified ancestor is recovered;
- synthetic recovery also preserves the verified ancestor's partial obligation
  ledger, position, and pending projection;
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
- orchestration replay requires persisted Decision identity evidence and
  rejects missing or source-hash-tampered identity rows;
- `CA_TIMING_MATRIX-V1` classifies payment-before-decision,
  payment-on-decision, payment-on-execution, and later payment boundaries;
  prepared matrices accept only hash-bound additive CA extensions;
- CA timing payload verification now enforces canonical envelope/row shape,
  ordered event identity, ISO dates, hash fields, and timing/action semantics;
- persisted execution replay now rechecks nested evidence, reconciliation,
  timing, and runtime-lineage parents and rejects a recomputed outer hash over
  tampered nested evidence;
- `RECONCILIATION_RESULT-V1` verification now validates canonical dates,
  hash-shaped provenance fields, normalized ticker sets, coverage inclusion,
  and mismatch-row shape before accepting a hash-valid PASS payload;
- `EXPOSURE_CAUSE-V1` now distinguishes unavailable position state from a
  bound zero position, so entry and full-exit deltas are explicit `0 -> fill`
  and `held -> 0` transitions;
- replay now also cross-checks runtime-lineage contract/artifact links,
  reconciliation CA parents, and evidence/reconciliation session parents;
- replay validates cause-obligation binding payloads, execution-session scope,
  cause/join row identity, and recomputed obligation join content before
  accepting a child artifact;
- persisted orchestration replay rejects a hash-valid obligation payload with
  a noncanonical nested field;
- `RUNTIME_LINEAGE-V2` binds implementation/config/entrypoint/artifact hashes,
  and interrupted controller `RUNNING` state fences to `RECOVERY_REQUIRED`;
- runtime-lineage verification now rejects hash-valid but noncanonical binding
  status/field combinations by replaying the builder normalization;
- operational `BOUND` lineage is persisted and rechecked across synthetic
  prepare/execute/replay, with config mismatch rejected;
- hash-pinned controller selection now rejects prepared artifacts whose
  operational runtime lineage is missing or unbound;
- all four V1/V2 phase child entrypoints now require the external hash-pinned
  runtime config, require its branch/commit identity to match the parent
  controller, and pass the non-null config SHA into orchestration;
- an independent synthetic subprocess timeout now proves the durable
  `CHILD_EXECUTION` boundary remains `RUNNING` and the next controller pass
  returns `RECOVERY_REQUIRED` without replaying provider/outcome work;
- caller-supplied identity evidence is now an optional but hash-pinned runtime
  config input; all four phase children validate its file/payload/session and
  required-ticker resolution before passing it to Decision identity binding;
- migration activation now has an explicit immutable policy/decision gate and a
  verified-snapshot consumer: compatible state may activate, legacy mode
  requires explicit authorization, and orphaned/reconciliation-required state
  remains blocked; provenance and the decision are persisted separately without
  mutating runtime state;
- orchestration state loading consumes verified-ancestor snapshot recovery;
- dual-calendar V2 controller preserves the same durable recovery boundary
  metadata across all eight synthetic side-effect boundaries without provider
  or outcome access, and its no-certified-Open missed-execution branch now
  reuses the exact schedule-bound prepared parent;
- latest-snapshot recovery rejects noncanonical snapshot filenames with a
  typed fail-closed error instead of leaking an untyped sorting failure;
- snapshot loading replays the canonical snapshot builder and rejects a
  hash-valid but noncanonical payload envelope;
- post-implementation independent challenge record V2 is PASS for nested replay,
  lineage, CA, cause, identity, snapshot, migration, and V1/V2 controller gates;
  see `2026-09-20_IDX_INDEPENDENT_CHALLENGE_RESULT_V2.md`;
- exact base/runtime lineage remains recorded;
- current HEAD full repository regression via `python -m pytest -q` passed at
  100% with only three pre-existing pandas `FutureWarning` records; two
  earlier reruns encountered unrelated Windows `PermissionError [WinError 5]`
  atomic-replace fixture flakes in capture and official-open tests, and each
  targeted recheck passed;
  direct `pytest -q` invocation has a pre-existing root-namespace collection
  issue for tests importing `scripts.*`.

## Remaining evidence before Phase 4

- external authorization/adoption of the migration activation policy (the
  local immutable policy/decision gate and verified-snapshot consumer are
  implemented);
- authoritative identity-source provisioning/activation and policy approval;
- live provider/scheduler crash/interruption validation is not authorized in
  this lane; the synthetic subprocess challenge is PASS;
- external/policy-gated activation and any live protected-runtime validation;
  synthetic independent challenge V2 is recorded in
  `2026-09-20_IDX_INDEPENDENT_CHALLENGE_RESULT_V2.md`.
