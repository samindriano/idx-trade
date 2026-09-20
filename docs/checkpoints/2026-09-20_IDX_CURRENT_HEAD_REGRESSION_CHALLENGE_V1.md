# IDX-Trade Current-Head Regression Challenge V1

Date: 2026-09-21
Lane: `codex/idx-contract-hardening-20260920`
Verification revision: `cda6a9e4`

## Boundary

This is a fresh local regression challenge, not an independent reviewer
attestation and not a production-promotion gate. It is synthetic and
outcome-blind: it uses repository tests, temporary fixtures, local subprocesses,
and in-memory contract evidence only. It does not access provider/canonical
data, protected outcomes, cloud/capture, telemetry, scheduler, production, or
alpha state.

## Result

`253/253 PASS`.

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
same-session idempotent write. A tampered latest explicit-close snapshot is
quarantined and the verified partial ancestor is recovered without selecting
the closed artifact.
The runtime-aware wrapper preserves the dividend ledger while delegating all
quantity transition and projection ownership to the base obligation contract.
The V4-X1 Decision adapter also rejects boolean rank values before numeric
coercion, preventing `True` from becoming rank `1`.
Execution state and runtime snapshot decoding now reject non-integer or boolean
position shares before whole-lot validation, preventing lossy `100.9 -> 100`
coercion. Prepared replay now loads and verifies the exact parent snapshot named
by the prepared artifact, reconstructs the embedded Decision plan from that
parent, and rejects a rehashed nested plan while preserving valid idempotent
reruns. The same exact-parent replay gate now covers the nested execution plan;
rehashing a forged execution-plan payload is rejected before idempotent return.
The controller recovery fence now treats an existing `RECOVERY_REQUIRED` status
as terminal on repeated V1/V2 invocations. The latest-snapshot quarantine
manifest is versioned, exact-keyed, entry-order canonical, and authenticated by
its own manifest hash; manifest tampering fails closed.

Explicit Decision-seat closure now requires a caller-supplied,
hash-bound `DecisionSeatClosePolicyV1`. The policy records its authorization
reference and allowed status/reason set, close events persist both the policy
envelope and hash, and restart deserialization re-verifies them. Reusing an
event ID with a different policy is a conflict; missing or unauthorized policy
semantics fail closed. No production status/reason, paired-replacement,
expiry, or `FULL`-quantity policy is chosen by this lane.

The current full repository run collected `891` tests and completed
`891/891 PASS`, with only the three pre-existing pandas `FutureWarning`
records. An intermediate run before the durable policy-envelope hardening hit
the unrelated Windows `PermissionError [WinError 5]` temporary-directory
replace in the capture fixture; its targeted test passed in isolation and the
current full run is clean. No protected/provider/canonical/cloud/capture/
telemetry/scheduler state was accessed.

## Verification command

```text
python -m pytest -q tests/test_v4_x1_decision_seat_policy_v1.py tests/test_v4_x1_quantity_obligation_v1.py tests/test_v4_x1_execution_v1_decision_v2_adapter.py tests/test_v4_x1_execution_v1_exit_capacity.py tests/test_v4_x1_execution_evidence_v2.py tests/test_v4_x1_ca_timing_matrix_v1.py tests/test_v4_x1_identity_contract_v1.py tests/test_v4_x1_identity_evidence_v1.py tests/test_v4_x1_transition_binding_v1.py tests/test_v4_x1_runtime_lineage_v2.py tests/test_v4_x1_migration_provenance_v1.py tests/test_v4_x1_migration_activation_v1.py tests/test_forward_dividend_runtime_v1_1.py tests/test_forward_dividend_orchestration_v1.py tests/test_e2e_paper_orchestration_v1.py tests/test_e2e_paper_operational_controller_v1.py tests/test_e2e_paper_operational_controller_v2.py tests/test_e2e_paper_phase_binding_v1.py tests/test_e2e_paper_runtime_config_v1.py tests/test_e2e_prepared_schedule_binding_v1.py tests/test_decision_v2_minimal.py tests/test_decision_v2_minimal_audit_remediation.py tests/test_v4_x1_decision_v2_minimal.py
```

## Interpretation

The fresh local result closes the stale “current-head challenge refresh”
evidence gap for these synthetic contracts. It does not close external
authorization/adoption, authoritative identity-source provisioning, live
provider/scheduler interruption validation, automatic migration activation, or
Decision-seat/cancellation policy semantics. Those remain fail-closed and
outside this lane except for the hash-bound policy gate; authoritative policy
activation remains outside this lane.
