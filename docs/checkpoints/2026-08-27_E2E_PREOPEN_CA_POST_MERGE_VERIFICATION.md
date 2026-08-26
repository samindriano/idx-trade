# E2E PREOPEN_CA Post-Merge Verification — 2026-08-27

Status: `REVIEW`

## Activation result

- Activation PR: `#109`, merged at `53767b2ba1cbc7faffe315b6ae1d575612323a7c`.
- Accepted implementation pin in the production workflow:
  `6e1bf4a1e47a2abff365b35c19687444cf3f0596`.
- Main workflow file: `.github/workflows/e2e-paper-cloud-orchestration.yml`.
- The actual `origin/main` bytes invoke `run_e2e_paper_cloud_v3.py`; no V2 runner invocation remains.

## Actual production schedules

GitHub Actions cron is UTC; times below are Asia/Jakarta:

| Phase | GitHub cron | WIB |
|---|---|---|
| `PREOPEN_CA` | `30 1 * * 1-5`, `45 1 * * 1-5`, `55 1 * * 1-5` | 08:30, 08:45, 08:55 |
| `PREOPEN` | `3 2 * * 1-5`, `13 2 * * 1-5`, `22 2 * * 1-5` | 09:03, 09:13, 09:22 |
| `POST_EOD` | `35 11 * * 1-5`, `5 12 * * 1-5`, `35 12 * * 1-5` | 18:35, 19:05, 19:35 |

Scheduled phase resolution explicitly maps all three phase families. V3 retains the hard 09:02 WIB PREOPEN_CA cutoff. The workflow uses separate `preopen-ca`, `preopen`, and `post-eod` concurrency groups, so a queued or hung PREOPEN_CA run cannot queue-block PREOPEN.

## Stockbit single-writer protection

The production cloud workflow remains scheduled at 18:30/19:30/20:30 WIB. Read-only task audit found the legacy Windows task `IDX-Trade Stockbit Intraday Daily` enabled on the same three weekdays/slots. It was disabled reversibly to prevent dual provider writes during the first cloud proof:

```powershell
Enable-ScheduledTask -TaskName 'IDX-Trade Stockbit Intraday Daily' -TaskPath '\\'
```

The task definition and `fix/stockbit-intraday-postclose-fix-v1` fallback remain retained. No task was deleted or edited. `IDXTrade-ForwardEOD`, `IDXTrade-E2E-Paper`, and the already-disabled `IDXTrade-ForwardOpenArchive` were not modified.

## Validation and boundary

- Activation tests: 3 passed.
- Accepted V3 tests: 11 passed.
- PREOPEN_CA/recovery/consumer tests: 15 passed.
- Full pytest: 838 passed, 3 existing warnings.
- YAML parse and `git diff --check`: passed.
- PR CI pytest: passed (`32995925560`).
- No provider capture, R2 mutation, model/counter mutation, or protected outcome access occurred.
- At checkpoint time, the 2026-08-27 genuine scheduled cloud proof remains pending; no manual trigger was used.
