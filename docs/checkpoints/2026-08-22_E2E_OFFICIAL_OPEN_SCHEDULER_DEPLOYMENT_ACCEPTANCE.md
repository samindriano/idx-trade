# E2E Baseline Paper V1 — Official Open Scheduler Deployment Acceptance

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`
Validated implementation anchor: `a17d580a0dbd89c648215043281b6f995385bec2`
Pre-deployment branch HEAD: `ace5587e43b986aedd8b4f4fd767417ee74691fc`

## Deployment result

The dedicated Windows morning scheduler for execution-grade official IDX `OpenPrice` evidence is now installed and operationally smoke-tested.

Task:

`IDXTrade-E2E-OfficialOpen`

State after installation:

- task registration: PASS;
- task state: `Ready`;
- enabled: `True`;
- runtime root: `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1`;
- Python executable: `C:\Users\Sam\AppData\Local\Programs\Python\Python313\python.exe`;
- runner: `scripts\run_official_open_capture.ps1`;
- no API key is present in task arguments;
- repository remained clean after installation and smoke run.

## Trigger contract

Registered triggers:

- 09:02 Asia/Jakarta;
- 09:07 Asia/Jakarta;
- 09:12 Asia/Jakarta;
- 09:17 Asia/Jakarta;
- 09:22 Asia/Jakarta;
- AtLogOn catch-up.

Task settings retain:

- `StartWhenAvailable`;
- `MultipleInstances IgnoreNew`;
- network availability requirement;
- current Windows user principal;
- limited run level as defined by the installer.

## Weekend headless smoke

A manual `Start-ScheduledTask` run was executed after installation on Saturday, 2026-08-22.

Observed:

- `LastTaskResult = 0`;
- runtime status: `WEEKEND_NO_SESSION`;
- `session_date = 2026-08-22`;
- no IDX capture attempt was required;
- no Zapi capture attempt was required;
- no historical/backfill capture occurred;
- runtime log was written only under the dedicated runtime root;
- repository remained clean.

`latest_capture.json` recorded:

```json
{
  "current_session_only": true,
  "session_date": "2026-08-22",
  "status": "WEEKEND_NO_SESSION"
}
```

## Accepted transport lineage

The deployed runtime uses the already validated policy:

`DIRECT_IDX_THEN_ZAPI_RAW_V1`

Primary:

`DIRECT_IDX_HTTPS`

Secondary on transport failure only:

`ZAPI_IDX_RAW_PASSTHROUGH`

Source semantics remain frozen:

- authority: `IDX`;
- upstream path: `TradingSummary/GetStockSummary`;
- field: `OpenPrice` only;
- `FirstTrade` is audit witness only;
- price fallback policy: `NONE`;
- missing/non-positive `OpenPrice` remains unavailable;
- no Stockbit/IEP/IEV substitution;
- no prior-session automatic backfill.

The prior real fallback validation on session `2026-06-12` had already passed with direct IDX HTTP 403 followed by Zapi raw HTTP 200, coherent 959/959/959 full-session counts, exact AADI/BBCA/BBRI witnesses, successful certification, and successful execution verifier admission.

## Operational state

Official Open transport and scheduler deployment gates are now accepted.

The next operational observation is the first genuine weekday same-session run. That observation is monitoring, not a prerequisite for continuing CA/dividend/persistent E2E integration.

Verdict:

`OFFICIAL_OPEN_MORNING_SCHEDULER_INSTALLED_WEEKDAY_LIVE_CAPTURE_PENDING`
