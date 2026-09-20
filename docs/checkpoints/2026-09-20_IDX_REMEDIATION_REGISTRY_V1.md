# IDX-Trade Remediation Registry V1

| ID | Finding | Contract state | Implementation state | Required evidence before closure |
|---|---|---|---|---|
| REM-OBL-001 | Positive partial BUY loses residual | `IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / RESTART_OPEN` | Runtime BUY/SELL state, replay, restart, Decision seat semantics |
| REM-OBL-002 | Partial SELL/replacement lacks quantity lineage | `IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / REPLAY_OPEN` | Paired retry/reversal and cancellation lineage |
| REM-STATE-001 | Snapshot omits obligation state | `V2_SCHEMA_IMPLEMENTED` | `IMPLEMENTED_LOCAL / RECOVERY_OPEN` | Versioned snapshot/hash, restart replay, and legacy loader |
| REM-CA-001 | Projected CA state differs from execution parent | `LINEAGE_CONTRACT_IMPLEMENTED_LOCAL` | `TIMING_MATRIX_IMPLEMENTED_LOCAL / ARTIFACT_REPLAY_OPEN` | Three timing cases, additive CA extension, and restart/idempotency |
| REM-EVAL-001 | Execution evidence loses quantity semantics | `EVIDENCE_V2_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / REPLAY_GATES_IMPLEMENTED` | Versioned evidence artifact, structural evaluator replay, nested parent hash, and independent challenge |
| REM-REC-001 | False reconciliation bit lacks provenance | `RESULT_V1_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / REPLAY_GATES_IMPLEMENTED` | Typed result, evidence binding, nested replay, and independent challenge |
| REM-ID-001 | Identity normalization/revision splits | `IDENTITY_CONTRACT_IMPLEMENTED_LOCAL` | `TRANSITION_BINDING_IMPLEMENTED_LOCAL / OPERATIONAL_SOURCE_OPEN` | Alias, same-class revision, and child-consumer replay with authoritative identity source |
| REM-CAUSE-001 | Exposure/cash cause state collapses | `CAUSE_V1_IMPLEMENTED_LOCAL` | `TRANSITION_BINDING_IMPLEMENTED_LOCAL / REPLAY_MATRIX_OPEN` | Cause-to-obligation join, retry transition, and child-consumer replay |
| REM-LINEAGE-001 | Config/runner identity absent from artifacts | `LINEAGE_V2_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / OPERATIONAL_BINDING_OPEN` | Config mismatch fail-closed across prepare/execute/replay |
| REM-CTRL-001 | Controller phase/attempt held in memory | `RECOVERY_FENCE_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / FAULT_MATRIX_OPEN` | Fault injection at each side-effect boundary |
| REM-RECOVERY-001 | Latest snapshot rejects without safe recovery | `QUARANTINE_LOCAL_IMPLEMENTED` | `IMPLEMENTED_LOCAL / CONTROLLER_OPEN` | Immutable rejection/quarantine, restart replay, and fork-safe ancestor rules |
| REM-POLICY-001 | Post-entry concentration overlay | `POLICY_BLOCKED` | `POLICY_BLOCKED` | Authoritative policy only; no autonomous overlay |
| REM-POLICY-002 | Dividend tax/net treatment | `POLICY_BLOCKED` | `POLICY_BLOCKED` | Authoritative tax policy only; retain gross semantics |
| REM-EXTERNAL-001 | Unsupported structural CA admission | `EXTERNAL_BLOCKED` | `EXTERNAL_BLOCKED` | External source/authority contract outside this lane |

Status vocabulary is intentionally strict: `UNADJUDICATED` is not a PASS;
`POLICY_BLOCKED` and `EXTERNAL_BLOCKED` are not silently converted into
implementation tasks.
