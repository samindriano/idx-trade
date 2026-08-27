# Cloudflare GitHub Scheduler Redundancy V1 — Build Checkpoint

Date: 2026-08-27 Asia/Jakarta
Branch: `ops/cloudflare-github-scheduler-redundancy-v1`
Base: `main@5170314b574fc280f161cafff39ad03262daa06c`
Status: `IMPLEMENTATION_HARDENED_NOT_PRODUCTION_ACTIVATED`

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
- exact run-name/branch/ref/event coverage validation; `created_at` is only a
  bounded current-date search filter;
- GitHub run query with fail-closed errors;
- exact `workflow_dispatch` input mapping;
- one SQLite-backed Durable Object for strongly consistent per-slot markers;
- short durable dispatch lease for duplicate Cloudflare invocations;
- actual observed time controls cutoff admission;
- production activation separated into `wrangler.production.jsonc`;
- five exact UTC cron expressions stay within the Cloudflare Free-plan limit;
  `dueSlots()` decides which logical slots are handled at each wake-up.

## Security

Required Worker secret: `GITHUB_ACTIONS_TOKEN` only.

No Zapi, IDX, Stockbit, R2, HMAC, PaperState, execution, target, or outcome
secret is accepted by the Worker configuration.

## Validation completed in implementation environment

- Node: 26.0.0
- `npm ci`: BLOCKED because this lane has no package-lock or npm-shrinkwrap;
  `npm install --no-package-lock` completed successfully with 0 vulnerabilities.
- `npm test`: 24/24 PASS
- schedule tests include exact run-name coverage, delayed-slot rejection,
  exact watchdog dispatch coverage, branch/ref filtering, morning and 09:22
  deadlines, native/dispatch contracts, GitHub query fail-closed, exact
  dispatch inputs, retryable/non-retryable GitHub responses, durable marker
  suppression, and explicit Stockbit Stream exclusion.
- `npx wrangler types --config wrangler.production.jsonc`: PASS.
- `npx wrangler types --config wrangler.jsonc`: PASS.
- `npx wrangler deploy --dry-run --config wrangler.production.jsonc`: PASS;
  Wrangler 4.127.0, 15.73 KiB upload / 4.63 KiB gzip; no deployment occurred.
- focused watchdog tests: 21/21 PASS with a fresh explicit Windows pytest
  temp root; full repository pytest: PASS.
- PyYAML syntax parse: 12 workflow/config files PASS; `actionlint` and
  `yamllint` are unavailable in this environment. `git diff --check`: PASS.

## Next gate

Before any provider-free staging/diagnostic deployment:

1. review this rebased/hardened lane and its exact-slot evidence;
2. separately update the temporary local Windows watchdog to send E2E
   `trigger_slot`; its current script still sends only `phase`;
3. provide/configure the staging GitHub Actions token and explicitly authorize
   the provider-free diagnostic;
4. retain Windows fallback until one genuine future Cloudflare-covered slot is
   observed;
5. separately harden Stockbit Stream early dedupe before admitting it.
