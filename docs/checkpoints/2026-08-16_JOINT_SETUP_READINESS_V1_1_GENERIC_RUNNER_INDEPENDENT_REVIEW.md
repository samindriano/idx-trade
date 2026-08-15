# Joint Setup Readiness V1.1 Generic Runner — Independent Review

Status: `JOINT_SETUP_READINESS_V1_1_GENERIC_RUNNER_PARENT_SEMANTIC_REMEDIATION_REQUIRED`

Reviewed implementation:
`integration/joint-setup-readiness-v1-1-generic-runner-v1@6d416f080482a4d1ebfa4c096c51ad565465e249`

Accepted controlled-runtime parent:
`integration/joint-setup-readiness-v1-1-forward-v1@8ede786622713b03127fbf856abe2d7d2bd5c03d`

## Accepted findings

- session-parametric source/feature resolution is implemented;
- V1.1 fingerprint and Price-domain subset policy remain frozen;
- domain counts and state distributions are dynamic;
- the accepted 2026-08-12 -> 2026-08-13 artifact pair replays unchanged with `created=false` and stable hashes;
- immutable partial/conflicting-output handling is fail-closed;
- no scheduler/provider/outcome/model/O2/repository-hygiene work occurred.

## Blocking issue: parent verification is self-consistency, not full semantic provenance

The generic runner dynamically hashes parent bytes, but its new parent checks do not yet re-establish the accepted upstream semantic provenance strongly enough for scheduler use.

### Price State

`_verify_price_source()` validates output schema, allowed state domains, manifest state-distribution summaries, and hashes of files named in `input_provenance`. It does **not** recompute Price State from the verified causal HLCV/context or invoke the accepted strict Price State verifier.

Therefore a self-consistent **valid-state** tamper can evade the current check: change a row from one allowed trend/confirmation state to another allowed value, rewrite the parquet, update `artifact_sha256` and `state_distributions` in the Price manifest, and keep the unchanged input-provenance files. The generic parent check has no independent recomputation tying the changed state row back to those inputs.

The existing adversarial test does not cover this case: it changes `trend_state` to `NOT_A_FROZEN_STATE`, so rejection proves enum/domain validation rather than semantic provenance.

### Foreign Flow Setup / Representation V2

`_verify_foreign_flow_source()` correctly recomputes Setup State from the referenced Representation V2 artifact. However the Representation V2 pair itself is only checked for path/hash/session/schema-level consistency here; the generic runner does not invoke the accepted Representation V2/Setup strict verifier or independently re-establish its raw/canonical provenance.

Thus a self-consistent mutation of Representation V2, followed by regeneration of Setup State and corresponding representation/setup manifest hash updates, can remain internally consistent while no longer being tied to the originally verified source evidence. The existing test mutates Setup State while leaving Representation V2 unchanged, so it does not exercise this stronger adversarial case.

The same root problem applies to calendar/input identities: hashing whatever a mutually rewritten parent manifest declares is not equivalent to re-establishing accepted upstream provenance.

## Required remediation before scheduler integration

1. Reuse/import the accepted strict Foreign Flow prospective verifier (Representation V2 + Setup State provenance) or implement an equivalent verifier that reaches the accepted raw/canonical source evidence. Do not stop at Setup-vs-Representation reproducibility.
2. Reuse/import the accepted strict Price State verifier that recomputes/re-establishes the state artifact from its causal market/context lineage. Do not stop at schema/distribution plus declared input hashes.
3. Only after those strict parent verifiers pass should the generic joint runner derive dynamic parent SHA identities and build/verify the joint artifact.
4. Add adversarial tests proving rejection of:
   - Price State changed to a *different valid frozen state*, with artifact SHA and manifest distributions consistently rewritten;
   - Representation V2 changed within valid feature domains, Setup State regenerated from it, and both representation/setup manifest hashes consistently rewritten;
   - parent calendar/provenance identity rewritten self-consistently without accepted upstream authority.
5. Preserve the accepted compatibility replay exactly: existing 2026-08-13 joint artifact/manifest hashes must remain unchanged and `created=false`.

## Verdict

`JOINT_SETUP_READINESS_V1_1_GENERIC_RUNNER_PARENT_SEMANTIC_REMEDIATION_REQUIRED`

No scheduler hook is authorized yet. This review does not invalidate the already accepted controlled 2026-08-13 joint artifact or the V1.1 contract/domain semantics.
