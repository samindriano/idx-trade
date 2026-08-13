# Schema Hardening V2 — Review Handoff

Status: `REVIEW_ROUND_2`

Branch: `integration/schema-hardening-v2`

Independently verify closure of the seven findings from review round 1 before the next integration phase.

Scope remains offline contract/schema/storage preparation only. Do not perform network/account access or modify the existing public Ownership/KSEI lane.

## Findings to re-check

1. `COMPLETE` requires explicit success and row-accounting evidence for every required endpoint class.
2. History has concrete atomic uniqueness plus immutable append-only behavior; newer partial observations do not replace last-good complete state.
3. Reviewed source commit pins cannot be mutated after construction.
4. Canonical minimization rejects unnecessary identity/session material and requires backend-derived opaque subaccount references.
5. Runtime Python validation and checked-in Draft 2020-12 schema are kept in parity, including timezone-aware timestamp format checks and exact source pins.
6. Decimal representation-only scale does not alter canonical hashes/dedup keys, and large monetary values must not be misclassified as account identifiers.
7. Duplicate holdings and duplicate cash identities are rejected.

## Files

- `src/idx_trade/personal_portfolio/surface.py`
- `src/idx_trade/personal_portfolio/snapshot.py`
- `src/idx_trade/personal_portfolio/types.py`
- `src/idx_trade/personal_portfolio/validation.py`
- `src/idx_trade/personal_portfolio/schema.py`
- `src/idx_trade/personal_portfolio/store.py`
- `src/idx_trade/personal_portfolio/__init__.py`
- `schemas/personal_portfolio_snapshot_v1.schema.json`
- `tests/test_snapshot_hardening.py`
- `tests/test_snapshot_enrichment_boundary.py`
- `docs/checkpoints/2026-08-14_AKSES_ADAPTER_SCHEMA_HARDENING_V2.md`
- `pyproject.toml`

The earlier monolithic `contracts.py` and `storage.py` were superseded and removed; runtime imports now flow only through the modules above.

## Review checks

Run the focused tests, compile/import validation, JSON-schema parsing, schema/runtime parity and round-trip checks. Adversarially test completeness evidence, concurrent duplicate append, mutation/deletion rejection, source-pin immutability, opaque subaccount enforcement, sensitive-value minimization, decimal canonicalization including a large IDR amount, and duplicate positions/cash.

Confirm Investment Health remains separate from short-horizon Trading Opportunity and no automatic action field is introduced.

Compare the branch to latest main and confirm no public Ownership/KSEI, Corporate Action PIT, Financial PIT, Foreign Flow, model, protected-outcome, or UI scope changed.

Behavioral source pins remain:

- `nichsedge/ksei-mcp@a3dfd3260889d704b75001387b646c25b4b69aa3`
- `chickenzord/goksei@5e51319feb3d373e463c21dfca5c31f971335653`

No upstream implementation code was copied.

## Verdict gate

Return either:

- `ACCEPTED_FOR_BOUNDED_REAL_AUTH_TEST_DESIGN`, or
- `REWORK`, with severity, exact failure path, and recommended fix.

Acceptance is only a gate to design one bounded private/no-persist integration check. It does not authorize public endpoints/UI, automated provider collection, historical scheduling, or automatic investment/trading actions.
