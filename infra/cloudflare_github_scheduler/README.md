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
It names a separate Worker, `idx-trade-github-scheduler-v1-staging-observe`,
with an isolated Durable Object namespace and explicit `DISPATCH_MODE=observe_only`.
The baseline staging config explicitly sets `"triggers": { "crons": [] }`.
In that mode the Worker may query GitHub and report `WOULD_DISPATCH`, but the
dispatch POST path is unreachable. A read-only GitHub token is sufficient.

`wrangler.staging-live.jsonc` is a separate, not-deployed observe-only config
with the same five bounded Cron Triggers as production. It exists only for a
future live observe-only proof. Remove all five staging-live crons explicitly
before production crons are deployed: Workers Free allows five Cron Triggers
per account.

`wrangler.production.jsonc` is the explicit activation configuration and must
not be deployed until the existing native-GitHub + Windows-watchdog proof has
been audited. It names `idx-trade-github-scheduler-v1` and explicitly sets
`DISPATCH_MODE=active`.

## Architecture

```text
Cloudflare Cron (independent clock)
  -> Worker due-slot resolver (Asia/Jakarta, actual observed time)
  -> one global SQLite-backed Durable Object
     -> durable per-date/per-slot coordination marker / short dispatch lease
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

The production config uses five UTC Cron Trigger expressions, within the
Cloudflare Free-plan limit:

```text
35,50 1 * * 1-5
0,5,15,22 2 * * 1-5
40 11 * * 1-5
10,40 12 * * 1-5
40 13 * * 1-5
```

Cloudflare Cron runs in UTC. These wake-ups correspond to bounded checks at
08:35/08:50, 09:00/09:05/09:15/09:22, 18:40, 19:10/19:40, and 20:40 WIB.
`dueSlots()` still decides which logical slots need handling at each wake-up;
the Worker never extends the 09:02 CA cutoff or the 09:22 PREOPEN deadline.

Actual `Date.now()` controls admission. `controller.scheduledTime` is evidence
only; a badly delayed Cloudflare invocation cannot use its nominal timestamp to
backfill an expired market window.

## Exact-slot evidence

GitHub workflow-run metadata does not expose the originating cron expression or
`workflow_dispatch` inputs, and native schedule delivery can be delayed by many
hours. The three production workflows therefore expose a deterministic
`run-name` contract containing `IDX-SLOT:<exact_slot_id>`:

- E2E derives the identity from the exact native cron or its optional
  provenance-only `trigger_slot`; a manual dispatch without it is
  `IDX-SLOT:AMBIGUOUS_MANUAL`.
- Official Open derives the identity from its native cron or exact `slot`
  input, and both paths share the same canonical concurrency key.
- Stockbit Intraday derives the identity from its native cron or exact `slot`
  input.

The Worker accepts coverage only when all of these hold:

- the event is `schedule` or `workflow_dispatch`;
- the run is on production `main` (validated from branch/ref metadata);
- `display_title`/run-name contains the exact current `IDX-SLOT:<slot_id>`;
- `created_at` is at or after the logical slot due time, strictly before its
  cutoff, and no later than the observation time.

The timestamp is never used to infer the logical slot. Consequently:

- a delayed morning run cannot cover an evening slot;
- a delayed previous same-workflow slot cannot cover the next slot;
- an exact Windows-watchdog dispatch covers only after it emits the same exact
  slot identity;
- an ambiguous manual run never suppresses Cloudflare fallback.

An unknown or ambiguous run is **not** accepted as exact slot evidence. Exact
coverage is persisted as the generic `covered_exact` coordination marker, with
provenance preserving the real GitHub event: `native_schedule` or
`workflow_dispatch`. It is not capture completion. A visible run, an accepted
dispatch, and an operational block are all non-final scheduler states. Only a
separate validator that reads the existing family archive and verifies its
immutable commit plus hash-bound children may produce `capture_complete`.
A Cloudflare-originated dispatch is additionally identified by the coordinator's
durable marker and the returned workflow run id when GitHub provides one.

Ambiguity fails toward another invocation of the existing idempotent cloud
workflow, never toward silently suppressing a required slot.

## Completion grain

Completion is a property of existing archive evidence, not of a scheduler
marker or GitHub run. The family contracts are:

- E2E: `session + stage/phase`;
- Official Open: `session + exact observation slot`;
- Intraday: `session recovery objective`, retaining slot provenance and
  residual progress;
- Stream: `exact observation slot + universe/source identity`, but Stream is
  not admitted to this Cloudflare scheduler until its identity/indexing and
  zero-provider completion path are independently proven.

The Cloudflare package defines contract validators for the admitted E2E,
PREOPEN_CA checkpoint, Official Open, and Intraday archive records. The
PREOPEN_CA validator is intentionally separate from the normal E2E stage-commit
schema. An archive-reading caller must supply bytes/hashes obtained from the
existing authority; the Worker does not gain an R2 binding or a parallel
archive authority in this phase. The Stream grain is documented for the
cross-family contract and is intentionally not a Cloudflare trigger path.

## Failure semantics

- GitHub run-query error -> fail closed; no dispatch.
- Native exact schedule or exact watchdog dispatch -> non-final `covered_exact`
  marker with `native_schedule` or `workflow_dispatch` provenance. A recent
  in-flight run may receive a short grace period; terminal success, failure, or
  cancellation without validated archive completion remains recovery-eligible.
- Missing native run in `observe_only` -> non-final `would_dispatch` marker and
  `WOULD_DISPATCH` result; no dispatch POST.
- Missing native run in `active` -> durable short `dispatching` lease, then
  dispatch.
- Successful dispatch -> non-final `dispatch_requested` marker; the workflow
  must produce independently validated archive completion.
- Retryable GitHub error (408/409/429/5xx) -> retryable marker; a later cron may
  re-query and retry while the slot is still valid.
- Non-retryable GitHub error -> non-final `blocked` marker; recovery remains
  eligible while the semantic window is still valid.
- Expired market window -> no dispatch, no backfill.
- Missing or invalid `DISPATCH_MODE` -> fail closed; never defaults to active.

The Intraday GitHub workflow has a provider-free preflight that validates the
existing canonical archive before Python setup, accepted-E2E checkout, package
installation, or provider access. A validated complete archive skips the
capture job with zero provider calls. Missing completion continues to the
existing runner; malformed or conflicting archive evidence fails closed.

Intraday stale-claim recovery remains blocked when the create-only claim store
cannot prove a fence against a still-running old provider writer. Residual
progress is preserved, but takeover is not inferred to be safe. Stream remains
outside Cloudflare redundancy because its archive identity depends on its
universe/source hashes and its current runner has no proven zero-provider
completion gate.

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
