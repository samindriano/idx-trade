# Contract Adoption Registry V1

Date: 2026-09-21

This registry separates implementation readiness from authority admission and
operational activation. It is outcome-blind and candidate-local.

| Contract | Candidate owner | Hardening evidence | Adoption state | Remaining gate |
|---|---|---|---|---|
| OBLIGATION-V1 | v4_x1_quantity_obligation_v1.py | conservation/replay/restart evidence in completion audit | READY_IN_SOURCE after extraction | candidate test execution and system replay |
| PAPER-STATE-V2 | forward_dividend_runtime_v1_1.py and snapshot consumers | canonical V2 snapshot/restart evidence | READY_IN_SOURCE after extraction | legacy compatibility and migration rehearsal |
| DECISION-SEAT-POLICY-V1 | v4_x1_decision_seat_policy_v1.py | hash-bound policy, typed malformed failures, durable close provenance | FAIL-CLOSED READY_IN_SOURCE | caller policy authorization; no production default |
| CA-SIZING-LINEAGE-V1 | forward_dividend and sizing adapters | raw execution parent/projected NAV separation | READY_IN_SOURCE after extraction | timing replay on candidate |
| CA-TIMING-MATRIX-V1 | v4_x1_ca_timing_matrix_v1.py | pre/decision/execution timing tests | READY_IN_SOURCE after extraction | system replay and no double settlement |
| EXECUTION-EVIDENCE-V2 | v4_x1_execution_evidence_v2.py | quantity-bearing intrinsic replay and parent binding | READY_IN_SOURCE after extraction | evaluator/reconciliation chain replay |
| RECONCILIATION-RESULT-V1 | v4_x1_reconciliation_result_v1.py | typed mismatch/provenance gates | READY_IN_SOURCE after extraction | backward/forward semantic challenge |
| IDENTITY-CANONICAL-V1 | v4_x1_identity_contract_v1.py | alias/revision canonical identity tests | CONTRACT_READY / AUTHORITY_OPEN | external identity artifact only |
| EXPOSURE-CAUSE-V1 | v4_x1_execution_cause_v1.py | bound-zero and cause-obligation joins | READY_IN_SOURCE after extraction | child and restart replay |
| TRANSITION-BINDING-V1 | v4_x1_transition_binding_v1.py | parent/child content binding | READY_IN_SOURCE after extraction | candidate integration |
| RUNTIME-LINEAGE-V2 | v4_x1_runtime_lineage_v2.py | config/runner/branch/commit hash gates | READY_IN_SOURCE after extraction | actual candidate entrypoint audit |
| CONTROLLER-RECOVERY-V1 | e2e_paper_operational_controller_v1.py and v2.py | eight boundary recovery matrix and child interruption | SYNTHETIC_ONLY | candidate replay; no live validation |
| SNAPSHOT-RECOVERY-V1 | snapshot consumers/orchestration | quarantine, ancestor, fork rejection | SYNTHETIC_ONLY | migration and restart rehearsal |
| MIGRATION-PROVENANCE-V1 | v4_x1_migration_provenance_v1.py | immutable source/hash/classification provenance | READY_IN_SOURCE after extraction | source-shape challenge |
| MIGRATION-ACTIVATION-V1 | v4_x1_migration_activation_v1.py | explicit activation decision and legacy authorization | FAIL-CLOSED READY_IN_SOURCE | policy supplied by caller; never automatic |

## Adoption rules

- A contract marked READY_IN_SOURCE is not READY_FOR_SHADOW.
- Identity contract readiness does not admit historical identity authority.
- Synthetic recovery does not prove live scheduler recovery.
- No policy gap is closed by choosing a convenient default.
- The incumbent alpha, Decision V2 science, sizing targets, fee assumptions,
  execution-price semantics, and unsupported-CA fail-closed boundary remain
  unchanged.

