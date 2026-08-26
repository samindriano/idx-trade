# Stockbit Intraday Cloud Migration Remediation V1

Date: 2026-08-26 Asia/Jakarta
Branch: `ops/stockbit-intraday-cloud-migration-v1`
Current authority base: latest `origin/main`; do not reset the lane to its original branch point.
Legacy implementation reference: `fix/stockbit-intraday-postclose-fix-v1@03d42988b16ced8d5c2656291c629ea3596f91f4`
Accepted E2E read authority: `043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2`

## Goal

Port only the bounded, still-valid Stockbit intraday acquisition semantics into a current-main cloud lane, while fixing recovery/idempotency defects before any scheduled GitHub Actions activation.

This lane must not alter model science, Decision V2, Sizing V1, Execution V1, protected outcomes, prospective counters, Official Open authority, or the canonical EOD/CA contracts.

## Accepted legacy semantics to preserve

- provider contract: `provider=stockbit`, `interval=intraday`, `timeframe=today`;
- exact requested ticker identity;
- exact current Asia/Jakarta session date;
- no historical reconstruction after provider rollover;
- no synthetic minute data, interpolation, OHLCV invention, or forward fill;
- frozen same-day canonical listed-security universe;
- strict reuse of canonical same-session official EOD Stock Summary when available;
- conservative fetch when gate evidence is missing;
- monthly quota reserve and bounded retry behavior;
- raw provider evidence, normalized path rows, status evidence, and hashes.

## Implemented remediation contracts

### R1 — explicit status classes

Admissible terminal statuses are `SUCCESS` and `SKIPPED_IDX_NO_ACTIVITY`. Transient `REQUEST_ERROR` is retryable. 404/provider-terminal/quota/payload/session/identity failures are blocking until explicitly resolved by an admitted rule. Unknown statuses fail closed.

Recovery retries only missing or retryable tickers. It does not refetch admissible or blocking terminal evidence.

### R2 — admissible completion

`attempted == universe` is not completion. Runtime state exposes observed, admissible-terminal, retryable, blocking, missing, `all_observed`, `all_terminal`, and `admissible_complete`. Only `admissible_complete=true` produces a final admitted session manifest.

### R3 — official same-session EOD gate

A zero-activity skip is admitted only from the already-canonical E2E POST_EOD Stock Summary evidence for the exact same session. Stockbit Intraday does not create another IDX EOD collector. A SHADOW 404 may be reconciled to `SKIPPED_IDX_NO_ACTIVITY` only when that exact official gate proves zero activity.

### R4 — rollout-policy idempotency and final admission

A policy transition is bound to `(session_date, admitted_session_manifest_sha256)` and applied at most once. Final replay is zero-provider-call. The final verifier rechecks child hashes, frozen run contract, schedule/gate/EOD bindings, recomputed completion, and SHADOW metrics reconstructed from immutable provider-attempt history. Top-level rollout metrics are not trusted independently.

### R5 — cloud durability

Production namespace is fixed to `stockbit-intraday-v1`. Known slots are `1830`, `1930`, `2030`.

Each slot writes immutable snapshot/result objects first and `commit.json` last. R2/S3 writes require `If-None-Match: *`; identical replay is idempotent and conflicting bytes fail closed. Same-slot divergent races fail closed. A delayed earlier slot cannot run after a later slot has committed.

Snapshot paths reject traversal, forbidden secret/outcome paths, duplicate entries, and noncanonical path segments that would otherwise be normalized away.

### R6 — provider completeness wording

`SUCCESS` proves exact-session Stockbit provider-path validity; it does not invent a last-minute completeness threshold. Illiquid names are not rejected merely because their final trade happened earlier in the session.

### R7 — canonical schedule and accepted E2E bridge

The bridge reads only `e2e-paper-v1` through exact accepted runtime `043003ee...`. The accepted checkout must be exact and clean. Its child Python process runs isolated and receives only minimal process environment plus R2 credentials; provider/account secrets are not inherited. The E2E store is wrapped read-only so any attempted `put_if_absent` is rejected.

A non-session date is a zero-provider-call NOOP. Current-session-only guards prohibit retroactive Stockbit capture.

### R8 — deployment provenance

A real cloud run requires exact `STOCKBIT_INTRADAY_EXPECTED_IMPLEMENTATION_REF`; missing, malformed, or mismatched pins fail before the capture proceeds. `--dry-run` remains genuinely offline and needs no cloud/provider credentials.

## External E2E/R2 evidence already available

The accepted E2E path has a successful manual full-cloud synthetic rehearsal:

- workflow run: `32959923100`
- accepted runtime: `043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2`
- production CloudInputBundle manifest SHA-256: `858327909343a887c54fbc5e3bea4dafe6f7a8b89f2422a313b954dee04c08ee`
- rehearsal manifest SHA-256: `d6cda2503291c0cc1bf734a10fa741adffea7590090c98487acddfdd8ce40a60`
- verdict: `SYNTHETIC_FULL_CLOUD_E2E_REHEARSAL_PASS`
- provider calls: `0`
- protected outcomes accessed: `false`
- real R2 create-only/idempotent/conflict/readback behavior: exercised under an isolated throwaway prefix.

This proves the shared E2E input/R2 boundary exists and is readable. It does **not** substitute for the dedicated Intraday smoke or a genuine future-session Intraday proof.

## Remaining migration order

1. Keep exact-head PR CI green after all static/adversarial fixes.
2. Run dedicated Intraday ConditionalS3 smoke under a unique `stockbit-intraday-smoke-v1/<run-id>` prefix with zero provider calls.
3. Run the read-only accepted-E2E bridge preflight for the current Jakarta date.
4. Review the resulting smoke/preflight evidence and freeze the exact Intraday implementation SHA intended for proof.
5. Define a **single-writer proof window** for one future trading session. The Windows scheduled tasks must not issue Stockbit provider calls for that proof session while cloud is the designated writer. Windows code/config remains available for rollback; only duplicate execution is suppressed.
6. Run the cloud slots prospectively. Do not backfill a missed slot/date.
7. Verify immutable R2 slot commits, provider-call counts, universe/gate identity, final session manifest, policy checkpoint, restart/idempotency behavior, and no outcome/retro/synthetic use.
8. If proof fails before a provider call, Windows may remain/return as the live path subject to the prospective window. If cloud already issued provider calls for that session, do not run a duplicate Windows capture merely to compare outputs.
9. Only after one accepted genuine future-session proof may cloud scheduling be considered for normal operation. Retire Windows scheduling only with explicit acceptance; keep the legacy implementation recoverable for rollback.

## Current verdict

`STOCKBIT_INTRADAY_CLOUD_MIGRATION_REMEDIATION_ACTIVE`

No scheduled Stockbit Intraday GitHub workflow or production `stockbit-intraday-v1` provider capture is authorized merely by this document.
