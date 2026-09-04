# IDX-Trade Cloudflare → GitHub Scheduler Redundancy V1

Trigger-only redundancy for the existing IDX-Trade production GitHub Actions workflows.

## Safety boundary

This Worker is **not** a market-data collector. It has no Zapi, IDX, Stockbit,
PaperState, scoring, order/fill, counter, target, or outcome credentials or code
paths. The archive adapter performs known-key R2 `get()` calls only; it never
calls write, delete, or list and never becomes a second archive authority.

That is an application-code read-only boundary, **not** a claim that a normal
Cloudflare R2 binding is IAM-enforced read-only. Production capture remains in
the existing GitHub workflows on `main`. GitHub run metadata remains provenance
and coordination evidence only.

## Current activation status

`wrangler.jsonc` is isolated staging with `DISPATCH_MODE=observe_only` and no
Cron Trigger. `wrangler.staging-live.jsonc` is a separate observe-only config
with the five bounded production-equivalent wake-up expressions for a future
shadow proof. Neither observe-only config carries a GitHub workflow-dispatch
credential or the Official Open signing key; both require only
`GITHUB_ACTIONS_READ_TOKEN`.

`wrangler.production.jsonc` is the explicit active configuration and remains
undeployed. It requires separate read and write GitHub credentials plus the
Official Open HMAC signing key. The write credential is accessed lazily only
inside the active dispatch function.

No config here authorizes production deployment by itself.

## Architecture

```text
Cloudflare Cron (independent clock)
  -> due-slot resolver using actual Asia/Jakarta observation time
  -> one SQLite-backed Durable Object
     -> per-date/per-slot coordination marker and short dispatch lease
     -> known-key read of canonical archive parent/children
     -> exact GitHub run discovery with pagination
     -> archive completion + family-specific recovery admission
     -> observe-only WOULD_DISPATCH, or active existing-workflow dispatch

GitHub Actions
  -> existing pinned production runtime
  -> existing provider / immutable R2 / PaperState contracts
```

The Durable Object coordinates scheduler attempts. It is never capture-final.
Only validated canonical archive bytes may establish completion.

## Covered workflows

Bounded redundancy covers:

- E2E PREOPEN_CA
- Official Open
- E2E PREOPEN
- E2E POST_EOD
- Stockbit Intraday

**Stockbit Stream is intentionally excluded.** Its current runtime has not yet
proved the required zero-provider early completion gate for redundant triggering.

## Trigger model

Production uses five UTC Cron expressions:

```text
35,50 1 * * 1-5
0,5,15,22 2 * * 1-5
40 11 * * 1-5
10,40 12 * * 1-5
40 13 * * 1-5
```

They wake the Worker at bounded checks around 08:35/08:50,
09:00/09:05/09:15/09:22, 18:40, 19:10/19:40, and 20:40 WIB. `dueSlots()` decides
which logical slots are valid at each wake-up. Actual `Date.now()` controls
admission; `controller.scheduledTime` is evidence only. A delayed Cloudflare
invocation cannot use its nominal timestamp to backfill an expired market
window.

## Exact-slot GitHub evidence

The production workflows expose deterministic `IDX-SLOT:<slot_id>` run names.
E2E binds manual recovery to an explicit phase-compatible `trigger_slot`;
Official Open and Intraday bind to their exact `slot` input. Ambiguous manual
runs do not suppress recovery.

Exact GitHub evidence requires all of the following:

- event `schedule` or `workflow_dispatch`;
- production `main` branch/ref;
- exact current `IDX-SLOT:<slot_id>` identity;
- `created_at` inside that slot's due/cutoff observation interval.

Run discovery follows GitHub pagination. It fails closed rather than silently
truncating after the configured 20-page safety bound.

A visible run, accepted dispatch, or coordinator marker is never capture
completion. The output keeps GitHub provenance, archive validation, and the
final effective scheduler decision separate.

## Recovery concurrency

GitHub workflow concurrency is **not** the exactly-once authority for E2E or
Official Open recovery. A shared concurrency group can queue a later recovery
behind a hung earlier run until the prospective window has expired. The
integration wrapper therefore keeps E2E retry attempts and Official Open
native/trusted-recovery attempts independently runnable.

Correctness is instead enforced by the existing conditional immutable archive
commit:

- Official Open: deterministic `slot_manifest.json` is create-only;
- E2E: deterministic stage/checkpoint commit is create-only;
- a same-key conflicting contender cannot overwrite the winner and fails closed.

A rare overlapping attempt may perform redundant work before the immutable
winner exists, but it cannot replace canonical durable state. Intraday retains
its separately reviewed same-session provider fencing and is not changed by
this topology rule.

