# Forward EOD Single-Task Consolidation — Pre-Capture

Date: 2026-08-12 (Asia/Jakarta)
Branch: `integration/forward-eod-automation-monitoring`
Status: `IMPLEMENTED_PRE_CAPTURE`

## Decision

The legacy `IDXTrade-ForwardOpenArchive` scheduler is superseded by the
canonical `forward_monitoring` EOD runner. The project will use one EOD task at
18:00 Asia/Jakarta. The old task is disabled, not deleted, after the first
controlled canonical capture succeeds.

The canonical session transaction remains the only capture path. Its immutable
`session_ohlcv.parquet` contains Open/High/Low/Close/Volume and provenance;
`model_input.parquet` remains unchanged. No second `forward_open_archive`
fetch, database, scheduler, or session hierarchy is introduced.

## Missed-schedule and date-validity contract

The task has a daily 18:00 trigger and an interactive logon trigger. If the
laptop is off at 18:00, the next available logged-in run starts the same
catch-up runner. `StartWhenAvailable` and chronological `_earliest_missing`
selection prevent skipped sessions; `MultipleInstances=IgnoreNew` prevents
overlap.

At each run the runner first synchronizes the official IDX exchange calendar
through the current closed-session boundary. A missing target must be present
in that calendar. The canonical Stock Summary and Index Summary providers also
require exact response dates, complete records metadata, and valid source
identity. A target that is no longer an official closed session is rejected;
the runner does not infer a replacement date from weekdays, Yahoo, or a stale
local calendar. Existing verified `DATA_READY` sessions remain immutable.

The captured session log records the official-calendar validation and exact
source-date validation. Retrieval timestamps remain observed acquisition times,
not retroactive publication timestamps.

## Current boundary

At implementation time local Jakarta time was before 18:00. Therefore no real
capture was executed and no scheduler was enabled in this pre-capture step.
The required next step is exactly one post-18:00 controlled EOD run, followed
by read-only artifact/hash verification. Only if that run reaches a valid
terminal result may the canonical task be enabled and the legacy task disabled.

## Scope preserved

Stockbit intraday automation remains unchanged. No outcomes,
`FORWARD_OUTCOME_ACCESS_STARTED`, model refit, Path Risk, OPEN historical
backfill, or historical PIT work was accessed.
