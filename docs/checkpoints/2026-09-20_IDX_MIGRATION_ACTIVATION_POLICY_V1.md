# IDX-Trade Migration Activation Policy V1

Date: 2026-09-20
Lane: `codex/idx-contract-hardening-20260920`
Base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Contract

`src/idx_trade/v4_x1_migration_activation_v1.py` adds an explicit decision
surface between migration provenance and any future runtime activation:

- `MIGRATION_ALREADY_COMPATIBLE` → `ACTIVATE_COMPATIBLE`;
- `MIGRATION_REQUIRES_LEGACY_MODE` → `REQUIRES_AUTHORIZATION` unless the
  caller supplies an explicit policy with `allow_legacy_mode: true`;
- `UNKNOWN_ORPHANED_PARTIAL` and other reconciliation-required states →
  `BLOCKED_RECONCILIATION` even when legacy mode is authorized.

Both the policy and decision are canonical-hash-bound, outcome-blind, and
persisted immutably/idempotently. The decision function does not mutate a
runtime snapshot or activate a scheduler/provider path.

## Evidence

`tests/test_v4_x1_migration_activation_v1.py` covers denied/authorized legacy
mode, compatible state, orphaned-state blocking, and immutable decision replay.
Together with `tests/test_v4_x1_migration_provenance_v1.py`, the focused migration
suite passes.

The remaining item is external adoption of an authorized policy for a real
runtime. No such policy or source artifact is invented or activated in this
lane.
