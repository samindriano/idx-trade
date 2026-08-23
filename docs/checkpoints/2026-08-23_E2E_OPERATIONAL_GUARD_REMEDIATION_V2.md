# Controlled Live E2E Paper Operationalization — Guard Remediation V2

Date: 2026-08-23 Asia/Jakarta  
Branch: `integration/idx-e2e-baseline-paper-v1`  
Code commit: `3dd7055b7669c9c7999420a81a670d906690597c`  
Parent: `4d0c8f1cf32beea20ed9abcd81adeabe71e2311f`

## Scope

This is an engineering-only remediation milestone. It does not access
providers, protected outcomes, models, brokers, or scheduler installation.
`coordination/TEAM_STATUS.md` was intentionally not changed because MAIN is
its sole owner.

## Remediation

- Official session calendars now fail closed on duplicate dates and weekend
  rows instead of silently deduplicating or accepting a non-session.
- Controller score pointers require an exact manifest path/hash and the exact
  decision session date.
- Prepared parents require the frozen schema, canonical payload hash, exact
  execution session, and matching OHLCV/model-input/calendar file hashes.
- PREOPEN and POST_EOD entrypoints retain exact deployment attestation and
  runtime locking.
- Controller branch tests now cover pointer tampering, prepared-parent
  rejection, and a persisted Sunday/holiday no-op.

## Validation

- Focused guard/controller/orchestration/dividend runtime suite: PASS.
- Full repository pytest: PASS; 3 pre-existing pandas `FutureWarning`s only.
- `py_compile`: PASS for changed Python modules/scripts/tests.
- `git diff --check`: PASS.
- Fresh controller smoke at 2026-08-23 13:01:44 Asia/Jakarta:
  `WEEKEND_OR_HOLIDAY_NOOP`, status SHA
  `f9f741de89bf525a62608d0d86f2e021135abf7f2656d7c7d2f6999d528ada57`.
  Provider calls, model refit/rescore, and outcome access were all false.

## Remaining review blockers

This milestone is not a weekday live-cycle pass and does not claim the final
armed state. The controller still stops fail-closed until the existing V1.2
corporate-action attestation/journal is explicitly configured and the
controller invokes the existing guarded POST_EOD/PREOPEN consumers. A
weekday cycle, T0 bootstrap, cold restart acceptance, and scheduler review
remain required before `CONTROLLED_LIVE_E2E_ARMED_WEEKDAY_PROOF_PENDING` can
be claimed.

