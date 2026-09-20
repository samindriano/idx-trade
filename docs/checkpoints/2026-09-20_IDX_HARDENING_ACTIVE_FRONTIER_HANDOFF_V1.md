# IDX-Trade Hardening Active Frontier Handoff V1

Date: 2026-09-20  
Lane: `codex/idx-contract-hardening-20260920`  
Base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Current frontier

`restart/fault-injection + latest-snapshot recovery → Decision seat semantics → CA composition`

## Immediate sequence

1. Add restart/replay and fault-injection coverage around obligation snapshots.
2. Add immutable latest-snapshot quarantine/recovery and fork-safe selection.
3. Complete Decision seat/reversal semantics without retuning Decision rules.
4. Add migration artifact provenance and legacy classification persistence.
5. Only then move to CA composition and projected-vs-raw state lineage.

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
- exact base/runtime lineage remains recorded.
- full repository regression: `pytest -q` PASS; only three pre-existing pandas
  `FutureWarning` records, no test failures.

## Required handoff evidence before Phase 3

- restart/fault-injection replay;
- restart/fault-injection and latest-snapshot quarantine/recovery;
- migration artifact provenance;
- Decision seat/reversal semantics;
- CA timing and projected/raw state binding.
