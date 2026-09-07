# Cloud Runtime Recovery Cutover Runbook V1

Status: pre-activation preparation only. Prepared 2026-09-07 (Asia/Jakarta).
This document is not operational authorization and no step in it was executed by
the audit. It covers E2E PREOPEN_CA/PREOPEN/POST_EOD, Official Open, and
Stockbit Intraday. Stockbit Stream remains outside Cloudflare recovery.

## Fixed identities and claims

- Current `origin/main`: `9b070894535c0c0fc13bc441f004f5d0a8039cb9`.
- Local ahead-only candidate: resolve and record `git rev-parse HEAD` immediately
  before authorization; it is based on the current main above and replays the
  dependency-closed PR120 content plus valid PR121 remediation.
- Candidate E2E implementation pin: `8bc3ee3efd65e8b16478e404e4b226451b105c48`.
- Candidate Official Open producer pin: `ac29a0552b1785045906f8d608b5371d93e01b73`.
- Canonical completion authority: independently validated immutable R2 objects
  and their family completion contracts. GitHub run metadata, scheduler markers,
  and a successful workflow step are not completion evidence.
- Automatic recovery authority after cutover: Cloudflare Durable Object
  coordination. Windows is retained as reversible rollback/manual recovery.
- Cross-scheduler invariant: Cloudflare active mode is forbidden while any
  Windows automatic recovery task or watchdog process is enabled or running.
  This gives at-most-one Cloudflare recovery POST per slot after verified
  mutual exclusion; it does not give provider exactly-once or global
  at-most-one dispatch while native GitHub schedules can overlap.

## PRECHECK — every item must be PASS

1. Recompute Jakarta time and verify the system is outside every relevant slot
   window, with no relevant GitHub run, watchdog process, or provider capture in
   progress. An inability to prove this is a stop.
2. Verify the candidate checkout and provenance:

   ```powershell
   git rev-parse --show-toplevel
   git status --short --branch
   git rev-parse HEAD
   git rev-parse origin/main
   git diff --check origin/main...HEAD
   git diff --name-status origin/main...HEAD
   ```

   Require a clean tree, zero commits behind `origin/main`, the recorded
   candidate SHA, no temporary validator workflow, and a reviewed changed-file
   census. Do not merge or push from this runbook without separate approval.
3. Require exact-head hosted CI for the recorded candidate. Local tests alone
   do not satisfy this gate. The current local candidate has not been pushed, so
   this gate is presently UNKNOWN.
4. Re-run and retain logs for `npm ci`, `npm test`, `npm audit --omit=dev`,
   Python focused tests, full `pytest`, compile/AST checks, YAML/config parsing,
   and all three Wrangler deploy dry-runs. A failed or unavailable check blocks.
5. Verify Cloudflare identity and configuration read-only. Staging-live must be
   `DISPATCH_MODE=observe_only`, expose only the GitHub read capability, and
   have no write credential, Official Open HMAC, or R2 write/delete/list path.
   Production must not be called ready until the Worker, Durable Object, R2
   binding, cron set, and secret names are independently confirmed. Never print
   secret values.
6. Reconcile the candidate archive bucket name with the canonical archive
   authority and the GitHub `R2_BUCKET_NAME` configuration. A matching string in
   source is not live binding proof. Read-only R2 access and archive hashes are
   required for any completion claim.
7. Export the existing Windows task XML and deployment manifest, hash both
   exports, and retain them as rollback evidence. Verify the current task is
   disabled and no V1/V2 watchdog process remains before Cloudflare active mode.
   The live V1 task is currently Ready, so this gate is not met.
8. Provision the Official Open HMAC out of band only after authorization. Keep
   it out of Git, XML, command arguments, logs, checkpoint files, and child
   process environments. Verify only presence and scope, never the value.
9. Verify the GitHub read/write capabilities are separate and that the external
   provider implementation pin is reachable. Missing or unverified provenance
   remains UNKNOWN.

## CUTOVER — authorized maintenance window only

1. Announce the maintenance window and freeze all manual dispatches. Re-check
   the no-active-window and no-in-flight-run preconditions immediately before
   mutation.
2. Export and hash the V1 task definition again. Disable the V1 task and verify
   `State=Disabled`, no new trigger can start, and no watchdog process is alive.
