# GitHub Schedule Trigger Remediation V1

Date: 2026-08-27 Asia/Jakarta  
Lane: `ops/github-schedule-watchdog-v1`  
Status: `IMPLEMENTED_PENDING_RUNTIME_INSTALL_AND_POST_CLOSE_PROOF`

## Incident evidence

The target workflows were enabled and active in the authenticated GitHub API,
but no `event=schedule` run was observed for the 2026-08-27 morning slots.
The untouched Stockbit Stream canary window from 12:07 through 12:16 WIB also
produced zero new target-workflow runs. The morning incident is therefore
classified as:

`MISSED_GITHUB_SCHEDULE_TRIGGER`

The accessible repository state was:

- default branch: `main`;
- Actions: enabled;
- workflow permission default: read;
- E2E Paper, Official Open, Stockbit Intraday, and Stockbit Stream workflows:
  active;
- target workflow runs since 00:00 WIB on 2026-08-27: none at the canary audit;
- no API evidence of a manually disabled workflow or an Actions permission
  denial.

One provider-free manual diagnostic dispatch was performed only after the
canary failed:

- workflow: `E2E Paper synthetic cloud rehearsal`;
- run: `33042090215`;
- result: `success`;
- event: `workflow_dispatch`;
- guards: synthetic-only, zero provider calls, zero protected-outcome access,
  zero production PaperState/order/fill/counter mutation.

This separates workflow-dispatch delivery from GitHub's native schedule-event
delivery.

## Trigger-only fallback

No Cloudflare Worker/Wrangler project or authenticated Wrangler context was
available in the local environment. Wrangler is not installed. No Cloudflare
resource, secret, or binding was created or changed. The authorized fallback is
therefore a reversible Windows watchdog.

The watchdog is `scripts/github_schedule_watchdog.py`. It only:

1. queries GitHub Actions run metadata through the existing `gh` credential
   store;
2. if no current-day run exists for the due slot, dispatches the existing
   workflow on `main`;
3. records a non-secret slot marker and JSONL operational event under the
   external state root.

It never imports or calls a market-data provider, capture runtime, R2, Paper-
State, order/fill, counter, target, or outcome path. It has no credential
argument and does not persist command output.

The existing production workflows remain the only capture implementations:

| WIB slot | Workflow | Dispatch input |
| --- | --- | --- |
| 18:30 | Stockbit Intraday cloud production | `slot=1830` |
| 18:35 | E2E Paper cloud orchestration | `phase=POST_EOD` |
| 19:05 | E2E Paper cloud orchestration | `phase=POST_EOD` |
| 19:30 | Stockbit Intraday cloud production | `slot=1930` |
| 19:35 | E2E Paper cloud orchestration | `phase=POST_EOD` |
| 20:30 | Stockbit Intraday cloud production | `slot=2030` |

The task's four daily checks are at approximately 18:40, 19:10, 19:40, and
20:40 WIB, plus `AtLogOn`. Each check is restricted to the current Jakarta
date and a two-hour late grace window; it does not backfill a previous date.
Weekend/logon outside a due window is a no-op.

Native and watchdog runs are duplicate-safe at the trigger layer: an existing
`schedule` or `workflow_dispatch` run in the slot window suppresses a new
dispatch. A successful watchdog request creates a per-slot marker; if GitHub
run visibility is delayed, the marker prevents repeated dispatches and records
`DISPATCH_ALREADY_REQUESTED_NO_VISIBLE_RUN` for operator review.

The production workflows' own concurrency/idempotency and current-session
guards remain authoritative. A watchdog query failure or dispatch failure is
fail-closed and never turns into provider capture.

## Existing local automation isolation

The existing `IDX-Trade Stockbit Intraday Daily` Windows task remains disabled
to prevent dual writes while cloud Intraday is active. It was not re-enabled
or modified by this lane. Reversible rollback, if needed, is:

```powershell
Enable-ScheduledTask -TaskName 'IDX-Trade Stockbit Intraday Daily' -TaskPath '\\'
```

`IDXTrade-E2E-Paper` and `IDXTrade-ForwardEOD` remain untouched.

## Validation status

- watchdog focused tests: 6 passed;
- Python compile: pass;
- PowerShell installer parse: pending final install validation;
- workflow-dispatch diagnostic: success as recorded above;
- production post-close trigger proof: pending the first genuine slot;
- no provider capture was initiated by this remediation.

The stronger closure state is only warranted after the watchdog is registered
and one genuine post-close slot is observed through the existing cloud workflow
path.
