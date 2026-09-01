# ACTIONS_COST_OPTIMIZATION_V1_POST_RESET_MEASUREMENT

Status: `WAITING_FOR_REPRESENTATIVE_SCHEDULED_PRODUCTION_RUNS`

This is the Phase-1 measurement package for the bounded GitHub Actions cost
optimization integrated on `main@898864b4a8934877dc81086403a2a1068f7a6566`.
No post-reset successful hosted run is available yet, so no after-measurement
or numeric savings claim is made.

## Integration and validation

- Implementation integration main SHA: `898864b4a8934877dc81086403a2a1068f7a6566`.
- Candidate: `codex/actions-cost-optimization-v1@898864b4a8934877dc81086403a2a1068f7a6566`.
- Pre-integration local evidence: focused integrity/cost suite `74 passed`;
  full local pytest `377 passed, 3 warnings`; YAML parse `10` workflows;
  compileall and `git diff --check` passed.
- Post-fast-forward local evidence: focused suite `74 passed`, YAML parse
  `10` workflows, and `git diff --check` passed.
- Automatic push CI after allowance recovery: `tests` run `33415425851`, job
  `pytest` `99727108225`, conclusion `success`. The run was created at
  `2026-08-31T16:40:41Z` and started at `2026-09-01T03:29:49Z`, so the delay
  was recorded rather than hidden. Job duration was about `125 s`; install
  was `16 s`; Test was `102.90 s`; the log reported `377 passed, 7 warnings`.
  This is one successful CI sample, not a production-capture proof.

## Hosted runs and measurement boundary

The following are measured historical successful baselines, not post-change
measurements:

| Representative run | Workflow | Total hosted duration | Bootstrap/install | Useful capture/test work |
|---|---|---:|---:|---:|
| `33350458826` | E2E Paper | 140 s | 26 s install; 3 s setup-uv | 97 s cloud stage |
| `33317094874` | Stockbit Stream | 496 s | 20 s install | 462 s capture |
| `33169532655` | Stockbit Intraday | 96 s | 19 s install | 65 s capture |
| `33355320532` | normal tests | not recorded | 17 s install | 88 s pytest |

## Post-reset production observations

- Stockbit Stream run `33479015238`, job `99764254815`, was a scheduled
  success on `main@be1391fecbba4a7cac0c7a11a6661ea1612a882a`. The run was
  created at `2026-09-01T06:45:49Z` (`13:45 WIB`) but its log carried
  `EVENT_SCHEDULE=47 1 * * *`, the `08:47 WIB` pre-open slot, not the requested
  `12:07 WIB` slot. It is therefore a delayed scheduled observation, not an
  on-time 12:07 proof.
- The Stream job ran from `06:45:52Z` to `06:53:31Z` (about `459 s`). Install
  ran from `06:45:54Z` to `06:46:17Z` (about `23 s`); the capture step ran from
  `06:46:17Z` to `06:53:28Z` (about `431 s`). Runtime evidence reported
  `completed_calls=200`, `successful_responses=200`, `status=DATA_READY`,
  `counter_mutated=false`, `model_accessed=false`, and `outcome_accessed=false`.
  This is the first post-reset successful production capture sample, with no
  claim beyond the evidence exposed by the run.
- Against the historical Stream install sample of `20 s`, this sample measured
  `23 s` (a single-sample `+3 s` variance, not a saving). Aggregate savings and
  the requested 12:07 measurement remain pending.
- Stream run `33494770035`, job `99814281125`, was a scheduled success on
  `main@75c3e8ed5fdb45b0d4f99e5340f8103d225d3d24` with
  `EVENT_SCHEDULE=7 5 * * *` and `STOCKBIT_STREAM_SLOT=midday`, the requested
  `12:07 WIB` logical slot. It was created at `2026-09-01T09:55:47Z`
  (`16:55 WIB`), about `4 h 48 m` after the logical slot, so it is a delayed
  scheduled observation rather than on-time timing proof.
- The Stream job ran from `09:55:50Z` to `10:03:33Z` (about `463 s`). Install
  ran from `09:55:57Z` to `09:56:15Z` (about `18 s`); the capture step ran from
  `09:56:15Z` to `10:03:30Z` (about `435 s`). Runtime evidence reported
  `completed_calls=200`, `successful_responses=200`, `status=DATA_READY`,
  `counter_mutated=false`, `model_accessed=false`, and `outcome_accessed=false`
  for run `2026-09-01_midday_dd6d14a0f8ac4f24_466550e9eed9e789`.
- Against the historical Stream samples (`20 s` install and `462 s` useful
  capture), this sample measured `18 s` install (`-2 s`) and `435 s` capture
  (`-27 s`). These are two isolated Stream observations, with one delayed
  pre-open sample and one delayed midday sample; they are not yet a robust
  aggregate production saving.
- Delayed E2E PREOPEN_CA runs `33477900776`, `33478995730`, and `33479797175`
  failed with `MISSED_PREOPEN_CA_CAPTURE`; their controller evidence reported
  no provider calls, no outcome access, and no PaperState mutation. Delayed
  Official Open run `33480505350` failed before execution admission with
  `OFFICIAL_OPEN_TRANSPORT_CHAIN_FAILED`; it reported no outcome access or
  forward-counter mutation. These delayed events are not acceptance proofs and
  were not rerun or backfilled.

The first available post-reset successful sample is CI run `33415425851`:
`125 s` job duration, `16 s` install, and `102.90 s` pytest. Against the
historical `17 s` install sample, this is a measured single-sample `1 s`
install delta; it is not yet a representative aggregate saving.

Post-reset production after-values are now available for two delayed Stream
observations, including their runner/install/capture durations, provider-call
counts, conclusions, and `DATA_READY` status. Intraday and E2E POST_EOD
production after-values remain
`NOT_AVAILABLE_AWAITING_SCHEDULED_PRODUCTION_RUNS`; the E2E runs observed so
far were delayed PREOPEN no-op/availability observations, not captures. The CI
values above remain a separate measurement class and are not production
capture evidence.

Actual measurable savings: one CI install sample shows `1 s` lower install
time than the historical sample; production and aggregate savings remain
`NOT_YET_MEASURABLE`. Estimated opportunities from removing pip self-upgrade,
removing unused Stream test installation, and omitting the exact
coordination-only CI run remain estimates, not measured savings.

## Capture integrity and next measurement

The two Stream runs produced `DATA_READY` archive results, but no new E2E
prospective acceptance proof was produced by this integration or by the CI run
above. The Stream results are delayed observations and are reported separately
from E2E acceptance.
The existing capture/recovery contracts remain authoritative, and the
2026-08-27 prospective result remains governed by the coordination ledger.
If scheduled capture fails after allowance reset, prospective data recovery has
priority over cost measurement under the existing approved recovery semantics.

After the reset, observe several representative successful scheduled production
runs (and retain CI as a separate measurement class)
without changing schedules. Record exact run IDs and total, bootstrap, useful
runtime, provider-call, retry/no-op, conclusion, and durable-status evidence;
separate measured values from estimates. Phase-2 completion-aware retry is
`DEFERRED / NOT_STARTED`; it must not begin in this task.

Remaining wasted compute includes per-run package installation and any
pre-start billing failures. No new telemetry or completion oracle was added.
Production frequency, field/quality semantics, provider behavior, R2, Cloudflare,
Windows fallback, and scientific behavior remain unchanged. No manual dispatch,
provider call, deployment, backfill, token/secret change, or production state
mutation occurred.
