# Forward EOD Automation Installation — 2026-08-13

Status: `AUTOMATED`

This checkpoint records the post-installation read-only verification. No
provider capture was triggered, and no model, O2 contract, Reliability V1,
outcome, or data schema was changed.

## Installation result

The existing canonical installer was run through a UAC-elevated PowerShell
process using the existing repository and runtime paths. The previous
`Register-ScheduledTask` `Access is denied` blocker is resolved on this
machine.

Verified at `2026-08-13T02:33:04.7965878+07:00` Asia/Jakarta:

| task | state | last result | next run |
|---|---|---:|---|
| `IDXTrade-ForwardEOD` | `Ready` | `0x00041303` (`SCHED_S_TASK_NOT_RUNNING`; no capture run yet) | `2026-08-13 18:00 +07:00` |
| `IDXTrade-ForwardOpenArchive` | `Disabled` | prior result `1` | no execution while disabled |
| `IDX-Trade Stockbit Intraday Daily` | `Ready` | `0` | `2026-08-13 16:35 +07:00` |

The canonical task XML matches the existing installer contract:

- daily trigger at `18:00` Asia/Jakarta;
- interactive logon trigger for catch-up;
- `StartWhenAvailable=true`;
- `MultipleInstancesPolicy=IgnoreNew`;
- `RunOnlyIfNetworkAvailable=true`;
- hidden task, two-hour execution limit;
- existing interactive limited principal;
- action script:
  `C:\Users\Sam\OneDrive\Documents\Project\idx-trade\scripts\run_forward_eod_catchup.ps1`;
- repository/worktree:
  `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`;
- runtime root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v`;
- Python:
  `C:\Users\Sam\AppData\Local\Programs\Python\Python313\python.exe`.

No provider was called by this verification. The canonical task has not yet
run; the first normal scheduled opportunity is 18:00 WIB.

## Separation and secret checks

- The legacy `IDXTrade-ForwardOpenArchive` task is disabled only after
  canonical registration succeeded.
- Stockbit remains enabled with the previously verified separate worktree,
  action, triggers, and runtime root; no Stockbit task definition changed.
- No API-key/secret/password/authorization/bearer field was present in any of
  the three task definitions.
- A read-only scan of the canonical `forward_monitoring` runtime logs found
  zero credential-name hits and zero hit files.

## Operational interpretation

The scheduler is now installed and ready for automatic future sessions. The
canonical runner retains the previously audited fail-closed behavior:
official-calendar ordering, earliest-missing recovery, no holiday invention,
explicit failure on incomplete provider data, and idempotent `DATA_READY`
sessions. `StartWhenAvailable` and logon catch-up cover missed execution; the
task does not actively wake a sleeping laptop because `WakeToRun` is not part
of the canonical installer.

The first scheduled run should be independently checked from its persisted
run log and session manifest after 18:00. That check must not read protected
outcomes or alter the frozen data/model contracts.
