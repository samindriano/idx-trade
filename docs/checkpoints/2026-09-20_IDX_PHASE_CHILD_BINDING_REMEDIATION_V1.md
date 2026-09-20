# IDX-Trade Phase Child Runtime Binding Remediation V1

Date: 2026-09-20
Lane: `codex/idx-contract-hardening-20260920`
Base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Scope

This checkpoint records a code-only hardening pass for the four phase child
entrypoints. It does not run the scheduler or provider, access outcomes, or
modify external runtime data, capture, telemetry, cloud, or alpha state.

## Change

`src/idx_trade/e2e_paper_phase_binding_v1.py` adds one mandatory binding gate:

- the child must load the external `config.json` and its SHA sidecar;
- V1 uses the hash-pinned runtime config loader;
- V2 additionally verifies the dual-calendar schedule binding;
- configured branch and commit must equal the parent controller's CLI identity;
- the exact loaded config SHA is passed to `prepare_post_eod` or
  `execute_preopen` and can no longer degrade to `None` when config is absent.

The V1/V2 post-EOD and pre-open scripts fail closed before phase work when this
binding is missing or mismatched. Their existing self entrypoint SHA remains
part of the persisted runtime lineage.

## Evidence

- `tests/test_e2e_paper_phase_binding_v1.py`: mandatory config, identity
  mismatch, missing config, dual-calendar loader, and all-entrypoint AST gates.
- `tests/test_e2e_phase_cli_attestation_v1.py`: existing phase identity wiring
  gates remain passing.
- `python -m pytest -q`: PASS at 100%; only three pre-existing pandas
  `FutureWarning` records were emitted.

The remaining frontier is an independently authorized live child-process
crash/interruption challenge and authoritative identity-source wiring across
all child inputs. No production/provider/scheduler validation is claimed here.
