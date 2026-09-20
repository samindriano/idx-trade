# IDX-Trade Identity Evidence Child Wiring V1

Date: 2026-09-20
Lane: `codex/idx-contract-hardening-20260920`
Base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Scope

This is a code-only, outcome-blind wiring contract. It does not discover or
download identity data, invoke a provider, access outcomes, or mutate any
external runtime, canonical, capture, cloud, telemetry, scheduler, or alpha
state.

## Contract

`src/idx_trade/v4_x1_identity_evidence_v1.py` consumes only a caller-supplied
JSON artifact whose runtime config declares both an absolute path and its
SHA-256. The loader requires:

- `idx_trade_security_identity_evidence_v1` schema;
- exact file SHA and canonical payload SHA;
- explicit `source_reference` and `outcome_access: false`;
- exact as-of session date;
- validated `SecurityIdentityV1` rows with source references/evidence hashes;
- successful resolution of every required execution ticker.

The four V1/V2 phase scripts obtain this artifact through the hash-pinned
runtime config and pass the validated rows to `prepare_post_eod` or
`execute_preopen`. Missing, stale, tampered, session-drifted, or incomplete
identity evidence fails closed. When the config does not provide an identity
artifact, no identity is fabricated; existing replay gates still reject a
prepared artifact that requires identity evidence.

## Evidence

- `tests/test_v4_x1_identity_evidence_v1.py`: file/payload/session/ticker/
  outcome-access gates pass.
- `tests/test_e2e_paper_phase_binding_v1.py`: runtime binding and all four
  child-to-orchestration identity wiring gates pass.
- `tests/test_e2e_paper_runtime_config_v1.py`: config path/SHA pair and invalid
  pair gates pass.
- `python -m pytest -q`: full regression PASS after this change.

This proves the child-consumer wiring only. Selection and activation of an
authoritative IDX/KSEI identity artifact remains policy/source work outside
this lane and is not claimed complete.
