# Forward Open Archive — Windows Installation Result

Date: 2026-08-10 (Asia/Jakarta)
Branch: `ops/idx-forward-open-archive-v1`
Runtime code HEAD before this documentation result:
`7d68d23597729e45bb14858b22445b34636bdc0b`

## Decision

**`FORWARD_OPEN_ARCHIVE_WINDOWS_INSTALLED_SOURCE_BLOCKED`**

The source-agnostic Windows scheduler was installed and manually triggered
once. The expected source gate remains active:
`BLOCKED_SOURCE_NOT_FROZEN`. No provider was selected or configured.

No IDX website scraping/crawling, Yahoo, Zapi, TradingView, Investing.com,
historical Open backfill modification, modelling, Stage-5 rerun,
execution-PnL analysis, paper/live trading, broker integration, or main merge
was performed.

## Repository and environment

- worktree: Codex-managed detached worktree from
  `ops/idx-forward-open-archive-v1`
- starting/runtime code HEAD: `7d68d23597729e45bb14858b22445b34636bdc0b`
- remote branch matched the starting HEAD before installation
- working tree was clean before installation
- pytest: **216 passed, 3 warnings**
- Python: **3.13.5**, project installed editable in the local user
  environment without dependency installation
- DataRoot: new external directory under the existing IDX runtime-data root;
  it is outside Git and is intentionally not recorded as an absolute local
  path in repository documentation

## Task Scheduler verification

Task name: `IDXTrade-ForwardOpenArchive`

- task state after manual run: `Ready`
- principal: current user, `InteractiveToken`, limited run level
- daily trigger: `22:00` local Windows time, every day
- logon trigger: enabled
- `StartWhenAvailable`: `true`
- `RunOnlyIfNetworkAvailable`: `true`
- `MultipleInstancesPolicy`: `IgnoreNew`
- execution limit: `PT45M`
- action: `scripts/run_forward_open_archive.ps1`
- `-LookbackDays`: `45`
- `-ProviderModule`: absent/unset

## Manual and scheduled execution

Direct manual command returned the expected source-blocked result:

- status: `BLOCKED_SOURCE_NOT_FROZEN`
- direct exit code: `2`
- provider module: empty

The scheduled task was then manually started once:

- `latest_run.json` status: `BLOCKED_SOURCE_NOT_FROZEN`
- scheduled-task result: `1`, because the PowerShell wrapper surfaces the
  expected blocked runner exit as a task failure
- task returned to `Ready`
- no session directories or price Parquet files were written
- only the durable status JSON and runner log were produced

The durable status message states that no network price source was selected.
The scheduler therefore performed no price-data fetch.

## Boundaries preserved

- no `-ProviderModule` was passed during installation or execution;
- `execution_grade_promoted=false` remains unchanged;
- the immutable research panel and historical Open backfill artifacts were
  not modified;
- Ranking V1/V2 semantics and consumed Stage-5 evidence were not changed;
- provider selection remains blocked pending a separate source audit.

Stop for independent ChatGPT review. Do not configure a provider in this
track until a separate audited acquisition decision is approved.
