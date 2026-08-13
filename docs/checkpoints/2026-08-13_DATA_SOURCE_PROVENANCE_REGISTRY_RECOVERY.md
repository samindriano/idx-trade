# Data-source provenance registry recovery checkpoint

Date: 2026-08-13 (Asia/Jakarta)
Branch: `codex/data-source-provenance-registry-v1`
Recovered base: `origin/main` at `716746635139b87d8d0b74b2407b013158239eab`
Scope: registry, schema, validator, tests, and documentation only

## Recovered state

- The dedicated provenance-registry worktree was clean before continuation.
- There was no staged, unstaged, or untracked implementation diff to recover.
- The branch was fast-forwarded from its earlier coordination claim to the
  latest accepted `origin/main` state.
- The canonical `TEAM_STATUS.md` row remains `ACTIVE` under
  `Codex/Provenance-Registry`.
- The active repository-wide scientific-integrity audit remains a separate
  owner. This lane records accepted evidence; it does not perform scientific
  remediation or independently fix findings owned by that audit.

## Preserved evidence boundaries

The prior inventory is retained and must be represented without semantic
upgrade:

- official authority and transport parity do not by themselves establish
  historical PIT completeness or first-knowable publication time;
- Corporate Actions remains revision-sensitive, and
  `TanggalPencatatan` is not automatically a market-effective date;
- Stockbit intraday remains a forward SHADOW and is not canonical EOD;
- accepted Yahoo/TradingView Open derivatives may support bounded research
  common-support analysis while `execution_grade_promoted=false`;
- Stock Summary absence does not establish `NO_TRADE`, and its official
  session-date rows do not establish historical publication timing;
- unresolved Financial PIT, ownership/KSEI, foreign-flow, market/index,
  sector-history, historical-universe, tradability, corporate-action, and
  margin semantics remain explicitly unresolved or blocked;
- Zapi is represented as a transport/access layer where parity was accepted,
  never as an independent authority merely because values matched;
- missing public history, unavailable official bytes, and absent rows remain
  unknown or blocked rather than negative evidence.

## Implementation boundary

The next commit may add only the canonical machine-readable registry, its
fail-closed validator, tests, maintenance documentation, and the final factual
handoff/checkpoint. It must not call providers, acquire data, access protected
outcomes, rerun experiments, change models, or alter scientific conclusions.