## Completion and recovery admission

Completion grain is:

- E2E: session + stage/phase;
- PREOPEN_CA: session + checkpoint;
- Official Open: session + exact observation slot;
- Intraday: same-session recovery objective retaining slot provenance/progress;
- Stream: excluded from this scheduler.

The archive validators hash the raw canonical parent bytes and validate their
semantic identity and hash-bound children. Missing parents are incomplete;
malformed/conflicting evidence blocks fail closed.

Official Open has an additional recovery-admission layer. Structural existence
of an immutable slot manifest is insufficient to suppress retry. The manifest
must also prove the exact accepted producer pin, prospective timing, and either:

- native GitHub schedule authority; or
- producer-verified trusted external HMAC scheduler authority.

The accepted producer itself validates runner authority and runner-start timing
before store construction/provider access, validates source capture timing
before immutable archive writes, and rejects late or untrusted attempts before
they can occupy a new slot.

## Failure semantics

- GitHub run-query error -> fail closed; no dispatch.
- Validated archive completion -> suppress recovery.
- Coordinator `dispatching`/`dispatch_requested` short lease -> defer duplicate
  coordinator request; lease is not completion.
- Fresh in-flight GitHub run -> short defer for normal families only.
- **Official Open exception:** in-flight GitHub metadata cannot consume its sole
  narrow recovery opportunity. Without validated durable completion, an active
  scheduler remains recovery-eligible.
- `observe_only` recovery candidate -> `WOULD_DISPATCH`; dispatch function is
  not invoked.
- Active recovery candidate -> take short coordinator lease and invoke the
  existing workflow.
- Successful dispatch -> non-final `dispatch_requested`; workflow output still
  must become independently validated archive completion.
- Any HTTP response after the POST boundary -> fenced non-final response marker;
  status codes do not prove that GitHub did not accept the request, so no
  automatic reclaim is permitted.
- Pre-request preparation failure -> explicitly reacquirable
  `pre_dispatch_blocked` marker only after zero POST is proven.
- Expired market window -> no dispatch and no backfill.
- Missing/invalid `DISPATCH_MODE` -> fail closed; never defaults to active.

Intraday `WAITING_CANONICAL_EOD_GATE` and `WAITING_RECOVERY_RETRY` are validated
recoverable intermediate states, not completion. Stale-claim takeover remains
blocked unless fencing can prove a prior provider writer is no longer active.

## GitHub credential capability split

There is no generic `GITHUB_ACTIONS_TOKEN` contract.

`GITHUB_ACTIONS_READ_TOKEN` is used for workflow-run discovery in every mode.
For staging and staging-live it must be a dedicated fine-grained credential
restricted to `samindriano/idx-trade` with **Actions: read** and no workflow
write capability.

`GITHUB_ACTIONS_WRITE_TOKEN` exists only in the production active config and is
read lazily inside the dispatch function. It must be separately scoped to the
same repository with the minimum GitHub permission needed for workflow
dispatch. Do not reuse the write credential as the staging read credential.

`OFFICIAL_OPEN_SCHEDULER_HMAC_KEY` exists only in active production dispatch
plumbing. Its value must never be committed, pasted into documentation, emitted
in logs, or passed as a workflow input. Only the derived signature/nonce fields
are sent to Official Open recovery.

## Validation

Local/static validation:

```bash
npm test
node --check src/index.js
node --check src/core.mjs
node --check src/github.mjs
npx wrangler deploy --dry-run --config wrangler.staging-live.jsonc
npx wrangler deploy --dry-run --config wrangler.production.jsonc
```

Dry-run is validation only; it is not deployment.

## Activation gate

Production activation remains blocked until all of these are independently
proven:

1. final branch tests and both Wrangler dry-runs are green;
2. staging-live is deployed **observe-only only** with the dedicated
   `GITHUB_ACTIONS_READ_TOKEN`;
3. the staging credential's declared GitHub permission is Actions read-only and
   a safe authenticated GET proves workflow-run metadata access;
4. staging shadow produces zero workflow dispatches and zero R2 write/delete/list
   operations across representative morning and post-close observations;
5. production `GITHUB_ACTIONS_WRITE_TOKEN` and the shared Official Open HMAC key
   are provisioned separately only when active activation is authorized;
6. production config is not deployed merely because staging shadow is green;
7. Windows watchdog is retained until a genuine Cloudflare-covered future slot
   is proven;
8. Stockbit Stream remains excluded.

Do not perform a negative workflow-dispatch POST merely to test that the
staging token cannot write. Permission declaration plus safe read behavior is
the non-mutating proof path.
