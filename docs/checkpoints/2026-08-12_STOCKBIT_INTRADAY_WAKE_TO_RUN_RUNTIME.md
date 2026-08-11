# Stockbit Intraday Scheduled Task WakeToRun Runtime

Date: 2026-08-12 (Asia/Jakarta)  
Branch: `data/stockbit-intraday-forward-capture-v1`  
Starting remote HEAD: `d28623fcec83887d700a01622245f51ac79eec38`  
Decision: `STOCKBIT_INTRADAY_WAKE_TO_RUN_REREGISTERED_STOP`

## Scope

Re-registered the existing Windows Scheduled Task using the updated installer
that enables `WakeToRun`. No task trigger was manually invoked and no
Stockbit/IDX network capture was performed.

Recurring data root remained empty:

`D:\Documents\Project\idx-trade-data-gate-20260808v\stockbit_intraday_recurring_v1`

## Registration

- Installer exit code: **0**.
- Task name unchanged: `IDX-Trade Stockbit Intraday Daily`.
- First trigger boundary supplied: **2026-08-13**.
- Installer confirmed `WakeToRun: enabled`.
- Persistent User-level `ZAPI_API_KEY` remained the credential source; the
  value was never displayed or embedded.

## Post-registration task verification

- State: **Ready**.
- Enabled: **true**.
- `WakeToRun`: **true**.
- `StartWhenAvailable`: **true**.
- `MultipleInstances`: **IgnoreNew**.
- Primary: Monday-Friday at **16:35 WIB**.
- Recovery: Monday-Friday at **17:30 WIB**.
- Next run: **2026-08-13 16:35 WIB**.
- Last run: sentinel/no run.
- Missed runs: **0**.
- API key in task XML: **false**.
- API key in task arguments: **false**.
- Recurring data-root files after re-registration: **0**.

The intended future session remains unchanged. No manual trigger or capture was
performed during this configuration update.
