# Forward EOD Automation / Open / O2 / Intraday Result

Date: 2026-08-12 (Asia/Jakarta)
Branch: `integration/forward-eod-automation-monitoring`
Status: `CONTROLLED_CAPTURE_PASS_SCHEDULER_INSTALL_BLOCKED`

## Runtime and capture result

External runtime:
`D:\Documents\Project\idx-trade-data-gate-20260808v`

The final controlled headless run completed with `NO_MISSING_SESSION` after
capturing the earliest missing official session, `2026-08-11`. The official
IDX calendar available at capture time ended at `2026-08-11`; `2026-08-12` was
not present in that calendar and was not inferred or captured.

Successful capture log:
`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\eod_automation\runs\20260812T110751Z-4d52e089.json`

The final latest-run log is:
`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\eod_automation\latest.json`

Successful `2026-08-11` capture:

- Stock Summary: 963 rows, `recordsTotal=963`, `recordsFiltered=963`;
- Index Summary: 45 rows, `recordsTotal=45`, `recordsFiltered=45`;
- active regular-market rows: 832;
- model-safe rows: 832;
- local price hits: 0; downloaded accepted price rows: 832;
- Open/H/L/C/Volume sidecar: complete for all 832 model-safe rows;
- model-input SHA-256: `d2dc3b29d51587050011e85dd621bceee3e501bb91419975fc5405cc7423c63e`;
- session OHLCV SHA-256: `602318b7ff3abde819be0f6fac87d187078371b6483d34a4ca13052bd3b2c88a`;
- Stock Summary raw SHA-256: `3fceb51a437cab058df00d3949649abcc758de8638315e070e12a6e5371a2ea2`;
- Index Summary raw SHA-256: `bd0349d88b7e0cee986b11f23b26209a854dd8da6815dde52460f74890580bfd`;
- model-input schema remained unchanged;
- outcome access remained `LOCKED` and no forward marker was written.

V2 and V3-B fan-out artifacts for `2026-08-11` both reached `DONE`:

- V2 score artifact SHA-256: `8c4e8bf42dca341925c545646500e408d12ba6db7ce454a1b4beab86cf9f54e0`;
- V3-B score artifact SHA-256: `b53c50c6204d9e416a32a3ccd88ca5c743e13184609bfff4d41ee1b822ae5cc7`.

The O2 freeze is `2026-08-12T07:45:30+07:00`. Since the `2026-08-11`
official session began before that freeze, it is correctly excluded from O2
fresh-forward scoring. O2 remains at zero until the first official session
starting strictly after the freeze has a complete immutable OHLCV sidecar.
O2 now uses the existing `model_runs` fan-out contract; no separate O2 ledger
or duplicate V3-B score is created.

## Legacy Open repair

The original `model_input.parquet` artifacts were not rewritten:

| Session | Rows | Original model-input SHA-256 | Open sidecar SHA-256 |
|---|---:|---|---|
| 2026-08-03 | 831 | `fbc5d9293e40e5bf71aaa0f0d3a2cbfe1e7bbcc7cbecb1bd9ce2825a6af6fd21` | `e74a228f304b509f24e93bb69a6a50c8ce9af42372fb840b95b8aa01303eb867` |
| 2026-08-10 | 837 | `40667bff222c6d9c1f4bc0352f530ac9dd51c498e3ee5234db731d3fb66c3a0e` | `000f0e903b93ea7c28a735f0c33089d12d61959b410fc6121fcf51add33f92e8` |

Both sidecars contain complete Open/H/L/C/Volume rows from the existing
accepted Yahoo/yfinance `auto_adjust=False` daily provider lineage. They carry
later recovery provenance. `observed_retrieved_at_utc` is not a historical
publication timestamp. No direct IDX Open call was made.

The legacy repair initially exposed two source-contract defects and they were
fixed fail-closed:

1. legacy volume revisions must not block H/L/C Open recovery; H/L/C remain
   hard reconciliation fields while the old model input remains immutable;
2. official Stock Summary includes the valid five-character code `GOTOM`
   (MVS), so the source validator now accepts official 4–5-character codes
   and still rejects other malformed codes.

## Scheduler and laptop-off behavior

The canonical installer defines exactly one new task, `IDXTrade-ForwardEOD`,
with:

- daily 18:00 trigger;
- interactive logon catch-up trigger;
- `StartWhenAvailable`;
- `MultipleInstances=IgnoreNew`;
- hidden PowerShell action;
- existing runtime root and headless runner;
- chronological/idempotent catch-up through the existing capture engine.

Registration was attempted after the successful controlled capture but Windows
returned `Access is denied` because the current Codex process is medium
integrity/non-elevated. Therefore:

- `IDXTrade-ForwardEOD` is **not installed**;
- `IDXTrade-ForwardOpenArchive` remains enabled and unchanged;
- `IDX-Trade Stockbit Intraday Daily` remains enabled and unchanged.

An elevated/admin one-time execution of the existing installer is required;
the script performs preflight, registers the task, verifies registration, then
disables only the superseded Open task and verifies that disablement. No task
was partially registered.

## Monitoring UI

`/monitoring` remains read-only for model progress. Manual capture/date
controls remain removed. The page exposes existing Stockbit task health and
the shared V2/V3-B/O2 model-run progress. The Stockbit runtime-root fallback
now points to the existing child runtime:
`<IDX_TRADE_RUNTIME_ROOT>\stockbit_intraday_recurring_v1`.

## Leakage boundary

Putting a completed session into the archive later is not automatically data
leakage. It is valid outcome-blind archival when the source is acquired after
close, the actual retrieval time is recorded, no future labels/outcomes are
read, and the data is not backdated as if it were known earlier. It does not
retroactively make the session eligible for a frozen model contract. This is
why `2026-08-11` is valid for V2/V3-B prospective monitoring after capture but
not for O2, whose freeze boundary starts after that session.

No modelling, refit, realized outcome, `FORWARD_OUTCOME_ACCESS_STARTED`, Path
Risk, Stockbit capture change, or historical PIT work was performed.

## Validation

- focused forward/provider/OHLCV/model/runner tests: passed;
- full pytest: passed, 257 collected, 3 existing FutureWarnings;
- Next.js production build: passed, one non-blocking filesystem tracing warning;
- PowerShell installer parse: passed;
- controlled capture: terminal `NO_MISSING_SESSION` after successful Aug11;
- scheduler installation: blocked only by Windows permission (`Access is denied`).
