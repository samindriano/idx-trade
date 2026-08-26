# Stockbit Intraday Cloud In-Flight Progress Hardening V1

Date: 2026-08-26 Asia/Jakarta  
Branch: `ops/stockbit-intraday-cloud-migration-v1`

## Scope

This remediation hardens the existing Stockbit Intraday cloud slot path. It
does not change the provider schema, all-ticker admission contract, model,
Decision, sizing, execution, counters, outcomes, or the existing Windows
fallback.

## Finding and bounded fix

The previous runner kept the immutable claim before provider work but uploaded
the local journal only after the full ticker batch returned. A process kill in
the middle of that batch therefore left the claim but no recoverable progress.
The next runner could not safely resume the slot and would either remain
blocked or require an unsafe duplicate provider history.

The cloud archive now stores, in the existing `stockbit-intraday-v1` namespace:

- immutable provider-response evidence immediately after each provider return;
- immutable content-addressed progress snapshots/checkpoints before the batch,
  after every recorded ticker, after gate reconciliation, and after final
  session materialization;
- exact session/slot/claim/code identity and guard fields on every progress
  record;
- create-only list/read verification for progress and provider evidence.

A fresh runner restores the newest verified progress snapshot. If a prior slot
has progress but no committed marker, the next valid slot may continue that
snapshot and only request the still-pending tickers. A current-slot claim may
be resumed only after the immutable progress checkpoint is older than the
two-hour stale-claim threshold; a recent claim remains fail-closed to prevent
concurrent provider stages. The scheduled workflow must still use a single
concurrency policy and the later-slot ordering guard.

This preserves the conservative failure mode: an orphaned claim or malformed,
conflicting, stale, or hash-invalid progress object blocks rather than being
silently discarded.

## Validation

- Stockbit Intraday focused suite, including all intraday modules and the new
  hardening/process-kill tests: PASS.
- Actual subprocess `SIGTERM` after one provider response, then a fresh
  process from cloud-only local conditional storage: PASS.
- Resumed process fetched only the unfinished ticker; the already durable
  ticker was not refetched.
- Same-slot concurrent claim race: one provider-stage owner, one explicit
  `STOCKBIT_INTRADAY_SLOT_ALREADY_CLAIMED` failure.
- py_compile: PASS.
- git diff --check: PASS.
- Provider calls, R2 calls, protected outcomes, and runtime mutation: none in
  this remediation.

## Remaining gate

This is engineering evidence only. A genuine future-session cloud run remains
required before Stockbit Intraday cloud capture is considered operationally
accepted. No production scheduler is activated by this checkpoint.
