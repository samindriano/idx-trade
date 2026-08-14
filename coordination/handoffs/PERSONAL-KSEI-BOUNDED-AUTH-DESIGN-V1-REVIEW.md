# Personal KSEI Bounded Auth Design V1 — Independent Review Handoff

Status: `REVIEW`

Branch: `integration/personal-ksei-bounded-auth-design-v1`

Parent accepted schema:
`integration/schema-hardening-v2@dd323be798b6d2fa1631e65b3dc3f2693be07ef8`

## Review boundary

Review the bounded-auth **design/offline harness only**.

Do not:

- use AKSes credentials;
- login to KSEI;
- call provider endpoints;
- add a concrete HTTP transport;
- inspect real portfolio data;
- change public Ownership/KSEI;
- touch UI, scheduler, models, outcomes, Financial PIT, Corporate Actions, or
  Foreign Flow.

## Main implementation

- `src/idx_trade/personal_portfolio/bounded_auth.py`
- `src/idx_trade/personal_portfolio/__init__.py`
- `tests/test_personal_ksei_bounded_auth_design.py`
- `docs/checkpoints/2026-08-14_PERSONAL_KSEI_BOUNDED_AUTH_DESIGN_V1.md`

## Adversarial checks

Verify all of the following:

1. policy cannot be relaxed from one activation, one login, one call per exact
   portfolio endpoint, zero retries, no persistence, no browser/scheduler, and
   no global identity;
2. endpoint paths are exact and no caller can inject an arbitrary URL/path;
3. no concrete provider/network client exists;
4. credentials/transformed password/session token/raw response bodies never
   appear in repr, serialized report, pickle/reduce/getstate, or generic
   `dataclasses.asdict()` paths; sensitive transport containers must remain
   non-dataclass slot classes;
5. `finally` clears credential/session/transformed-secret references and closes
   the transport on success and failure;
6. activation/login auth failure stops before portfolio calls;
7. portfolio 401/403 stops remaining calls;
8. non-auth endpoint failure is attempted once only and does not trigger retry;
9. raw response values are absent from `BoundedAuthReport.to_json()`;
10. only raw SHA-256, byte count, field names/types/cardinality, and the minimal
    summary zero-state probe survive;
11. dynamic/suspicious object keys are redacted;
12. oversized and invalid-JSON bodies fail closed;
13. `completed_call_plan` is not misread as all-endpoints-success;
14. the transport protocol documentation makes concrete-method single-network-
    request/no-retry/no-log behavior a future review requirement;
15. no regression to the accepted personal portfolio schema/storage boundary.

## Required validation

Run at least:

- `pytest -q tests/test_personal_ksei_bounded_auth_design.py`
- all Personal Portfolio tests;
- full pytest;
- compile/import;
- `git diff --check`;
- scope diff against latest `origin/main`;
- repository/credential scan for literal secrets or real account material.

The known unrelated historical storage assertion may be reported separately if
it remains unchanged.

Also read latest `origin/main:coordination/TEAM_STATUS.md`. The AKSes row was
known stale at implementation start; synchronize it safely before any future
real-auth execution.

## Verdict

Return one of:

- `ACCEPTED_FOR_ONE_BOUNDED_PRIVATE_REAL_AUTH_RUN`
- `REWORK` with severity, exact path/line or reproducer, and minimal fix.

No provider execution is part of this review.
