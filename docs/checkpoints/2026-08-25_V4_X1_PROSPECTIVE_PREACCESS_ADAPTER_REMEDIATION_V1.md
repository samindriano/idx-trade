# V4-X1 Prospective Pre-Access Adapter V1 — Remediation

Date: 2026-08-25 (Asia/Jakarta)  
Branch: `ops/v4-x1-prospective-preaccess-readiness-v1`  
Parent reviewed HEAD: `f482717a3ed320e21f20ecb672544fa5035e5d58`  
Status: `V4_X1_PREACCESS_ADAPTER_V1_REMEDIATED_REVIEW_READY`

## Boundary

This remediation remains outcome-blind and metadata-only. It does not modify
the pure readiness core, frozen evaluator/gate, model, Decision, sizing,
Execution, runtime, scheduler, counter, or TEAM_STATUS. It performs no
provider calls, target materialization, target-value reads, protected-loader
calls, or outcome access.

## Production score evidence versus final-gate admission

The two real V4-X1 production score manifests are valid production evidence
and their declared score artifact bytes were re-hashed. Their production
schema is `v4_x1_prospective_score_manifest_v2` with model identity,
freshness, inputs, science, model-bundle, PIT diagnostics, guards, and output
metadata. The declared output columns are:

`ticker`, `date`, `raw_control_h5`, `alpha_control_h5`, `raw_control_h10`,
`alpha_control_h10`, `alpha_control_consensus`, `raw_challenger_h5`,
`alpha_h5`, `raw_challenger_h10`, `alpha_h10`, `alpha_consensus`,
`rank_consensus`, `rank_control_consensus`.

The frozen final gate accepts exactly one date/session-date column plus
`ticker` and `alpha_consensus`. Therefore production evidence is
`READY`, but `score_gate_admission` is explicitly `NOT_AVAILABLE` until a
future deterministic projection selects exactly those score-side columns,
publishes an immutable derived artifact and gate-compatible manifest, and
binds both source hashes. The projection contract is exact column selection;
it does not rerank, transform, infer, or read outcomes. The helper is present
for synthetic testing only and was not run against real score rows.

Frozen ranking semantics are verified metadata-only either from an explicit
manifest ranking or from the exact production consensus formula plus the
rank-consensus output identity. This proves the production science identity,
not final-gate admission.

## Inventory identities

The adapter now exposes two distinct identities:

- `rolling_partial_inventory_sha256` — path-aware rolling identity retained
  for operational discovery;
- `gate_shape_inventory_sha256` — exact final-gate record projection of
  `forward_position`, `session_index`, `session_date`,
  `score_artifact_sha256`, and `score_manifest_sha256`; filesystem paths are
  intentionally excluded.

For the current two discovered sessions:

- rolling/path-aware SHA: `3510e5b73189e97bc6f40fd96190164d193aceb45d969d55099e0e70221b89ee`;
- gate-shape SHA: `5d829936646e2cf2acc1e2ea3d8c8352fd2bf9e18e10c1d858244d869e6d8cff`.

Synthetic regression proves that relocating only local paths changes the
rolling identity but leaves the gate-shape identity unchanged. The gate-shape
implementation was cross-checked against the frozen gate hash formula.

## Counter reconciliation

The runtime status reports target `100`, completed `2`, and sessions in strict
order `2026-08-21`, `2026-08-24`. The exact production score discovery finds
the same two sessions in the same order, with no duplicate dates, so the
runtime status is `ACCUMULATING`, not a canonical attestation. It is not bound
to the rolling hash. A future `100/100` runtime status without a separate
inventory-bound counter attestation is classified `PENDING_EXPECTED`, not
false `READY`; contradictory sessions/counts are `PROVENANCE_INVALID`.

## Official calendar verification

The existing official IDX schedule is verified against its actual CSV and
summary, including ordered session identity, no duplicate/malformed dates,
declared count, first/last coverage, and the exact session-list hash.

- calendar CSV SHA: `5067282f8a0be19da7babe372ac78bc2f6a6ab5e46e7a803c710aea09c9c6cdd`;
- summary SHA: `151986e8b456d209b83dfe2148704c8cf97f9dc00bb1ce539027991350afa0ab`;
- declared/verified session-list SHA:
  `5c729b4e40aebcb8dc053b2bdf6322984f390dd6d1a11ff1f65abdf2415ad070`;
- count: `10`; coverage: `2026-08-10` through `2026-08-24`.

Hash, count, boundary, order, and malformed-date adversarial cases fail
closed.

## Code-pin verification

The frozen code-pin manifest is verified outcome-blind, including schema and
blocked status, exact model identity, protocol/evaluator/gate Git blob SHA-1,
contract SHA-256, target-construction SHA-256/Git blob/source-commit format,
target-spec SHA-256, and the access policy:

- `real_loader_allowed = false`;
- `real_outcome_marker_allowed = false`;
- `protected_outcomes_accessed = false`;
- `requires_explicit_human_authorization = true`.

Code-pin blob/target-source/access-policy mutations are `PROVENANCE_INVALID`.
Current code-pin manifest SHA:
`0012dc4822f676388c427e018c63873b9450ee6cc6067cd67638a439a7f0f65b`.

## Discovery boundary and target architecture

Score discovery now opens only the exact
`*/v4_x1_clean_geometry3_prospective_v1/manifest.json` path pattern. An
unrelated model manifest is not opened. Optional component discovery skips
protected subtrees whose path components contain outcome/label/realized/vault
or equivalent protected tokens before reading any file content.

The active `v4_x1_canonical_target_v1.py` remains the outcome-free semantic
and code pin. The retained `ranking_v4_3_target_execution.py` is not promoted
into this control plane: executing it computes raw realized H5/H10 returns and
is outcome-bearing. The sealed future architecture is:

`retained/pinned historical target semantics -> separately reviewed isolated
sealed producer -> protected target store -> public metadata-only target
attestation -> readiness adapter`.

No sealed producer/attestation pair is present in the audited active/runtime
shapes, so `target_attestation` remains:
`NOT_AVAILABLE / SEALED_PROSPECTIVE_TARGET_MATERIALIZER_OR_ATTESTATION_NOT_FOUND`.
Target values remain `PROTECTED_NOT_READ`.

## Real outcome-blind report

Audit output SHA:
`1f2ba78d1b28dae6fc274a408bd8d60e3e074e2a66f86e8a722b10e4e991e3db`.

- overall: `PREACCESS_REQUIREMENTS_INCOMPLETE`;
- verified production score sessions: `2/100`;
- score gate admission: `NOT_AVAILABLE`;
- counter: `ACCUMULATING`;
- calendar: `READY`;
- code pins: `READY`;
- target attestation: `NOT_AVAILABLE`;
- PaperState/session audit, benchmark, and prior-access audit: not available;
- all outcome/provider/runtime mutation guards: `false`.

## Validation

- focused adapter tests: `20 passed`;
- focused adapter/core/gate/preflight/evaluator/target tests: `137 passed`;
- full pytest: `215 passed`, exit `0`;
- py_compile/import smoke: PASS;
- `git diff --check`: PASS.

## Decision

`V4_X1_PREACCESS_ADAPTER_V1_REMEDIATED_REVIEW_READY`

This is review-ready metadata/control-plane remediation only. It does not
authorize score projection against real rows, target production, protected
access, counter mutation, or runtime deployment.
