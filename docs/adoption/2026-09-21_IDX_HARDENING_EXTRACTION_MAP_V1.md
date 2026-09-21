# Clean Hardening Extraction Map V1

Date: 2026-09-21 (Asia/Jakarta)

Source evidence:

- hardening source: 8ceec523d49500949b5ecf46e3b862cd4eb1c4fd;
- hardening base: 402fca4b27e91cf8c82d21ff1394ba2d6da73656;
- hardening history: 109 commits after the base;
- candidate branch: codex/idx-authoritative-runtime-adoption-20260921;
- candidate base: 402fca4b27e91cf8c82d21ff1394ba2d6da73656.

The old hardening branch is immutable development evidence. This map defines
the clean extraction; it is not a request to merge that branch.

## Extraction groups

| Planned clean commit | Final adoption payload | Hardening provenance | Original finding | Contract IDs |
|---|---|---|---|---|
| adopt: contract primitives and canonical identity | v4_x1_quantity_obligation_v1.py; v4_x1_identity_contract_v1.py; v4_x1_identity_evidence_v1.py; v4_x1_transition_binding_v1.py; matching tests | 30fa0ca5, 31588283, 78e104bc, 903d7df5, 21aa8c98, 3a0fa978, 7ccc3055 | ticker-only state loss, identity/revision split, unbound transition | OBLIGATION-V1, IDENTITY-CANONICAL-V1, TRANSITION-BINDING-V1 |
| adopt: execution evidence, causes, reconciliation | v4_x1_execution_evidence_v2.py; v4_x1_execution_cause_v1.py; v4_x1_reconciliation_result_v1.py; matching tests | e33fcee8, 4317f1dd, 6fc43f0a, e04fd005, 1f0d64f3, e65356f2, 55d98cbc | quantity semantics lost in evaluation; false reconciliation bit; collapsed exposure/cash causes | EXECUTION-EVIDENCE-V2, EXPOSURE-CAUSE-V1, RECONCILIATION-RESULT-V1 |
| adopt: CA and durable runtime lineage | v4_x1_ca_timing_matrix_v1.py; v4_x1_runtime_lineage_v2.py; v4_x1_migration_provenance_v1.py; v4_x1_migration_activation_v1.py; matching tests | 504d717f, 607f4972, 569651f5, 2d4e46e5, 0d7a0352, 4430b6a6, dffd70c9, 066c47ff, 4ac55fdc | raw/projected CA ambiguity, missing config/runner identity, unsafe legacy migration | CA-SIZING-LINEAGE-V1, CA-TIMING-MATRIX-V1, RUNTIME-LINEAGE-V2, MIGRATION-PROVENANCE-V1, MIGRATION-ACTIVATION-V1 |
| adopt: decision, execution, sizing, and dividend integration | modified forward_dividend modules; v4_x1_decision_v2_minimal.py; v4_x1_decision_seat_policy_v1.py; v4_x1_execution modules; v4_x1_sizing_v1_decision_v2_adapter.py; associated tests | ddc673b3, e5040346, e945166a, 3b5d5e4c, d57ec5d0, a8d5bafe, 938c8bc9, cda6a9e4, 5d42f9bd | residual/reversal/close semantics and policy provenance not durable | PAPER-STATE-V2, DECISION-SEAT-POLICY-V1, OBLIGATION-V1, EXECUTION-EVIDENCE-V2 |
| adopt: snapshot recovery and controller fences | modified e2e_paper_operational_controller_v1.py, e2e_paper_operational_controller_v2.py, e2e_paper_orchestration_v1.py, e2e_paper_runtime_config_v1.py; controller/orchestration tests | 66e11fb9, 2907a64b, 2aa210bf, 7969a07d, bb5bce56, 3b8ef010, 824c6bf6, d173ec2c, c91e2895, 42b9c63d, 5a85b1d3, ee4837da, 6b83def1, 1a1fe463 | in-memory controller state and unsafe latest-snapshot recovery | CONTROLLER-RECOVERY-V1, SNAPSHOT-RECOVERY-V1, PAPER-STATE-V2 |
| adopt: phase-child binding and identity injection | e2e_paper_phase_binding_v1.py; modified four phase scripts; phase/identity tests | a6702aeb, 26d8399c, cfd5e594, 7ccc3055 | child can run with wrong config/branch or interrupted boundary | RUNTIME-LINEAGE-V2, IDENTITY-CANONICAL-V1, CONTROLLER-RECOVERY-V1 |
| adopt: top-level replay and completion policy gates | modified top-level scripts/tests plus policy/replay assertions | 600866ae, 8f80b275, f9d323bd, 563e781f, e65356f2, d2388f37, 1cf774f3, 8ceec523 | component-green but semantically disconnected replay; close policy provenance | all contracts above; no new science |
| adopt: evidence-only packet | lineage matrix, registry, migration/compatibility/rollback/policy docs, completion/challenge references | 8ceec523 plus hardening checkpoint history | loss of provenance during extraction | MIGRATION-PROVENANCE-V1, RUNTIME-LINEAGE-V2 |

## Source inventory

### Required runtime sources

src/idx_trade additions:

- v4_x1_ca_timing_matrix_v1.py
- v4_x1_decision_seat_policy_v1.py
- v4_x1_execution_cause_v1.py
- v4_x1_execution_evidence_v2.py
- v4_x1_identity_contract_v1.py
- v4_x1_identity_evidence_v1.py
- v4_x1_migration_activation_v1.py
- v4_x1_migration_provenance_v1.py
- v4_x1_quantity_obligation_v1.py
- v4_x1_reconciliation_result_v1.py
- v4_x1_runtime_lineage_v2.py
- v4_x1_transition_binding_v1.py
- e2e_paper_phase_binding_v1.py

Modified runtime sources are listed by group above; no source outside those
groups is a dependency until the import and test graph proves it.

### Required tests

The candidate must carry the matching contract tests, controller/orchestration
tests, phase binding tests, modified Decision/Execution/Dividend tests, and
the hardening challenge tests. A test name is not evidence unless it executes
against the candidate checkout.

### Evidence-only files

Hardening completion audits, handoffs, no-retry logs, and challenge records are
review artifacts. They must remain available for provenance but must not become
runtime imports or activation inputs.

### Excluded from runtime extraction

Historical/debug-only notebooks, protected-outcome tooling, provider/capture
helpers, scheduler installers, and production/cloud workflow changes remain
excluded unless a later compatibility audit proves an explicit candidate
dependency. No external data or artifact is copied into this branch.

## Extraction acceptance

The clean extraction is accepted only when:

1. each planned commit has a disjoint, reviewable file set;
2. the final candidate source matches the intended final hardening files;
3. provenance points back to the hardening commit(s) and finding;
4. candidate tests run on the candidate branch;
5. no live or protected surface is touched.

Until those checks run, extraction status is IN PROGRESS.

