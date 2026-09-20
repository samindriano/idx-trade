# IDX-Trade Current-Head Regression Challenge V1

Date: 2026-09-20
Lane: `codex/idx-contract-hardening-20260920`
Verification revision: `5a85b1d3`

## Boundary

This is a fresh local regression challenge, not an independent reviewer
attestation and not a production-promotion gate. It is synthetic and
outcome-blind: it uses repository tests, temporary fixtures, local subprocesses,
and in-memory contract evidence only. It does not access provider/canonical
data, protected outcomes, cloud/capture, telemetry, scheduler, production, or
alpha state.

## Result

`206/206 PASS`.

The suite covers the latest top-level replay envelope hardening, active
obligation reversal fail-closed behavior, persisted quantity obligations,
explicit cancellation/relinquishment replay, execution evidence, CA timing,
identity/transition binding, runtime lineage, migration provenance/activation,
dividend runtime/orchestration, and E2E controller/orchestration boundaries.
The state-level explicit-close API is parent-hash bound and its compatibility
projections are rebuilt from the canonical obligation ledger. Identical close
events replay idempotently against the post-transition state; altered event
bytes or a mismatched pre-transition parent remain rejected. The explicit-close
state also round-trips through the V2 runtime snapshot writer/loader with a
same-session idempotent write.

The full repository command was also attempted twice after this test addition.
Both runs reached the end of the suite but encountered the known Windows
`PermissionError [WinError 5]` atomic-publish race in unrelated tests: once in
`tests/test_official_open_evidence_v1.py` and once in
`tests/test_capture_forward_ca_idx_bei.py`. The first failure test passed when
run in isolation. No contract-hardening test failed; the bounded 204-test
result above is the current clean evidence for this lane.

## Verification command

```text
python -m pytest -q tests/test_v4_x1_quantity_obligation_v1.py tests/test_v4_x1_execution_v1_decision_v2_adapter.py tests/test_v4_x1_execution_v1_exit_capacity.py tests/test_v4_x1_execution_evidence_v2.py tests/test_v4_x1_ca_timing_matrix_v1.py tests/test_v4_x1_identity_contract_v1.py tests/test_v4_x1_identity_evidence_v1.py tests/test_v4_x1_transition_binding_v1.py tests/test_v4_x1_runtime_lineage_v2.py tests/test_v4_x1_migration_provenance_v1.py tests/test_v4_x1_migration_activation_v1.py tests/test_forward_dividend_runtime_v1_1.py tests/test_forward_dividend_orchestration_v1.py tests/test_e2e_paper_orchestration_v1.py tests/test_e2e_paper_operational_controller_v1.py tests/test_e2e_paper_operational_controller_v2.py tests/test_e2e_paper_phase_binding_v1.py tests/test_e2e_paper_runtime_config_v1.py tests/test_e2e_prepared_schedule_binding_v1.py
```

## Interpretation

The fresh local result closes the stale “current-head challenge refresh”
evidence gap for these synthetic contracts. It does not close external
authorization/adoption, authoritative identity-source provisioning, live
provider/scheduler interruption validation, automatic migration activation, or
Decision-seat/cancellation policy semantics. Those remain fail-closed and
outside this lane.
