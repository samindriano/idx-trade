# Cloudflare GitHub Scheduler Redundancy V1 — Build Checkpoint

Date: 2026-08-27 Asia/Jakarta
Branch: `ops/cloudflare-github-scheduler-redundancy-v1`
Base: `main@f6b032350ac5a10feac7c1e093b523a4f91261f9`
Status: `IMPLEMENTATION_BUILT_NOT_PRODUCTION_ACTIVATED`

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
- exact same-workflow ambiguity boundaries;
- GitHub native-schedule query with fail-closed errors;
- exact `workflow_dispatch` input mapping;
- one SQLite-backed Durable Object for strongly consistent per-slot markers;
- short durable dispatch lease for duplicate Cloudflare invocations;
- actual observed time controls cutoff admission;
- production activation separated into `wrangler.production.jsonc`;
- one five-minute UTC cron is sufficient; most invocations are local no-ops.

## Security

Required Worker secret: `GITHUB_ACTIONS_TOKEN` only.

No Zapi, IDX, Stockbit, R2, HMAC, PaperState, execution, target, or outcome
secret is accepted by the Worker configuration.

## Validation completed in implementation environment

- Node: 22.16.0
- `npm test`: 14/14 PASS
- schedule tests include late-slot ambiguity, morning cutoff, native-only
  coverage, unknown workflow_dispatch ambiguity, GitHub query fail-closed, exact
  dispatch inputs, retryable/non-retryable GitHub responses, and explicit
  Stockbit Stream exclusion.
- dependency installation / Wrangler dry-run was attempted but the current
  execution environment timed out before installing `node_modules`; therefore
  **Wrangler runtime validation remains pending and is not claimed**.

## Next gate

After the 2026-08-27 18:30–20:40 proof:

1. audit actual native + Windows-watchdog evidence;
2. run clean npm/Wrangler validation in the user's local repo environment;
3. perform a provider-free Cloudflare -> GitHub diagnostic;
4. only then activate `wrangler.production.jsonc`;
5. retain Windows fallback until one genuine future Cloudflare-covered slot is
   observed;
6. separately harden Stockbit Stream early dedupe before admitting it.
