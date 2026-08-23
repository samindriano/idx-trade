# Historical E2E Replay Engine and Scope Freeze V1

Date: 2026-08-24
Branch: `research/idx-historical-e2e-replay-v1`
Parent readiness commit: `18cd5c72376742d287de1e5a7c30073c700c58c7`

## Decision

The historical E2E engine is structurally ready for a later replay, but the
current real-data strict scope is empty. No historical performance replay was
run. The final result is:

`TRUE_HISTORICAL_E2E_ENGINE_READY_PERFORMANCE_BLOCKED_BY_DATA`

This is not a model-quality verdict. It is a fail-closed data-readiness
verdict.

## Scope and boundaries

This lane added a thin artifact-driven replay adapter and an outcome-blind
historical official-Open acquisition/resume utility. It does not replace the
operational E2E runtime, scheduler, database, model, or counter. The replay
adapter uses the existing public artifact verifiers and production orchestration
path; it does not call providers, fit/rescore models, or load protected
outcomes.

`coordination/TEAM_STATUS.md` was not edited because MAIN owns that file.

## Historical official-Open acquisition

External root:
`D:\Documents\Project\idx-historical-open-acquisition-20260824-v1`

Manifest:
`ACQUISITION_MANIFEST.json`

Manifest SHA-256:
`dc74485c6d4ade01e125b08871105c8daea9c64f9daa2af6cc00d26592a8fcbf`

The acquisition consumed the frozen 600 structural Decision V2 sessions and
was resume-safe. Final status was `COMPLETE`, with 600/600 sessions certified.
Direct IDX was attempted first; the historical transport returned HTTP 403 and
the accepted Zapi raw IDX passthrough was selected for all 600 sessions. The
raw source identity remained `provider=idx` and
`path=TradingSummary/GetStockSummary`; no other provider was used.

Aggregate acquisition diagnostics:

- 568,555 raw rows;
- 226,323 positive OpenPrice rows;
- 342,232 unavailable/non-positive OpenPrice rows;
- 1,297 BUY intents in the frozen structural ledger;
- 905 BUY intents with certified official Open available;
- 392 BUY intents without certified official Open;
- 376/600 decision sessions buy-ready under the exact intent/Open check.

The 392 missing BUY Opens remain missing. No Open was inferred, synthesized,
backfilled from a non-official source, or used to claim performance readiness.

## Strict replay scope freeze

External root:
`D:\Documents\Project\idx-historical-e2e-scope-freeze-20260824-v1`

Scope file:
`REPLAY_SCOPE.json`

File SHA-256:
`8946a9b7ad4b35de32eca186f19e3297c9cf05d4771e553db8d6d8297e0a4827`

Payload SHA-256:
`40d538417b8c48dd95455ab425d4af20939f28a44f4c1cceeea876e26c5dcba3`

Status: `STRICT_SCOPE_EMPTY_BLOCKED`

The exact frozen candidate count was 600, but strict session count was 0.
The scope freeze fail-closed blockers were:

- `BUY_OPEN_SUPPORT_INCOMPLETE`;
- `CA_EVENT_WINDOW_CONTINUITY_BLOCKED`;
- `DIVIDEND_MARKET_WIDE_NO_EVENT_PROOF_MISSING`.

All 600 session manifests are certified, but certification of the market
archive is not equivalent to complete execution-grade support for every
decision intent. The existing CA event-window artifact remains blocked, and
the bounded dividend corpus does not prove market-wide no-event status for the
remaining holding spells. Absence of a captured event is not treated as proof
that no event occurred.

Because the strict scope is empty, the lane did not calculate returns, P&L,
NAV, CAGR, Sharpe, drawdown, targets, labels, IC, R5/R10, or Monte Carlo
performance.

## Replay implementation and synthetic verification

Added:

- `src/idx_trade/historical_e2e_replay_v1.py`;
- `scripts/acquire_historical_official_open_v1.py`;
- `scripts/freeze_historical_e2e_scope_v1.py`;
- `tests/test_historical_e2e_replay_v1.py`.

The replay adapter verifies score, EOD, corporate-action, and official-Open
artifacts through the existing public verifiers, then calls the existing
production orchestration. Static boundary auditing found no provider calls,
protected-outcome reads, model fit/rescore, or outcome marker access.

The separate synthetic production-path acceptance remained green:

- external root: `D:\Documents\Project\idx-historical-e2e-synthetic-production-replay-20260824-v1`;
- acceptance summary SHA-256:
  `2a14bb131054bee4454af1b822ca524d84c4c2a724980c8137d0c90d2a7a476a`;
- `synthetic_only=true` and `outcome_access=false`.

The cold-restart acceptance also remained green:

- external root: `D:\Documents\Project\idx-historical-e2e-cold-restart-20260824-v1`;
- acceptance summary SHA-256:
  `892cb72359927478a3bbeae61155d62a554edf7e0f2603d05b7f63fa5fa1ffac`;
- process A committed partial state, process B resumed from disk, and process
  C returned `ALREADY_COMPLETE`;
- duplicate rerun preserved execution SHA
  `291d8dcff916eb711ca9fe9cff86a6018ba2d1760511c24360f9439a2a47f1e2`,
  runtime snapshot SHA
  `98c7675975562f35178276e393061c9696759c7c51365f8777cbed610ef923d8`, and
  runtime state SHA
  `1219084bc2ad42f963b6456cebf59a8b50377f163c1be3b201f3ca19c011d920`;
- duplicate execution, snapshot, and state were unchanged.

These synthetic checks validate the engine boundary and idempotency only. They
are not historical performance evidence.

## Validation

- changed-module `py_compile`: PASS;
- focused E2E/Open/replay suite: `81 passed`;
- full pytest: `716 passed`, 3 pre-existing pandas `FutureWarning`s;
- `git diff --check`: PASS.

The live Open envelope marker was corrected from the stale `finance:idx`
fixture expectation to the observed raw-envelope marker
`finance:idx:raw`; tests now reject the legacy marker. This is provenance
contract alignment, not a source substitution.

## Guard confirmation

No protected outcomes, labels, returns, R5/R10, performance metrics, or model
fit/rescore were accessed. No scheduler, operational runtime, counter, or
`TEAM_STATUS` was changed. The external artifacts remain outside Git.

## Next action

Do not run historical performance replay until a separately accepted
outcome-blind remediation closes the three strict-scope blockers and produces a
non-empty, hash-pinned scope. The existing engine and synthetic acceptance can
then be reused without changing the frozen model/execution semantics.
