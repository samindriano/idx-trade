# Stockbit Intraday Scheduled Task — WakeToRun Patch

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/stockbit-intraday-forward-capture-v1`
Status: `IMPLEMENTED_NOT_YET_REREGISTERED_LOCALLY`

Independent review of the installed recurring task found that the task had `StartWhenAvailable=true` but did not yet set Windows Task Scheduler `WakeToRun`.

This distinction matters:

- `StartWhenAvailable` allows a missed task to run after the machine becomes available again;
- `WakeToRun` instructs Task Scheduler to wake a sleeping computer before the scheduled run.

Patch:

- `scripts/install_stockbit_intraday_task.ps1` now passes `-WakeToRun` to `New-ScheduledTaskSettingsSet`;
- the installer reports `WakeToRun: enabled` after registration;
- no capture, quota usage, model work, Open/TradingView work, or PIT-sector work was performed by this patch.

The currently registered local task must be re-registered from this updated branch before WakeToRun is actually active on the machine. After re-registration, verify the registered task settings report WakeToRun enabled and that the next run remains the intended future session. Do not manually trigger a capture during this configuration update.
