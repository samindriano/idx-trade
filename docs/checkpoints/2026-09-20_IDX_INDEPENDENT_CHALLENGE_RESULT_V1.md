# IDX-Trade Post-Implementation Independent Challenge Result V1

Date: 2026-09-20
Lane: `codex/idx-contract-hardening-20260920`
Implementation base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
Challenge head: `9e89de12`

## Scope and boundary

This is a synthetic, outcome-blind post-implementation challenge. It uses only
temporary test artifacts and in-memory contract evidence. It does not access
provider, canonical data, protected outcomes, cloud/capture, telemetry,
scheduler, or production state.

## Challenge gates

| Gate | Adversarial mutation | Expected result | Observed |
|---|---|---|---|
| Nested execution evidence | Change nested evidence, recompute only the outer execution hash | Reject evidence parent mismatch | PASS |
| Runtime lineage contract | Change timing contract link, recompute lineage and outer hashes | Reject lineage contract mismatch | PASS |
| Reconciliation CA parent | Change reconciliation source hash, recompute reconciliation, lineage, and outer hashes | Reject CA parent mismatch | PASS |
| Cause-obligation join | Change a cause row ID and recompute evidence/reconciliation/lineage/outer hashes | Reject cause-binding row mismatch | PASS |
| Decision identity replay | Omit identity evidence, then provide a source-hash-tampered identity row | Reject missing/tampered identity evidence | PASS |
| Latest snapshot | Tamper latest snapshot with a verified ancestor available | Quarantine latest and recover exact ancestor | PASS |
| Snapshot fork | Create a valid but non-ancestor competing history | Reject fork; never choose arbitrarily | PASS |
| Operational lineage | Change bound runtime config hash on replay | Reject config mismatch | PASS |
| Controller V1/V2 boundaries | Persist each of eight side-effect boundaries as `RUNNING` | Recover to `RECOVERY_REQUIRED` with boundary metadata and no provider/outcome access | PASS |
| Migration provenance | Tamper source snapshot or provenance payload | Reject; immutable same-bytes write remains idempotent | PASS |

## Executed verification

The complete repository suite was run after the replay/cause hardening:

```text
python -m pytest -q
```

Result: PASS at 100%, with three pre-existing pandas `FutureWarning` records
only (`curated_identity.py` and `tradability_anchor_reconstruction.py`).

Focused challenge coverage is implemented in:

- `tests/test_e2e_paper_orchestration_v1.py`;
- `tests/test_e2e_paper_operational_controller_v1.py`;
- `tests/test_e2e_paper_operational_controller_v2.py`;
- `tests/test_v4_x1_migration_provenance_v1.py`;
- `tests/test_forward_dividend_runtime_v1_1.py`.

## Interpretation

The local contract/replay surfaces pass the post-implementation challenge.
This is not production promotion. Authorized automatic migration activation,
authoritative identity-source wiring through live child scripts, and any
live/provider or protected-outcome validation remain outside this lane.