3. The V2 installer currently refuses an existing task (`WATCHDOG_TASK_ALREADY_EXISTS`)
   and does not provide a disabled-registration mode. Do not run it blindly over
   V1. Use an approved task-definition replacement procedure, or register V2
   under a distinct staged name and immediately disable it, then verify the
   canonical automatic-dispatch task set contains no enabled Windows dispatcher.
   Preserve both definitions and hashes.
4. Verify the HMAC is present only in the authorized user environment, and that
   V2 removes signing, provider, and archive secrets before spawning `gh`.
5. Do not activate Cloudflare until the Windows mutual-exclusion check is PASS.
   Activate only the recorded candidate configuration with the exact production
   pins and separate read/write/HMAC capabilities. Do not use Official Open as
   the first active canary.

## REMEDIATED DEPLOYMENT TRANSACTION — V1

The prior incident was a deployment-transaction failure, not a scheduler-logic
failure. `wrangler.production.jsonc` previously declared
`OFFICIAL_OPEN_SCHEDULER_HMAC_KEY` in an unconditional `secrets.required` list.
Wrangler validates that list before upload; it does not evaluate the runtime
`RECOVERY_ALLOWED_SLOTS` branch to decide whether the key is needed. The active
candidate scope was Intraday-only, but the blanket declaration blocked the full
deploy. Later `secret put` operations created versions without proving the
candidate application bytes, which left a stub Worker and no Cron configuration.

The remediation is scope-aware:

- `wrangler.production.jsonc` requires only read/write GitHub credentials for
  `RECOVERY_ALLOWED_SLOTS=["STOCKBIT_INTRADAY_2030"]`.
- `prepareActiveDispatch()` still requires the Official Open HMAC lazily for an
  Official Open slot. An Official Open scope expansion is rejected by the
  readiness checker unless its HMAC declaration is added, and runtime absence
  remains fail-closed.
- `wrangler.production-preparation.jsonc` uses the same Worker name and
  bindings, but is `observe_only` with no recovery scope and no Cron Triggers.
  It is the only configuration allowed for the preparation deployment.
- `scripts/check-deployment-readiness.mjs` verifies scope-aware secret names,
  entrypoint and scheduled handler, non-stub bundle bytes, deterministic hash/
  size, R2/DO bindings, and expected Cron configuration. Its readback mode
  rejects a wrong Worker/version, wrong bytes, missing handler/binding, or empty
  active Cron set.

### Exact next-attempt sequence

1. **Candidate gate.** Merge PR #122 only through the normal review path, then
   record the exact `main` SHA. Recompute the candidate branch SHA from a clean
   checkout and require exact-head hosted CI. Do not use the pre-merge branch
   as production `GITHUB_REF` evidence.
2. **Build/readiness gate.** Run `npm ci`, `npm test`, Python focused/full tests,
   `node --check` for the Worker modules, and both the preparation and production
   readiness checks. Run Wrangler dry-runs with `--outdir` and `--metafile`, then
   run the checker against the emitted bundle. Record config hash, bundle size,
   and bundle SHA-256. Any missing binding, handler, scope, or Cron is a stop.
3. **Preparation.** With Windows still the sole automatic controller, deploy
   only `wrangler.production-preparation.jsonc`. This deployment has no Cron
   Triggers and cannot dispatch. Provision only the separately authorized read
   token by the secure operator channel; never paste its value into a command,
   log, checkpoint, or repository. A secret operation is not deployment proof.
4. **Preparation read-back.** Confirm the same Worker identity, the new version
   ID, compiled bundle hash/size, scheduled handler, `observe_only` mode, empty
   Cron set, `ARCHIVE -> idx-trade-stockbit-stream-v1`, and
   `COORDINATOR -> SchedulerCoordinator`. If any field is UNKNOWN, retain
   Windows and stop.
5. **Active secret readiness.** Only after preparation read-back passes, stage
   the separately authorized write token. The bounded Intraday scope does not
   require the Official Open HMAC. If scope is ever expanded, add and verify
   that HMAC through the same secure channel before the readiness checker can
   pass. Re-run the bundle/readback checks after any secret operation.
6. **Handoff precheck.** Announce a maintenance window outside all due/cutoff
   windows. Freeze manual dispatches. Verify no relevant GitHub run, provider
   capture, or watchdog process is in flight, and export/hash the Windows task
   again. Do not start the task manually.
