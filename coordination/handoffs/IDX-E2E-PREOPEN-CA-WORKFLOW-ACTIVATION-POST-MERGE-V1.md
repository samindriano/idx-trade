# Handoff: E2E PREOPEN_CA Workflow Activation — Post-Merge

from: Codex
to: MAIN / ChatGPT review
task_id: idx-e2e-preopen-ca-workflow-activation-post-merge-v1
source_repository: samindriano/idx-trade
source_commit: `53767b2ba1cbc7faffe315b6ae1d575612323a7c`
branch: `main`
scope: Post-merge verification of V3 cloud E2E activation and reversible Stockbit single-writer suppression.

## Findings

- PR #109 is merged with merge commit `53767b2ba1cbc7faffe315b6ae1d575612323a7c`.
- Main workflow bytes invoke the accepted V3 runner pinned to `6e1bf4a1e47a2abff365b35c19687444cf3f0596`.
- `PREOPEN_CA` is mapped to 08:30/08:45/08:55 WIB; `PREOPEN` remains 09:03/09:13/09:22 WIB; `POST_EOD` remains 18:35/19:05/19:35 WIB.
- Phase concurrency groups are isolated and V3 enforces the 09:02 WIB cutoff.
- Windows task `IDX-Trade Stockbit Intraday Daily` was enabled at the same Stockbit cloud slots and is now disabled reversibly. Its task definition remains available.

## Decisions

- Cloud E2E is activated in production main.
- Cloud Stockbit Intraday is the single automatic writer during the first proof; Windows fallback is retained but automatic execution is suppressed reversibly.
- No manual cloud/provider run is required or authorized before the next genuine scheduled slot.

## Validation

- Activation: 3 passed.
- Accepted V3: 11 passed.
- PREOPEN_CA/recovery/consumer: 15 passed.
- Full pytest: 838 passed, 3 existing warnings.
- PR CI pytest: passed, run `32995925560`.
- Actual main workflow byte checks: V3 present, V2 absent, all required cron literals and phase dispatches present.

## Rollback

```powershell
Enable-ScheduledTask -TaskName 'IDX-Trade Stockbit Intraday Daily' -TaskPath '\\'
```

## Boundary

The first genuine scheduled 2026-08-27 cloud proof remains pending. No provider call, R2 write, model/counter mutation, scheduler installation, or protected outcome access was performed by this verification.
