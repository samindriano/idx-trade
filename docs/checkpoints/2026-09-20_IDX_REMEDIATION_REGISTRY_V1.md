# IDX-Trade Remediation Registry V1

| ID | Finding | Contract state | Implementation state | Required evidence before closure |
|---|---|---|---|---|
| REM-OBL-001 | Positive partial BUY loses residual | `IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / RESTART_OPEN` | Runtime BUY/SELL state, replay, restart, Decision seat semantics |
| REM-OBL-002 | Partial SELL/replacement lacks quantity lineage | `IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / REPLAY_OPEN` | Paired retry/reversal and cancellation lineage |
| REM-STATE-001 | Snapshot omits obligation state | `V2_SCHEMA_IMPLEMENTED` | `IMPLEMENTED_LOCAL / CANONICAL_REPLAY_GATED / RECOVERY_OPEN` | Versioned snapshot/hash, canonical payload replay, restart replay, and legacy loader |
| REM-MIG-001 | Legacy migration decision lacks durable provenance | `PROVENANCE_V1_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / POLICY_GATE_IMPLEMENTED_EXTERNAL_ADOPTION_OPEN` | Immutable source/hash/classification artifact, explicit policy-gated activation decision, and verified-snapshot consumer; external policy adoption |
| REM-CA-001 | Projected CA state differs from execution parent | `LINEAGE_CONTRACT_IMPLEMENTED_LOCAL` | `TIMING_MATRIX_IMPLEMENTED_LOCAL / REPLAY_GATES_IMPLEMENTED` | Three timing cases, additive CA extension, and restart/idempotency |
| REM-EVAL-001 | Execution evidence loses quantity semantics | `EVIDENCE_V2_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / CROSS_PARENT_REPLAY_GATES_CHALLENGE_PASS` | Versioned evidence artifact, structural evaluator replay, nested parent hash, cross-parent lineage, and challenge record |
| REM-REC-001 | False reconciliation bit lacks provenance | `RESULT_V1_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / CROSS_PARENT_REPLAY_GATES_CHALLENGE_PASS` | Typed result, evidence/CA/session binding, nested replay, and challenge record |
| REM-ID-001 | Identity normalization/revision splits | `IDENTITY_CONTRACT_IMPLEMENTED_LOCAL` | `TRANSITION_BINDING_IMPLEMENTED_LOCAL / HASH_PINNED_CHILD_WIRING_TESTED / AUTHORITY_OPEN` | Alias, same-class revision, hash-pinned child-consumer artifact, and eventual authoritative identity source |
| REM-CAUSE-001 | Exposure/cash cause state collapses | `CAUSE_V1_IMPLEMENTED_LOCAL` | `TRANSITION_BINDING_IMPLEMENTED_LOCAL / REPLAY_ROW_GATES_TESTED` | Cause-to-obligation join, retry transition, and child-consumer replay |
| REM-LINEAGE-001 | Config/runner identity absent from artifacts | `LINEAGE_V2_IMPLEMENTED_LOCAL` | `BOUND_REPLAY_TESTED / CHILD_RUNTIME_BINDING_AND_SELECTION_TESTED` | Config mismatch and unbound prepared-artifact rejection across prepare/execute/replay |
| REM-CTRL-001 | Controller phase/attempt held in memory | `RECOVERY_FENCE_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / V1_V2_BOUNDARY_MATRIX_AND_SYNTHETIC_SUBPROCESS_CHALLENGE_PASS` | Any separately authorized live protected-runtime validation |
| REM-RECOVERY-001 | Latest snapshot rejects without safe recovery | `QUARANTINE_LOCAL_IMPLEMENTED` | `IMPLEMENTED_LOCAL / ORCHESTRATION_BOUND` | Immutable rejection/quarantine, restart replay, and fork-safe ancestor rules |
| REM-POLICY-001 | Post-entry concentration overlay | `POLICY_BLOCKED` | `POLICY_BLOCKED` | Authoritative policy only; no autonomous overlay |
| REM-POLICY-002 | Dividend tax/net treatment | `POLICY_BLOCKED` | `POLICY_BLOCKED` | Authoritative tax policy only; retain gross semantics |
| REM-EXTERNAL-001 | Unsupported structural CA admission | `EXTERNAL_BLOCKED` | `EXTERNAL_BLOCKED` | External source/authority contract outside this lane |

Status vocabulary is intentionally strict: `UNADJUDICATED` is not a PASS;
`POLICY_BLOCKED` and `EXTERNAL_BLOCKED` are not silently converted into
implementation tasks.
