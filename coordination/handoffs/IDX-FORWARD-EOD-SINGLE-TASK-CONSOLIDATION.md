# Handoff

from: Codex MAIN
to: ChatGPT reviewer
task_id: IDX-FORWARD-EOD-SINGLE-TASK-CONSOLIDATION
model_used: gpt-5.6-luna xhigh
reasoning_level: xhigh
source_repository: `C:/Users/Sam/OneDrive/Documents/Project/idx-trade`
source_commit: `6b85a93`
branch: `integration/forward-eod-automation-monitoring`
head_commit: see result commit
scope: consolidate the legacy source-blocked Open archive schedule into the canonical forward_monitoring EOD runner

## Change

- canonical Windows task: one daily trigger at 18:00 Asia/Jakarta;
- interactive logon trigger provides catch-up after laptop downtime;
- `StartWhenAvailable=true` and chronological official-calendar selection are
  retained;
- exact target date is validated against the official IDX calendar and exact
  Stock/Index Summary response dates;
- old `IDXTrade-ForwardOpenArchive` is disabled, not deleted, after controlled
  capture acceptance;
- existing Stockbit intraday task is untouched;
- canonical `session_ohlcv.parquet` is the only forward OHLCV/Open artifact.

## Boundary

Implementation occurred before 18:00 Jakarta. No real capture and no task
enable/disable action were performed before the post-18:00 controlled capture
gate.

## Validation

Focused and full pytest results are recorded in the final result commit.

## Prohibited scope

No model/outcome access, no `FORWARD_OUTCOME_ACCESS_STARTED`, no OPEN
historical backfill, no Path Risk, no Stockbit automation changes, and no
main merge.
