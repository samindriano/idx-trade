# Stockbit Intraday Cloud Production Workflow

This checkpoint records the production workflow added to the Stockbit
Intraday migration branch. It uses the existing cloud runner and archive; it
does not introduce another capture system or change the Windows fallback.

## Scheduling contract

`.github/workflows/stockbit-intraday-cloud-production.yml` schedules one
current-session slot at 18:30, 19:30, and 20:30 Asia/Jakarta (GitHub cron
11:30, 12:30, and 13:30 UTC) on weekdays. The same workflow may be invoked
manually only on `main` with one of the three explicit slots. The runner
rejects a non-current session, an early slot, and an unavailable/invalid
official E2E context. Concurrency is non-cancelling and archive claims remain
create-only/idempotent.

The workflow checks out `${GITHUB_SHA}` and binds
`STOCKBIT_INTRADAY_EXPECTED_IMPLEMENTATION_REF` to that exact commit. Its
accepted E2E read-only bridge remains pinned to
`043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2`. Secrets are passed only through
GitHub Actions environment interpolation; no credential is present in
arguments, source, or artifacts.

## Safety state

This is workflow configuration, not proof of a live production capture. It
must not be called operationally accepted until the branch is merged, the
isolated R2 smoke and E2E bridge preflight pass on the exact current main,
and one controlled future-session run proves the production prefix without a
second writer. The existing Windows 18:30/19:30/20:30 fallback remains
untouched until that proof and an explicit single-writer cutover decision.

No provider call, R2 write, outcome access, counter mutation, or local
scheduler change was performed while preparing this checkpoint.
