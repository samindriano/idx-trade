# E2E Dividend Orchestration Journal Acceptance

Date: 2026-08-22

## Verdict

`DIVIDEND_ORCHESTRATION_JOURNAL_ACCEPTED`

## Purpose

The prospective dividend acquisition layer is separated from the immutable
Paper portfolio runtime.

Flow:

`execution-relevant ticker universe`
? `prospective acquisition`
? `immutable acquisition journal`
? `POST_EOD/PREOPEN consumer`
? `DividendAwarePaperState`

The acquisition layer does not mutate Paper state.

## Execution-relevant universe

Required coverage is the union of:

- actual Paper positions;
- pending buys;
- pending sells;
- current Decision targets.

## Discovery coverage policy

New tickers receive a 366-calendar-day bootstrap lookback.

Already-covered tickers receive a 7-calendar-day overlap.

Coverage is monotonic and only advances after successful acquisition handling.

## Journal behavior

The journal is:

- normalized;
- deterministic;
- SHA-256 addressed;
- written atomically;
- immutable per target path;
- exact-rerun idempotent;
- linked to the previous journal by file SHA and journal SHA;
- recursively parent-verified.

## Certified evidence

Certified journal entries bind:

- announcement identity;
- ticker;
- certified event id;
- certified event SHA-256;
- immutable evidence directory;
- ATTACHMENT_REVIEW.json SHA-256.

Evidence files are re-hashed when the journal is loaded.

## Progression invariants

A child journal may not:

- drop or mutate a previously certified event;
- downgrade certified evidence back to a blocker;
- silently drop or alter an unresolved blocker;
- regress prior ticker coverage.

A blocker may resolve to certified evidence.

## Fail-closed blockers

Ambiguous or unsupported dividend candidates remain explicit blockers instead
of being silently ignored.

## Acceptance

Focused orchestration regression passed:

`21 passed`

Next:

`Step 4D2b - restart-safe prospective acquisition batch runner`
