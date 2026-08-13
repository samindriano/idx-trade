# Schema Hardening V2 — Review Handoff

Status: `REVIEW_ROUND_3`

Branch: `integration/schema-hardening-v2`

Review round 2 returned `REWORK` with three P1 findings. This handoff asks for an independent round-3 review of the remediation only. Scope remains offline contract/schema/storage preparation. Do not perform network/account access and do not modify the existing public Ownership/KSEI lane.

## Round-2 findings to re-check

1. **Timezone parity**
   - Runtime Draft 2020-12 schema now requires an explicit `Z` or numeric UTC offset in addition to `format: date-time`.
   - The shared semantic validator independently parses timestamps and rejects naive values.
   - `fetched_at >= snapshot_at` is also enforced on direct canonical payloads.
   - Adversarial test directly instantiates `Draft202012Validator(..., FormatChecker())` and verifies a naive timestamp fails.

2. **One authoritative semantic gate for canonical payloads**
   - `validate_snapshot_payload()` now runs structural schema validation, minimization checks, then `validate_snapshot_semantics()`.
   - The Python `PortfolioSnapshot` object path delegates its cross-field checks to the same semantic validator.
   - Shared semantics enforce successful endpoint arithmetic `observed = accepted + rejected`, failed-endpoint zero-row constraints, duplicate positions/cash rejection, detail endpoint accepted-row reconciliation, completeness evidence, and timestamp ordering.
   - New direct malformed-payload tests exercise these conditions rather than relying only on dataclass constructors.

3. **`PORTFOLIO_SUMMARY` accounting**
   - V1 now freezes summary semantics as one aggregate row per represented non-empty canonical asset class (cash plus distinct non-cash classes present in the snapshot).
   - `PORTFOLIO_SUMMARY.accepted_rows` is reconciled against that count; an arbitrary value such as `999` is rejected.
   - This is intentionally fail-closed and provisional. The reviewed unofficial clients expose category aggregates, but no real account response has been inspected. If one bounded sanitized real response later proves that zero-value categories are always returned, revise this contract through review rather than silently broadening it.

## Additional hardening

The round-2 note about `ksa_...` shape-only validation was also addressed at the Python ingestion boundary:

- `derive_subaccount_ref()` now returns a dedicated `SubaccountRef` string subtype that can only be constructed with a private module factory token.
- `PortfolioPosition` and `CashBalance` reject ordinary strings even when they syntactically match `ksa_<64hex>`.
- Canonical deserialization first validates the persisted payload, then uses an internal rehydration path for the already-validated opaque reference.
- A focused regression test rejects a manually supplied shape-valid string and accepts a value created by `derive_subaccount_ref()`.

The wire schema still validates the opaque reference by shape because persisted JSON has no way to carry cryptographic object provenance. Factory origin is enforced where untrusted raw account identifiers enter the Python object model.

## Key files

- `src/idx_trade/personal_portfolio/schema.py`
- `src/idx_trade/personal_portfolio/semantics.py`
- `src/idx_trade/personal_portfolio/snapshot.py`
- `src/idx_trade/personal_portfolio/types.py`
- `src/idx_trade/personal_portfolio/validation.py`
- `src/idx_trade/personal_portfolio/store.py`
- `src/idx_trade/personal_portfolio/surface.py`
- `schemas/personal_portfolio_snapshot_v1.schema.json`
- `tests/test_snapshot_hardening.py`
- `tests/test_snapshot_semantic_gate.py`
- `tests/test_subaccount_ref_factory.py`
- `tests/test_snapshot_enrichment_boundary.py`

## Required round-3 validation

Run exact-branch focused tests and full pytest if the environment allows. Also run compile/import checks, Draft 2020-12 schema parsing/runtime parity, and `git diff --check`.

Adversarially verify:

- bare JSON Schema rejects naive timestamps;
- `validate_snapshot_payload()` rejects naive timestamps and backwards timestamp ordering;
- successful endpoint arithmetic mismatch is rejected;
- failed endpoints cannot report observed/accepted/rejected rows;
- duplicate positions and cash are rejected through the direct canonical payload path;
- detail endpoint `accepted_rows` must equal canonical detail row counts;
- `PORTFOLIO_SUMMARY.accepted_rows` must equal the number of represented non-empty asset classes;
- `PortfolioSnapshot.from_canonical_json()` round-trips a factory-origin subaccount reference after canonical validation;
- ordinary shape-valid `ksa_<64hex>` strings are rejected by `CashBalance`/`PortfolioPosition` constructors;
- round-1 append-only, source-pin, minimization, Decimal, enrichment-boundary and provider-neutral constraints remain intact.

## Validation disclosure from remediation agent

This ChatGPT runtime could not execute an exact checkout because outbound Git access is unavailable. Remote GitHub consistency/diff inspection and targeted logic checks were performed, but **no new exact pytest pass count is claimed here**. Round 3 must rerun the tests on the exact branch HEAD.

No KSEI login, credential access, provider call, real portfolio data, backend endpoint, UI, public Ownership/KSEI modification, Financial PIT modification, Corporate Action modification, Foreign Flow modification, model change, or protected-outcome access occurred.

## Verdict gate

Return one of:

- `ACCEPTED_FOR_BOUNDED_REAL_AUTH_TEST_DESIGN`
- `REWORK`, with severity, exact path/line/failure mode, and the minimal recommended fix.

Acceptance authorizes only design of one bounded private/no-persist real-auth check. It does not itself authorize credential use, provider execution, public APIs/UI, scheduled collection, or automatic investment/trading actions.
