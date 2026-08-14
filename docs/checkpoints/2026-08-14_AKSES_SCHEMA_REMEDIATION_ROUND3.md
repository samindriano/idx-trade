# Personal AKSes KSEI Schema — Round 3 Remediation

Date: 2026-08-14

Lane: `AKSes adapter schema V1`

Branch: `integration/schema-hardening-v2`

Scope: offline schema/contract remediation only. No KSEI login, credential use, provider call, real portfolio data, backend API/UI, scheduled collection, public Ownership/KSEI changes, Financial PIT changes, Corporate Action changes, Foreign Flow changes, model changes, or protected-outcome access.

## Independent review input

Round 3 returned `REWORK` after:

- focused tests: 18 passed / 3 failed;
- full pytest: 57 passed / 4 failed;
- compile/import PASS;
- runtime schema parse PASS;
- checked-in schema parse/parity FAIL;
- `git diff --check` PASS.

The three branch-local blockers were:

1. malformed checked-in JSON Schema due one missing closing object delimiter;
2. `SubaccountRef` leaking from `jsonable()` as a guarded `str` subclass, causing `deepcopy()` failure;
3. diagnostic regression where constructor rejection no longer contained the prior `keyed-HMAC` wording.

The fourth reported failure remained the known unrelated historical storage assertion (`2` conflicts versus expected `1`).

## Remediation

### Checked-in schema

Repaired `$defs.endpoint_evidence.allOf[1]` so the conditional object is fully closed. No semantic rule was intentionally changed. The independent acceptance rerun must parse the JSON artifact and compare it exactly with the runtime `PERSONAL_PORTFOLIO_SNAPSHOT_SCHEMA_V1` object.

### Canonical string normalization

`jsonable()` now handles ordinary/string-subclass values explicitly after `StrEnum`:

- `SubaccountRef` becomes a built-in `str` in canonical payloads;
- constructor/factory provenance remains enforced in the Python object model before serialization;
- canonical dicts can be copied/deep-copied without invoking the guarded `SubaccountRef.__new__` constructor.

A focused regression checks exact built-in `str` type and `deepcopy()` safety.

### Diagnostic compatibility

`PortfolioPosition` and `CashBalance` still reject any non-`SubaccountRef` value even if it has a valid `ksa_<64hex>` shape. The message now states that the value must be a `server-derived keyed-HMAC reference from derive_subaccount_ref`, preserving both factory-origin semantics and prior test wording.

## Gate

No real-auth test design or execution is authorized until an independent exact-HEAD rerun returns:

`ACCEPTED_FOR_BOUNDED_REAL_AUTH_TEST_DESIGN`

This remediation agent cannot execute exact repo pytest in its runtime because outbound Git checkout is unavailable, so no new pass count is claimed here.
