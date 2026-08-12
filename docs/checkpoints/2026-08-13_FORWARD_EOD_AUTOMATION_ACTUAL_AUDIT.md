# Forward EOD Automation Actual Audit — 2026-08-13

Status: `BLOCKED_CANONICAL_TASK_ABSENT_LEGACY_STILL_ENABLED`

This is a read-only audit of the local Windows automation and runtime state. No
Task Scheduler entry, model, data contract, protected outcome, or Reliability
V1 artifact was changed.

## Repository and evidence boundary

- Repository: `samindriano/idx-trade`
- Branch: `integration/forward-eod-automation-monitoring`
- audited source commit: `c5b356ad1a21646c4d6b50352872c7e6718c6df9`
- runtime root: `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring`
- local verification time: `2026-08-13 02:18:56 +07:00`
- protected outcomes were not read; the runtime manifests remain
  `outcome_blind=true` and `forward_outcomes_accessed=false`.

## What the prior Access-denied resolution actually did

The repository contains the bounded installer
`scripts/install_forward_eod_task.ps1`. Its intended operation is:

1. register one hidden `IDXTrade-ForwardEOD` task;
2. schedule it daily at `18:00` Asia/Jakarta and at interactive logon;
3. use `StartWhenAvailable`, `MultipleInstances=IgnoreNew`, a two-hour limit,
   and `RunOnlyIfNetworkAvailable`;
4. invoke `scripts/run_forward_eod_catchup.ps1`, which runs the canonical
   `idx_trade.forward_eod_runner`; and
5. disable `IDXTrade-ForwardOpenArchive` only after registration.

The earlier controlled capture succeeded for 2026-08-11 and 2026-08-12, after
three fail-closed retries on 2026-08-12. The subsequent registration attempt
was made from a non-elevated medium-integrity process and returned Windows
`Access is denied`. The installer did not create a partial canonical task, and
the legacy task was not disabled. There is no later repository or local-machine
evidence of an elevated installer run.

## Actual Task Scheduler state

Read-only `Get-ScheduledTask` inspection found exactly these relevant tasks:

| task | actual state | trigger/next run | last result |
|---|---|---|---|
| `IDXTrade-ForwardEOD` | **NOT_FOUND** | none | none |
| `IDXTrade-ForwardOpenArchive` | `Ready` | daily `22:00` plus logon; next `2026-08-13 22:00 +07:00` | `1` |
| `IDX-Trade Stockbit Intraday Daily` | `Ready` | weekdays `16:35` and `17:30`; next `2026-08-13 16:35 +07:00` | `0` |

The legacy task still runs from the old isolated worktree and data root. Its
latest runtime record is `BLOCKED_SOURCE_NOT_FROZEN` at
`2026-08-12 22:00:04 +07:00`; it did not produce canonical EOD artifacts.

Therefore the claimed Access-denied gap is **not resolved on this machine**.
The canonical EOD collector is not installed or enabled, and automatic
collection for the next IDX session is not currently safe to claim.

## Latest canonical artifacts

The latest successful canonical session is `2026-08-12`.

- Stock Summary: `963/963` rows; raw and normalized artifacts present.
- Index Summary: `45/45` rows; raw and normalized artifacts present.
- official ACTIVE regular-market tickers: `836`.
- model-safe input rows: `836`.
- session OHLCV sidecar: present for `836` rows.
- model scoring: V2, V3-B, and O2 score artifacts are all present and `DONE`.
- O2 counter: `1/100`, first post-freeze session index `1268`.
- outcome access remains locked.

Selected SHA-256 values from the 2026-08-12 session:

