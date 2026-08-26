# V4-X1 Prospective Pre-Access Adapter V1 — Final Narrow Hardening

Date: 2026-08-26 (Asia/Jakarta)  
Branch: `ops/v4-x1-prospective-preaccess-readiness-v1`  
Implementation/remediation commit: `a1038ae4ba6fcbe6bd4ad0e72e6c230f00705464`  
Status: `V4_X1_PREACCESS_ADAPTER_V1_MERGE_REVIEW_READY`

## Scope and boundary

This is outcome-blind, metadata-only adapter hardening. It does not modify
the pure evaluation core, frozen V4-X1 science, protected gate, deployed
runtime, scheduler, counter state, model, Decision, sizing, Execution, or
target producer. No provider call, score projection against real rows, target
materialization, target-value read, protected-loader call, or protected
outcome access occurred. `coordination/TEAM_STATUS.md` was not modified;
MAIN remains its owner.

## Production score projection

`project_score_frame_to_gate_shape()` now accepts the verified production
14-column V4-X1 score superset and selects exactly one `date` or
`session_date`, `ticker`, and `alpha_consensus`. It preserves row order,
ticker values, and alpha values; it performs no reranking or transformation.
It fails closed on ambiguous/missing date identity, missing required columns,
forbidden outcome-like columns or metadata, invalid/multiple session dates,
duplicate ticker identity, invalid tickers, and non-finite scores.

The synthetic production-shape test uses the actual 14-column output schema
and proves the resulting frame is exactly the frozen three-column gate shape.
The helper remains disconnected from real score rows; no projection artifact
has been published.

## Inventory identities

The report and counter adapter distinguish:

- `rolling_partial_inventory_sha256`: path-aware operational discovery hash;
- `production_source_gate_shape_sha256`: exact gate-shaped identity of the
  currently discovered production-source artifacts;
- `canonical_admitted_gate_inventory_sha256`: the identity that a future
  published gate-compatible projection/manifest may admit.

For the current runtime, the exact values are:

- rolling partial: `3510e5b73189e97bc6f40fd96190164d193aceb45d969d55099e0e70221b89ee`;
- production source gate shape:
  `5d829936646e2cf2acc1e2ea3d8c8352fd2bf9e18e10c1d858244d869e6d8cff`;
- canonical admitted gate inventory: `NOT_AVAILABLE`.

The second value is not a final canonical admission. The runtime counter is
not bound to either raw identity (`canonical_inventory_sha256_binding=false`)
and can only bind a future canonical admitted identity. Artifact-SHA and
manifest-SHA mutation tests prove that the generic gate identity helper
changes whenever either projected artifact identity changes, while the helper
still reproduces the frozen `_inventory_hash()` for an actually gate-shaped
inventory.

## Independent code-pin trust anchor

Before trusting declarations inside
`config/v4_x1_prospective_evaluation_code_pin_v1.json`, the adapter now
requires the independently frozen manifest SHA:

`0012dc4822f676388c427e018c63873b9450ee6cc6067cd67638a439a7f0f65b`

The manifest must also contain exactly
`CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1` as
`target_identity.canonical_target_id`. A modified manifest with internally
consistent rewritten declarations remains `PROVENANCE_INVALID` because its
bytes no longer match the independent trust anchor. Guard metadata is
explicitly treated as safety metadata; production score evidence separately
rejects token-contained forbidden metadata such as
`realized_return_summary`, `target_value_preview`, and
`outcome_statistics`.

## Accumulation-state semantics

The adapter now preserves the pure-core maturity precedence:

- fewer than 100 sessions + missing score admission =>
  `ACCUMULATING_OUTCOME_BLIND`;
- 100/100 mature + missing score admission =>
  `PREACCESS_REQUIREMENTS_INCOMPLETE`;
- fewer than 100 sessions + provenance invalid =>
  `PREACCESS_PROVENANCE_INVALID`.

The real audit therefore remains accumulation, not a premature component-
missing terminal status.

## Real local metadata-only audit

Audit output:
`C:\Users\Sam\AppData\Local\Temp\idx-v4-x1-preaccess-final-7b54202a3f334dda9d3f8d8bacba523d.json`  
Audit SHA-256:
`6a0e975d49aa9ee8a8f9efccafe5b46cf101b044a165769d826b7b3a8294effb`

Observed runtime facts:

- production sessions: `2/100`, `2026-08-21` and `2026-08-24`;
- raw production evidence: `READY`;
- raw production schema: the verified 14-column V4-X1 superset;
- production-source gate admission: `NOT_AVAILABLE`, projection required;
- counter: `2/100`, remaining `98`, `ACCUMULATING`;
- calendar: `READY`, 10 official sessions from `2026-08-10` through
  `2026-08-24`;
- code pins: `READY`, independent manifest trust anchor verified;
- target attestation: `NOT_AVAILABLE`,
  `SEALED_PROSPECTIVE_TARGET_MATERIALIZER_OR_ATTESTATION_NOT_FOUND`;
- overall readiness: `ACCUMULATING_OUTCOME_BLIND`;
- all provider/target/outcome/runtime mutation guards: `false`.

## Validation

- focused adapter tests: `28 passed`;
- focused core/readiness/gate/preflight/evaluator/target tests:
  `145 passed`;
- full pytest: `223 passed`, exit `0`;
- py_compile/import smoke: `PASS`;
- git diff --check: `PASS`;
- provider calls: `FALSE`;
- protected outcome access: `FALSE`;
- target materialization: `FALSE`;
- counter/runtime/scheduler mutation: `FALSE`.

## Decision

`V4_X1_PREACCESS_ADAPTER_V1_MERGE_REVIEW_READY`

The lane is ready for independent review only. It does not authorize a real
score projection, target production, protected access, canonical counter
reset/binding, runtime deployment, or scheduler change.
