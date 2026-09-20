# IDX-Trade Independent Challenge Result V2

Date: 2026-09-20
Lane: `codex/idx-contract-hardening-20260920`
Implementation base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
Challenge head: local lane `HEAD` at verification time (recorded by Git)

## Boundary

This challenge is synthetic and outcome-blind. It uses temporary fixtures,
local subprocesses, and in-memory contract evidence only. It does not access
provider/canonical data, protected outcomes, cloud/capture, telemetry,
scheduler, production, or alpha state.

## Gates

| Gate | Evidence | Result |
|---|---|---|
| Nested execution replay | Rehashed nested evidence/CA/cause/lineage parents are rejected | PASS |
| Snapshot recovery | Tampered latest is quarantined; valid fork is rejected | PASS |
| Controller boundaries | All eight V1/V2 boundaries recover to `RECOVERY_REQUIRED` | PASS |
| Real child interruption | Timed-out subprocess leaves `CHILD_EXECUTION` durable and recovery-fenced | PASS |
| Phase runtime binding | All four phase children require config SHA and parent identity | PASS |
| Identity child wiring | Hash-pinned identity artifact validates and reaches orchestration | PASS |
| Identity adversarial cases | File/payload/session/ticker/outcome-access tampering fails closed | PASS |
| Prepared selection | Hash-pinned controller rejects unbound prepared artifacts | PASS |
| Migration provenance | Source hash/classification/provenance remains immutable | PASS |
| Migration activation policy | Legacy requires explicit authorization; orphaned state remains blocked; verified snapshot consumer persists provenance + decision | PASS |

## Verification

```text
python -m pytest -q
```

Result: PASS at 100%, with only the three pre-existing pandas
`FutureWarning` records. Focused new evidence is in:

- `tests/test_e2e_paper_operational_controller_v1.py`;
- `tests/test_e2e_paper_phase_binding_v1.py`;
- `tests/test_v4_x1_identity_evidence_v1.py`;
- `tests/test_v4_x1_migration_activation_v1.py`;
- `tests/test_v4_x1_migration_provenance_v1.py`.

## Limits

This challenge proves the local contracts and recovery behavior. It does not
authorize activation of a real IDX/KSEI identity artifact, automatic legacy
migration policy, provider execution, scheduler execution, or protected
outcome validation. Those remain external/policy-gated by design.