| artifact | SHA-256 |
|---|---|
| `idx_stock_summary.raw.json` | `816d6e96c736ed11518720bd5a27a6896c3385760c32332319e2ec8dc65bbcb6` |
| `idx_stock_summary.csv` | `1a00bbd74ad3d887c59ad81d59d2c2a84a75077fab5d56323eb311eefe3e97d3` |
| `idx_index_summary.raw.json` | `496c7ebff0be317f80450503d2aac46d40f383f6d9cc3ff50b7480e188b12ccf` |
| `idx_index_summary.csv` | `75cc8f7c4d409c9c38f6cfaae687c96116094859bb6d0703fb2e44f67614e866` |
| `model_input.parquet` | `51cfe9abacd322f330025b0bcd43d569f6fbb715b53aea3c27ead7588d16b00b` |
| `session_evidence.parquet` | `51abd380f7cc4912b889ca0c8b3ae86c3b3b7ba0ad4b69932edacc9f2eb021b5` |
| `session_ohlcv.parquet` | `0714942c7cc72a7ff93537a31847e451628dffa59112cce87a031bd9d14449e5` |
| `manifest.json` | `39f5d02a37a59930ed02ecdbf98fbf5260ed2e6ce5754ff7f558d04357e8d51c` |
| V2 `score_artifact.parquet` | `abcb0270e2f90281fd45c19aacb8c13cc6ae5308cbd6f4d3464ef7b461c5d336` |
| V3-B `score_artifact.parquet` | `d8827d7a5146a029afe1adf556619f0cdaf95291d349d66ed38f19cab8568b99` |
| O2 `score_artifact.parquet` | `b7fc6f22230500d65c1a24c4333b5601c0102da5bb99c3cae77a85bdb112c42d` |

The preceding canonical session `2026-08-11` also has complete Stock Summary,
Index Summary, OHLCV, evidence, model-input, and model-score artifacts.

## Foreign-flow retention

The raw 2026-08-12 Stock Summary contains `ForeignBuy` and `ForeignSell` for
all `963/963` rows; both fields are non-null in the preserved raw JSON. The
same is true for 2026-08-11. The normalized `idx_stock_summary.csv` does not
carry those two fields, so downstream consumers must read the preserved raw
JSON if foreign-flow analysis is required. This is a visibility caveat, not a
loss of the archived raw evidence.

## Failure, recovery, holiday, and idempotence behavior

The canonical runner is fail-closed and chronological in code:

- `_earliest_missing` scans the official calendar in sorted order and returns
  the first non-`DATA_READY` session.
- `capture_session` rejects a requested date that would skip an earlier missing
  session and validates exact official calendar/source dates.
- Stock Summary, Index Summary, unresolved point evidence, and missing ACTIVE
  prices raise a `DATA_FAILED` attempt rather than creating a partial final
  session.
- the EOD runner stops on the first failure, returns exit code `1`, and retries
  the same earliest missing session on a later invocation.
- verified sessions are create-once/idempotent; stale/incomplete captures are
  reconciled or marked failed rather than silently treated as ready.
- holidays are absent from the official exchange-session calendar, so the
  runner does not invent holiday captures. Calendar-sync failure is explicit,
  not a silent skip.

The actual 2026-08-12 run proves this recovery path: three failed attempts
(volume disagreement, invalid Stock Summary ticker, and partial Index Summary)
were followed by a successful chronological capture of 2026-08-11, then a
successful capture of 2026-08-12. No `DATA_READY` artifact was emitted by the
failed attempts.

The intended scheduler settings would provide missed-run catch-up through
`StartWhenAvailable` and interactive-logon catch-up. `WakeToRun` is not set on
the canonical installer, so a sleeping laptop is not actively woken at 18:00;
resume/logon catch-up is the intended path. Because the canonical task is
currently absent, none of those guarantees is active at present.

## Stockbit separation

Stockbit remains a separate `Ready` task with a separate worktree,
PowerShell entrypoint, and runtime root. Its 2026-08-12 run completed in
`SHADOW` mode with `962` attempted tickers, `835` successful tickers, zero
429 events, and no synthetic fill. Its policy state remains `SHADOW`; it is
not the canonical EOD task and does not share the canonical session registry.

## Decision and recommendation

Current decision: **NO-GO for claiming automatic canonical EOD collection**.

The existing installer needs to be run once from an elevated PowerShell
context by an authorized operator. After that, verify all of the following
read-only before relying on the next session:

1. `IDXTrade-ForwardEOD` exists and is `Ready`;
2. its daily 18:00 and logon triggers, `StartWhenAvailable`, network guard,
   and `IgnoreNew` settings match the script;
3. `IDXTrade-ForwardOpenArchive` is `Disabled`; and
4. Stockbit remains unchanged and separate.

The installer is sequential rather than transactional: it registers the
canonical task before disabling the legacy task. If the disable step fails,
both tasks could coexist, so the post-install verification above is required.
No scheduler change was made in this audit.
