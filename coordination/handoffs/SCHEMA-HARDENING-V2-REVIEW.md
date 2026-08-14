# Schema Hardening V2 — Review Handoff

Status: `REVIEW_ROUND_4`

Branch: `integration/schema-hardening-v2`

Review round 3 returned `REWORK` for three branch-local mechanical blockers after the semantic design itself passed adversarial review. This handoff asks for a narrow independent acceptance rerun. Scope remains offline contract/schema/storage preparation only. Do not perform network/account access and do not modify the existing public Ownership/KSEI lane.

## Round-3 blockers remediated

1. **Checked-in JSON Schema parse/parity**
   - Fixed the missing closing object delimiter in `$defs.endpoint_evidence.allOf[1]`.
   - The artifact is intended to remain byte-structure-equivalent in meaning to `PERSONAL_PORTFOLIO_SNAPSHOT_SCHEMA_V1` from `schema.py`.
   - Re-run `json.loads`, Draft 2020-12 schema parsing, and the existing checked-in/runtime parity assertion on the exact HEAD.

2. **Canonical payload deepcopy safety**
   - `jsonable()` now converts any remaining `str` subclass to a built-in plain `str` after the `StrEnum` branch.
   - Therefore `SubaccountRef` does not escape into canonical dictionaries as a constructor-guarded subclass.
   - Added a focused regression asserting exact built-in `str` type and successful `deepcopy()`.

3. **Subaccount error-message compatibility**
   - `PortfolioPosition` and `CashBalance` retain the stronger factory-origin rule.
   - Their rejection message now explicitly says `server-derived keyed-HMAC reference from derive_subaccount_ref`, preserving both the new factory contract and prior diagnostic expectation.

## Previously accepted semantic behavior to preserve

- bare Draft 2020-12 validation rejects naive timestamps;
- canonical semantic validation rejects endpoint arithmetic mismatch, failed-endpoint nonzero rows, duplicate holdings/cash, detail-count mismatch, invalid completeness, backwards timestamps, and arbitrary summary counts such as `999`;
- `PORTFOLIO_SUMMARY` remains provisional fail-closed V1 semantics: one aggregate row per represented non-empty canonical asset class;
- plain shape-valid `ksa_<64hex>` strings are rejected at Python ingestion; factory-derived references are accepted;
- `from_canonical_json()` round-trip remains allowed only after canonical validation;
- append-only storage, immutable pins, minimization, decimal canonicalization, provider-neutral boundary, and Investment Health vs Trading Opportunity separation remain unchanged.

## Files changed only for round-3 remediation

- `schemas/personal_portfolio_snapshot_v1.schema.json`
- `src/idx_trade/personal_portfolio/validation.py`
- `src/idx_trade/personal_portfolio/types.py`
- `tests/test_subaccount_ref_factory.py`

No auth/provider transport, API/UI, public Ownership/KSEI, Financial PIT, Corporate Actions, Foreign Flow, model, or protected-outcome file is part of this remediation.

## Required acceptance rerun

Run:

- focused personal-portfolio tests;
- full pytest;
- compile/import checks;
- checked-in JSON parse;
- runtime Draft 2020-12 schema parse;
- checked-in schema vs runtime schema parity;
- canonical round-trip/deepcopy paths;
- `git diff --check`;
- scope diff against latest main.

Known unrelated repository failure may still exist at `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` (2 historical conflicts versus expected 1). Report it separately; it is not an AKSes acceptance blocker unless behavior changed in this branch.

## Validation disclosure from remediation agent

This ChatGPT runtime cannot execute the repository checkout because outbound Git access is unavailable. Remote diff/content inspection was performed, but **no new pytest pass count is claimed**. The independent runner must verify the exact branch HEAD.

No KSEI login, credential access, provider call, or real portfolio data was used.

## Verdict gate

Return one of:

- `ACCEPTED_FOR_BOUNDED_REAL_AUTH_TEST_DESIGN`
- `REWORK`, with severity, exact path/line/failure mode, and minimal fix.

Acceptance authorizes only design of one bounded private/no-persist real-auth check. It does not itself authorize credential use, provider execution, public APIs/UI, scheduled collection, or automatic investment/trading actions.
