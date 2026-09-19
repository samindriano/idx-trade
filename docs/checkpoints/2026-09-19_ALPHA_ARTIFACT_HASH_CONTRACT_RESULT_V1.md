# Isolated Alpha Research Artifact Hash Contract — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `I_RESEARCH_INFRASTRUCTURE_HASH_BINDING`  
Status: `PASS_STRUCTURAL_ONLY`

## Finding

Current research outputs already bind code and input identities, but they use
several historical declaration shapes: `source_hashes`, nested `inputs`,
manifest `files`, and direct `*_sha256` fields. Before this checkpoint there
was no reusable fail-closed verifier that normalized these shapes.

The new verifier
`research/verify_alpha_research_artifact_contract_v1.py` accepts only explicit
artifact/code/input/manifest paths. It checks the artifact's declared code
hash, every explicitly requested input hash, conflicting declarations, and an
optional manifest hash. `--require-manifest` makes a missing manifest
declaration or path a hard failure. It performs no discovery and no network,
provider, target, outcome, cloud, capture, telemetry, or production access.

## Validation

The staged Stage-A audit artifact passed with all four declared source hashes
and the builder code hash:

- artifact: `alpha_stage_a_v3_audit.json`
- artifact SHA-256: `f9bfaf368d7157b9b35ff282ffcf18ff06579b9978b5a029609dacc7ecdaa38b`
- verifier code SHA-256: `c587bba69fbfdd77cf9ea4f5ce0dbda191ec5efd191bff55355f0b32cf9ca138`
- generated PASS report:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_stage_a_hash_contract_v1.json`
- generated report SHA-256: `2b8064b51f34b6de084f1facd070cc2288d0270e707c0b6798a3b2e2767615ad`

The Stage-A manifest fixture also passed when its feature file was supplied
through the manifest `files` declaration. Two fail-closed checks were
confirmed:

- substituting legacy `research/alpha_stage_a_v1.py` for the declared builder
  returned `FAIL` with exit code `1`;
- requesting `--require-manifest` for an artifact without a manifest
  declaration returned `FAIL` with exit code `1`.

## Interpretation and boundary

This is reusable provenance/tooling evidence, not PIT admission, source
authority, corporate-action certification, predictive evidence, or model
promotion. The verifier cannot make an undeclared source admissible; it only
fails closed when a caller explicitly requires a missing or mismatched
declaration. Future producers should emit a manifest and invoke
`--require-manifest` when the experiment contract requires one.

## Exact artifact/code location

- isolated code: `research/verify_alpha_research_artifact_contract_v1.py`
- staged output: the external path above; no canonical or production artifact
  was overwritten.
- test state: `py_compile` passed; PASS and deliberate FAIL paths behaved as
  expected.