7. **Single handoff transaction.** Disable Windows and prove `Disabled` plus
   zero watchdog processes. Immediately deploy the recorded
   `wrangler.production.jsonc` active configuration, then perform the complete
   post-deploy read-back before leaving the maintenance window. The active
   read-back must show the exact production scope, five Cron expressions,
   non-stub scheduled bytes, both bindings, and the recorded new version/hash.
   If activation or read-back fails, do not retry the POST/deploy blindly: keep
   Cloudflare inert if possible and restore the last verified Windows task.
8. **Natural canary.** Wait for the next natural
   `STOCKBIT_INTRADAY_2030` recovery opportunity. Do not manually dispatch, retry
   an uncertain POST, call the provider, backfill, or treat a GitHub success or
   Worker version as completion. Require the immutable Intraday R2 completion
   contract, exact run identity, and no forbidden side effects.
9. **Rollback.** On any unknown or failed canary/read-back gate, remove active
   Cloudflare scheduling using the approved inert/previous configuration,
   verify no active Cloudflare recovery remains, re-enable the exported Windows
   task, and preserve all version IDs, hashes, markers, run IDs, and logs. Do not
   mutate counters or repair historical EOD state.

The cross-platform switch has no provider-supported atomic transaction with
Windows Task Scheduler. Therefore the handoff is a bounded maintenance
transaction outside every eligible slot, with the Windows rollback package
already verified before the first mutation. The validator rejects both stable
unsafe states—Windows OFF while Cloudflare is not ready, and Windows ON while
Cloudflare active recovery is ready—and the operator must not leave the
intermediate handoff state unresolved. This preserves controller coverage for
every eligible recovery opportunity without treating a brief, explicitly
bounded maintenance switch as a production canary.

## CLOUDFLARE CANARY — post-close recovery only

Use the bounded `STOCKBIT_INTRADAY_2030` post-close recovery opportunity first.
The 20:30 slot is selected because its 20:40 recovery admission follows the
18:35, 19:05, and 19:35 E2E POST_EOD opportunities. The native GitHub workflow
remains scheduled at 18:30/19:30/20:30; this selection changes only the
Cloudflare active recovery scope. `WAITING_CANONICAL_EOD_GATE` is an explicitly
recoverable intermediate state for the next logical Intraday slot, not a reason
to reclaim the same slot's external dispatch lease.
For the selected slot, retain:

- exact Cloudflare/DO dispatch marker and ownership transition;
- GitHub run ID, event, exact `main` ref, exact run-name slot identity, and
  implementation pin;
- timing against the due/cutoff window and the observed Cloudflare cron time;
- independently read canonical R2 parent/child objects, hashes, identity, and
  completion grain;
- provider-call and false-outcome guards, if independently available; and
- evidence that no second canonical writer or unexpected dispatch occurred.

Any missing item is UNKNOWN and blocks the next family. A GitHub success result
alone is never sufficient. Do not retry an uncertain POST, backfill a missed
session, or use a provider capture merely to make the canary pass.

## ROLLBACK — authorized maintenance window only

1. Stop new Cloudflare automatic scheduling using the recorded prior Worker
   version/configuration. Verify the active schedule is no longer dispatching and
   preserve the Worker/version and request evidence.
2. Re-enable the exported V1 task (or the last verified Windows definition) with
   the explicit rollback command approved during PRECHECK, then verify task state,
   trigger set, executable paths, and no duplicate V2 dispatcher.
3. Preserve all logs, markers, run IDs, archive hashes, and task exports. Do not
   delete or overwrite evidence and do not perform retrospective capture,
   backfill, provider retry, or counter reset.
4. If any correctness-affecting state is UNKNOWN, stop with the rollback state
   preserved and require a new review.

## Acceptance boundary

The runtime is not production-proven until genuine prospective evidence covers
PREOPEN_CA, Official Open, PREOPEN, POST_EOD, and Stockbit Intraday with exact
provenance, implementation pins, timing, immutable archive completion, and no
forbidden side effects. Stream remains
`STREAM_RECOVERY_SEPARATE_BLOCKED` until its independent delayed-schedule and
zero-provider early-completion/idempotence gates are proven.
