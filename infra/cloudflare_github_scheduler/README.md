# IDX-Trade Cloudflare → GitHub Scheduler Redundancy V1

Trigger-only redundancy for IDX-Trade production GitHub Actions workflows.

## Safety boundary

This Worker is **not** a market-data collector. It has no Zapi, IDX, Stockbit,
R2, PaperState, scoring, order/fill, counter, target, or outcome credentials or
code paths. Its only external authority is GitHub Actions metadata +
`workflow_dispatch`.

The production capture implementations remain the existing GitHub workflows on
`main`.

## Current activation status

`wrangler.jsonc` intentionally contains **no Cron Trigger**. Building or staging
this Worker must not change the 2026-08-27 18:30–20:40 prospective proof.

`wrangler.production.jsonc` is the explicit activation configuration and must
not be deployed until the existing native-GitHub + Windows-watchdog proof has
been audited.

## Architecture

```text
Cloudflare Cron (independent clock)
  -> Worker due-slot resolver (Asia/Jakarta, actual observed time)
  -> one global SQLite-backed Durable Object
     -> durable per-date/per-slot marker / short dispatch lease
     -> query exact native GitHub schedule evidence
     -> if absent, workflow_dispatch existing workflow on main

GitHub Actions
  -> existing production runtime
  -> existing provider/R2/PaperState/idempotency contracts
```

The Durable Object is used because the slot marker is coordination state and
must be strongly consistent. Workers KV is intentionally not used for this
contract.

## Covered workflows

V1 contains bounded redundancy for:

- E2E PREOPEN_CA
- Official Open
- E2E PREOPEN
- E2E POST_EOD
- Stockbit Intraday

**Stockbit Stream is intentionally excluded.** The current Stream runner can
perform a Zapi stock-summary universe request before it reaches its manifest
idempotency gate. Stream must gain a zero-provider early completion gate before
it is admitted to redundant triggering.

## Trigger model

The production config uses one UTC Cron Trigger:

```text
*/5 1-15 * * 1-5
```

Cloudflare Cron runs in UTC. This polls every five minutes from 08:00 through
22:55 WIB on weekdays, but the Worker calls GitHub only while a bounded slot
window is actually due. The broad cron is intentionally separated from the
market deadlines encoded in `src/core.mjs`.

Actual `Date.now()` controls admission. `controller.scheduledTime` is evidence
only; a badly delayed Cloudflare invocation cannot use its nominal timestamp to
backfill an expired market window.

## Exact-slot evidence

GitHub workflow-run metadata does not expose the originating cron expression or
`workflow_dispatch` inputs. Therefore:

- a native `event=schedule` run is accepted only inside the exact interval for
  the current slot;
- the next same-workflow slot is a hard ambiguity boundary;
- an unknown `workflow_dispatch` run is **not** accepted as exact slot evidence;
- a Cloudflare-originated dispatch is identified by the coordinator's durable
  marker and the returned workflow run id when GitHub provides one.

Ambiguity fails toward another invocation of the existing idempotent cloud
workflow, never toward silently suppressing a required slot.

## Failure semantics

- GitHub run-query error -> fail closed; no dispatch.
- Native exact schedule run -> durable `covered_native` marker; no dispatch.
- Missing native run -> durable short `dispatching` lease, then dispatch.
- Successful dispatch -> durable `dispatched` marker.
- Retryable GitHub error (408/409/429/5xx) -> retryable marker; a later cron may
  re-query and retry while the slot is still valid.
- Non-retryable GitHub error -> durable `blocked` marker; no repeated calls.
- Expired market window -> no dispatch, no backfill.

## GitHub credential

The only secret is `GITHUB_ACTIONS_TOKEN`.

Use a fine-grained credential scoped to **only** `samindriano/idx-trade` with
GitHub repository permission **Actions: write** and an expiry/rotation policy.
Do not put the value in Wrangler vars, git, logs, CLI arguments, or test
fixtures. Configure it as a Cloudflare Worker secret.

## Local validation

```bash
npm test
node --check src/index.js
node --check src/core.mjs
node --check src/github.mjs
```

Wrangler is pinned in `package.json`. When a Wrangler-capable environment is
available, additionally run a no-deploy validation against `wrangler.jsonc`.

## Activation gate

Do not activate production Cron until all of these are true:

1. 2026-08-27 post-close native/Windows fallback proof is audited.
2. `npm test` passes from a clean checkout.
3. Wrangler config/dry-run validation passes.
4. Cloudflare secret exists with least privilege and no provider credentials.
5. A provider-free GitHub diagnostic proves the Worker can query + dispatch a
   synthetic/read-only workflow.
6. Windows watchdog is not retired until one genuine Cloudflare-covered future
   slot is proven.
7. Stockbit Stream remains excluded until its early zero-provider dedupe gate
   is implemented and tested.
