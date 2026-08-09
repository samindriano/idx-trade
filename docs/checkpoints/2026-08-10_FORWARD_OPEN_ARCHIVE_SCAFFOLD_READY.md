# Forward Open Archive Scaffold Ready

Date: 2026-08-10 (Asia/Jakarta)
Branch: `ops/idx-forward-open-archive-v1`

## Decision

**FORWARD_OPEN_ARCHIVE_SCAFFOLD_READY_SOURCE_BLOCKED**

The project now has a persistent, source-agnostic forward-Open archival scaffold so the operating idea is not lost while historical Open backfill and Ranking V2 work continue separately.

Implemented:

- `src/idx_trade/forward_open_archive.py`
- `tests/test_forward_open_archive.py`
- `scripts/run_forward_open_archive.ps1`
- `scripts/install_forward_open_archive_task.ps1`
- `docs/FORWARD_OPEN_ARCHIVE_V1.md`

## Intended local behavior

A Windows scheduled task may be installed with:

- daily trigger at 22:00 local time;
- logon catch-up trigger;
- `StartWhenAvailable` for missed schedules;
- one running instance maximum;
- 45-day recent session catch-up window by default.

The runner reuses the existing official IDX exchange-session source to determine expected sessions. It does not infer sessions from weekdays.

## Price-source boundary

No forward price/Open provider is yet frozen.

Without an explicit provider adapter the runner returns:

`BLOCKED_SOURCE_NOT_FROZEN`

and writes a durable status JSON. It does not silently choose or scrape a source.

A separate Forward Open Acquisition audit is required before a provider module may be configured. Direct IDX crawling remains disallowed under the current project source policy.

## Archive contract

When a future audited adapter is configured, each session snapshot is validated for ticker/date uniqueness, complete positive OHLC, non-negative volume, and OHLC envelope validity before writing an immutable Parquet snapshot plus manifest/SHA-256.

`execution_grade_promoted=false` remains mandatory.

## Local-machine step still required

GitHub cannot register the user's Windows Task Scheduler entry. A local Codex/PowerShell task must later:

1. check out this branch/worktree;
2. run the full tests;
3. choose a local external data root;
4. run the installer script;
5. verify both the 22:00 and logon triggers;
6. verify the current expected fail-closed status while the provider is unset.

No source audit, historical backfill result, model result, paper/live trading, broker execution, or main merge is authorized by this checkpoint.
