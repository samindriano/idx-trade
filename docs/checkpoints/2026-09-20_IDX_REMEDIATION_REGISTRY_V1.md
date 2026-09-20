# IDX-Trade Remediation Registry V1

| ID | Finding | Contract state | Implementation state | Required evidence before closure |
|---|---|---|---|---|
| REM-OBL-001 | Positive partial BUY loses residual | `IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / RESTART_OPEN` | Runtime BUY/SELL state, replay, restart, Decision seat semantics |
| REM-OBL-002 | Partial SELL/replacement lacks quantity lineage | `IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / REPLAY_OPEN` | Paired retry/reversal and cancellation lineage |
| REM-STATE-001 | Snapshot omits obligation state | `V2_SCHEMA_IMPLEMENTED` | `IMPLEMENTED_LOCAL / RECOVERY_OPEN` | Versioned snapshot/hash, restart replay, and legacy loader |
| REM-CA-001 | Projected CA state differs from execution parent | `LINEAGE_CONTRACT_IMPLEMENTED_LOCAL` | `IMPLEMENTED_LOCAL / TIMING_MATRIX_OPEN` | Three timing cases plus restart/idempotency |
| REM-EVAL-001 | Execution evidence loses quantity semantics | `UNADJUDICATED` | `UNADJUDICATED` | Versioned evidence schema and structural evaluator replay |
| REM-REC-001 | False reconciliation bit lacks provenance | `UNADJUDICATED` | `UNADJUDICATED` | Typed result, evidence binding, restart/replay |
| REM-ID-001 | Identity normalization/revision splits | `UNADJUDICATED` | `UNADJUDICATED` | Alias, same-class revision, and downstream containment matrix |
| REM-CAUSE-001 | Exposure/cash cause state collapses | `UNADJUDICATED` | `UNADJUDICATED` | Cause-state join with obligations and next Decision |
| REM-LINEAGE-001 | Config/runner identity absent from artifacts | `UNADJUDICATED` | `UNADJUDICATED` | Config mismatch fail-closed across prepare/execute/replay |
| REM-CTRL-001 | Controller phase/attempt held in memory | `UNADJUDICATED` | `UNADJUDICATED` | Fault injection at each side-effect boundary |
| REM-RECOVERY-001 | Latest snapshot rejects without safe recovery | `QUARANTINE_LOCAL_IMPLEMENTED` | `IMPLEMENTED_LOCAL / CONTROLLER_OPEN` | Immutable rejection/quarantine, restart replay, and fork-safe ancestor rules |
| REM-POLICY-001 | Post-entry concentration overlay | `POLICY_BLOCKED` | `POLICY_BLOCKED` | Authoritative policy only; no autonomous overlay |
| REM-POLICY-002 | Dividend tax/net treatment | `POLICY_BLOCKED` | `POLICY_BLOCKED` | Authoritative tax policy only; retain gross semantics |
| REM-EXTERNAL-001 | Unsupported structural CA admission | `EXTERNAL_BLOCKED` | `EXTERNAL_BLOCKED` | External source/authority contract outside this lane |

Status vocabulary is intentionally strict: `UNADJUDICATED` is not a PASS;
`POLICY_BLOCKED` and `EXTERNAL_BLOCKED` are not silently converted into
implementation tasks.
