# GitHub Actions Cost Optimization V1 — bounded review checkpoint

Status: `READY_FOR_INDEPENDENT_REVIEW`

This checkpoint records a deliberately bounded optimization of hosted bootstrap
and ordinary CI compute. It does not change any capture schedule, provider
request, universe, field set, recovery opportunity, R2 contract, or scientific
runtime. The review branch is `codex/actions-cost-optimization-v1`, based on
`origin/main@bd166f7fd143fb4c2b48ef6b4f60e549e5c0fde5`.

## Architecture and inventory

The canonical capture families remain Official Open, EOD Market, Corporate
Actions, Stockbit Stream, and Stockbit Intraday. The scheduled production
surface has 18 logical opportunities on a weekday: E2E Paper 9, Official Open
3, Stockbit Stream 3 (calendar-day), and Stockbit Intraday 3. Weekends retain
the three Stockbit Stream observations. Cloudflare has a five-cron
staging-live configuration and a five-cron production configuration, but neither
is deployed or used as production proof by this change. Windows watchdog
fallback remains retained.

The intended data path is still:

`scheduled opportunity -> existing capture runtime -> immutable evidence/R2 -> existing downstream admission`

Cloudflare and the Windows watchdog remain trigger-presence redundancy. The
current Cloudflare Worker has no R2/object-store binding and accepts exact
GitHub run metadata without inspecting run conclusion or durable capture
artifacts. It is therefore not a completion oracle. No new fast-skip path was
added: an early R2 probe would require a new cross-family authority contract and
could false-skip a missing or partial capture.

## Evidence-backed cost sinks

Recent successful GitHub runs show bootstrap work is material relative to short
jobs, while capture time remains the useful work:

| Run | Workflow | Bootstrap evidence | Useful-work evidence |
|---|---|---:|---:|
| `33350458826` | E2E Paper | `setup-uv` 3 s; install step 26 s | cloud stage 97 s |
| `33317094874` | Stockbit Stream | install step 20 s | capture 462 s |
| `33169532655` | Stockbit Intraday | install step 19 s | capture 65 s |
| `33355320532` | normal tests | install step 17 s | pytest 88 s |

These are measured historical step durations, not a post-change benchmark.
Current-day scheduled failures were account billing/spending-limit failures
before runner execution; they are not treated as savings or capture proof.

## Implemented minimum changes

- Removed the unnecessary `pip --upgrade pip` network/bootstrap operation from
  the four scheduled production capture workflows and normal test CI. Manual
  smoke, preflight, and rehearsal workflows retain their baseline bootstrap
  contract because their separate validation value outweighs their infrequent
  cost.
- Retained the E2E `astral-sh/setup-uv` step because the pinned E2E V1 runner
  passes its executable to the runtime; this proposed saving was rejected by
  the read-only audit.
- Changed Stockbit Stream production from `.[dev,archive]` to `.[archive]`.
  The production entrypoint does not import pytest; its capture and archive
  dependencies remain unchanged.
- Added `paths-ignore` for Markdown, `docs/**`, and `coordination/**` to both
  `push`-to-main and `pull_request` triggers of normal `tests.yml`. Any
  executable or workflow change still runs CI.
- Added latest-head concurrency cancellation only to normal `tests.yml`.
  Production capture workflows retain `cancel-in-progress: false` and all
  existing slot isolation.

No capture workflow schedule or production concurrency key changed.

## Schedule preservation

The exact cron sets remain:

- E2E: `30 1`, `45 1`, `55 1`, `3 2`, `13 2`, `22 2`, `35 11`, `5 12`,
  `35 12` UTC on weekdays.
- Official Open: `2 2`, `12 2`, `22 2` UTC on weekdays.
- Stockbit Stream: `47 1`, `7 5`, `47 9` UTC every calendar day.
- Stockbit Intraday: `30 11`, `30 12`, `30 13` UTC on weekdays.

The CI filter changes only whether a test job is created for documentation-only
changes; it does not apply to production capture workflows.

## Existing integrity and recovery contracts

Existing runtime-specific contracts remain authoritative: Stockbit Stream has
immutable manifest/idempotent replay and residual resume; Stockbit Intraday
checks existing commits and resumes verified progress; Cloudflare and watchdog
keep exact logical slot IDs, bounded windows, and fail-closed query behavior.
Typed failure behavior remains in the existing Cloudflare and Intraday paths;
this checkpoint does not introduce a shared error taxonomy.

The following were explicitly rejected for this bounded change:

- R2/provider completion probes before bootstrap, because no single portable
  read-only authority is exposed across all current families.
- GitHub run status as a completion signal, because a queued, failed, or
  successful run is not equivalent to durable capture completion.
- Changing production cron count, retry windows, concurrency, watchdog markers,
  Cloudflare state, or Windows fallback behavior.
- A new telemetry workflow or shared telemetry framework. Existing job-step
  timestamps, runtime status/provider-call fields, watchdog events, and
  Cloudflare result logs are available; a uniform cross-family bootstrap timing
  schema remains a follow-up requirement, not a reason to add another layer
  here.

Stockbit Stream remains outside the Cloudflare/watchdog redundant trigger path.
No provider, outcome, counter, PaperState, R2, token, secret, Cloudflare, or
Windows Task action occurred.

## Budget and rollback

Proposed priority order is P0 production capture/recovery, P1 genuine cloud
acceptance/smoke, P2 latest-head PR/final-head CI, and P3 synthetic or historical
work that can run locally. No quota shutdown behavior is implemented.

Measured savings are not yet available because hosted quota/billing failures
prevent a controlled before/after run. Expected savings are limited to avoided
pip self-upgrade, unused uv setup, unused Stream pytest installation, and
cancelled/omitted stale or documentation-only CI. Production logical job count
and capture frequency are unchanged. A later post-reset comparison must measure
install/bootstrap seconds, useful runtime, fast exits, provider calls,
recovery/residual work, and final durable status before claiming a numeric
monthly saving.

Rollback is a normal revert of this branch's workflow/test/checkpoint changes.
Reverting `tests.yml` restores full CI for documentation changes and allows
stale runs to continue; reverting production workflow lines restores the old
bootstrap commands. No production data or deployment state is part of the
rollback.

## Coordination and next gate

The branch proposes a coordination-only correction for the known E2E status
drift: the current workflow pin is `82007457522d6e268de8bd6e1b75762fb76accfe`,
introduced by main commit `b8ff82373de922455fce7139fb8d144e97cf5bfb`; the old
`TEAM_STATUS` text still named `6b6a411...`. The branch also records this lane
as review-only. The canonical ledger remains main-owned and must be refetched
and reconciled by the main owner before any merge.

The next safe step is independent review plus, after quota reset, a controlled
latest-head CI comparison. Genuine scheduled capture proof remains governed by
the existing coordination ledger; this optimization is not that proof.

Result for this bounded slice: `ACTIONS_COST_OPTIMIZED_WITH_DATA_SEMANTICS_UNCHANGED`.
