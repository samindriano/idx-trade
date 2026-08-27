# Cloudflare GitHub Scheduler Redundancy V1 — Build Checkpoint

Date: 2026-08-28 Asia/Jakarta (remediation update)
Branch: `ops/cloudflare-github-scheduler-redundancy-v1`
Base: `main@acd448c9d554bbb9e37254e4d45b61f03cf59e5b`
Status: `PREPARED_FOR_INDEPENDENT_REVIEW_NOT_PRODUCTION_ACTIVATED`
Watchdog compatibility head: `ops/github-schedule-watchdog-v1@82f938e9`

## Incident basis

On 2026-08-27, native GitHub `schedule` delivery was absent for the repository's
morning production workflows and for all three Stockbit Stream canaries
08:47/12:07/16:47 WIB. A provider-free `workflow_dispatch` diagnostic succeeded,
separating Actions execution from native schedule-event delivery.

This lane builds an independent cloud clock without creating a second capture
runtime.

## Boundaries

- no production Cloudflare Cron deployment before the 18:30–20:40 proof;
- no change to `main` while that proof is pending;
- no provider/R2/PaperState/outcome credentials in Cloudflare;
- no Stockbit Stream redundancy in V1;
- no retroactive market-stage dispatch;
- no model/science changes.

`coordination/TEAM_STATUS.md` was read before branch creation. The canonical
coordination file is intentionally not edited yet because even a coordination
commit would move default-branch HEAD immediately before the scheduled proof.

## Implementation

- pure Jakarta slot/cutoff resolver;
- exact five-expression bounded Cloudflare cron schedule;
- deterministic `IDX-SLOT:<slot_id>` run-name contracts on E2E, Official Open,
  and Stockbit Intraday workflows;
- E2E provenance-only `trigger_slot` validation and dispatch propagation;
- Official Open native/dispatch same-slot concurrency identity;
- exact run-name/branch/ref/event coverage validation; `created_at` admits only
  runs at or after the logical slot due time, before its cutoff, and no later
  than observation time; it never supplies logical slot identity;
- GitHub run query with fail-closed errors;
- exact `workflow_dispatch` input mapping;
- one SQLite-backed Durable Object for strongly consistent per-slot markers;
- short durable dispatch lease for duplicate Cloudflare invocations;
- actual observed time controls cutoff admission;
- staging `observe_only` mode with no dispatch POST path and `WOULD_DISPATCH`
  results;
- distinct staging/production Worker names, therefore isolated Durable Object
  namespaces;
- explicit baseline staging `"triggers": { "crons": [] }` plus a separate,
  not-deployed five-cron `wrangler.staging-live.jsonc` observe-only config;
- explicit production `active` mode; missing or invalid mode fails closed;
- reproducible pinned `package-lock.json` and production activation separated
  into `wrangler.production.jsonc`;
- five exact UTC cron expressions stay within the Cloudflare Free-plan limit;
  `dueSlots()` decides which logical slots are handled at each wake-up.
- exact coverage persists generic `covered_exact` markers and preserves the
  real GitHub event as `native_schedule` or `workflow_dispatch` provenance.

## Security

Required Worker secret: `GITHUB_ACTIONS_TOKEN` only.

No Zapi, IDX, Stockbit, R2, HMAC, PaperState, execution, target, or outcome
secret is accepted by the Worker configuration.

## Validation completed in implementation environment

- Node: 26.0.0
- `npm ci`: PASS; 37 packages added, 0 vulnerabilities.
- `npm test`: 35/35 PASS.
- schedule tests include exact run-name coverage, delayed-slot rejection,
  exact watchdog dispatch coverage, branch/ref filtering, morning and 09:22
  deadlines, native/dispatch contracts, GitHub query fail-closed, exact
  dispatch inputs, retryable/non-retryable GitHub responses, durable marker
  suppression, and explicit Stockbit Stream exclusion.
- `npx wrangler types --config wrangler.jsonc`: PASS.
- `npx wrangler types --config wrangler.staging-live.jsonc`: PASS.
- `npx wrangler types --config wrangler.production.jsonc`: PASS.
- `npx wrangler deploy --dry-run --config wrangler.jsonc`: PASS; Wrangler
  4.127.0, observe-only binding visible, no deployment occurred.
- `npx wrangler deploy --dry-run --config wrangler.staging-live.jsonc`: PASS;
  Wrangler 4.127.0, observe-only binding and five bounded Cron expressions
  visible, no deployment occurred.
- `npx wrangler deploy --dry-run --config wrangler.production.jsonc`: PASS;
  Wrangler 4.127.0, active binding and five Cron expressions visible, no
  deployment occurred.
- focused watchdog tests: 29/29 PASS; related E2E activation/synthetic tests:
  19/19 PASS; full repository pytest: 349/349 PASS.
- PyYAML syntax parse: 10 workflow files plus 3 Wrangler configs PASS;
  `actionlint` and `yamllint` are unavailable in this environment.
- Node syntax/import checks and `git diff --check`: PASS.
- watchdog cross-contract test parses the E2E workflow's actual schedule and
  trigger-slot allow-lists and matches all nine watchdog E2E slot IDs; the
  final 09:22 slots expire at 09:23 and the installer no longer contains 09:26.

## Next gate

Before any provider-free staging/diagnostic deployment:

1. independently review this remediated lane and the watchdog
   compatibility branch;
2. provide/configure the staging GitHub Actions token and explicitly authorize
   the provider-free diagnostic; no token has been configured here;
3. retain Windows fallback until one genuine future Cloudflare-covered slot is
   observed;
4. separately harden Stockbit Stream early dedupe before admitting it.
