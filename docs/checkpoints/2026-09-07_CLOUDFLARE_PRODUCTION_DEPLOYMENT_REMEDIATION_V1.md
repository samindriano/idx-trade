# Cloudflare Production Deployment Remediation V1

Status: local candidate ready for review; production remains inert. Prepared
2026-09-07 (Asia/Jakarta) on `codex/cloud-runtime-recovery-integration-v1`.

## Verdict

`CLOUDFLARE_DEPLOYMENT_REMEDIATION_READY_FOR_REVIEW`

This checkpoint records only repository/configuration/test work. No Cloudflare
production deploy, secret mutation, Cron mutation, Windows task mutation, GitHub
workflow dispatch, provider call, R2 write, merge, or outcome access was
performed for this remediation.

## Root cause

The accepted production config declared these names unconditionally in
`secrets.required`:

```text
GITHUB_ACTIONS_READ_TOKEN
GITHUB_ACTIONS_WRITE_TOKEN
OFFICIAL_OPEN_SCHEDULER_HMAC_KEY
```

Wrangler treats that list as a Worker-wide deployment prerequisite and checks it
before uploading the application. It does not evaluate the runtime
`RECOVERY_ALLOWED_SLOTS` branch. The active candidate was bounded to
`["STOCKBIT_INTRADAY_2030"]`, and the runtime reads the Official Open HMAC only
inside `prepareActiveDispatch()` when `isOfficialOpenSlot(slot)` is true. The
HMAC therefore blocked deployment at the deployment layer even though it was
not needed by the selected Intraday canary.

The later `wrangler secret put` operations were not equivalent to an application
deployment. With no accepted application upload proven, those operations could
create a Worker/version containing only `export default { fetch() {} }`. Because
the failed full deploy never installed the candidate trigger configuration, the
production Cron set remained empty. Worker existence, secret existence, and a
new version ID are not bundle or readiness evidence.

## Remediation

- `wrangler.production.jsonc` now declares only the read/write GitHub
  credentials for the exact bounded Intraday scope.
- Runtime security is retained: Official Open preparation still requires
  `OFFICIAL_OPEN_SCHEDULER_HMAC_KEY` lazily, and missing HMAC fails closed before
  any POST. Expanding active scope to Official Open requires the HMAC declaration
  to be added; the readiness checker rejects a mismatch.
- `wrangler.production-preparation.jsonc` uses the same Worker/bindings in
  `observe_only` mode with no `RECOVERY_ALLOWED_SLOTS` and no Cron Triggers. It
  is the safe preparation configuration while Windows remains the automatic
  controller.
- `src/deployment_readiness.mjs` and
  `scripts/check-deployment-readiness.mjs` provide pure/static checks for:
  scope-aware secret declarations, exact entrypoint, non-stub scheduled bundle,
  deterministic bundle hash/size, R2/DO bindings, vars/scope, Cron set, and a
  normalized post-deploy read-back. The read-back rejects wrong Worker/version,
  wrong bytes, missing handlers/bindings, and empty active Cron configuration.
- `validateControllerState()` rejects both Windows OFF + Cloudflare not ready
  and Windows ON + Cloudflare active recovery, as well as a stable state with no
  automatic controller. Existing lazy HMAC and active-scope runtime fencing are
  unchanged.

## Preparation → activation state machine

| State | Automatic owner | Required evidence |
|---|---|---|
| `WINDOWS_PRIMARY` | Windows | Windows task enabled/quiescent when outside a slot; Cloudflare preparation config is observe-only/no-Cron. |
| `CLOUDFLARE_STAGED` | Windows | Preparation Worker, compiled bytes/hash, bindings, vars, and no-Cron read-back all match. |
| `HANDOFF_READY` | Windows | Exact merged `main` SHA, readiness checks, separate credentials, no in-flight/uncertain dispatch, and verified rollback package. |
| `CLOUDFLARE_ACTIVE_CANARY` | Cloudflare | Outside all slot windows, Windows disabled with zero watchdog processes, active config read-back matches exact scope/five Crons/bundle/bindings. |
| `CLOUDFLARE_PROVEN` | Cloudflare | Natural `STOCKBIT_INTRADAY_2030` canary has exact run identity and immutable R2 completion with no forbidden side effects. |
| `ROLLBACK_READY` | Windows | Cloudflare active scheduling is inert/removed, last verified task export is restored, and all evidence is preserved. |
| `POST_UNCERTAIN_FENCED` | No automatic reclaim | Any uncertain GitHub POST remains fenced; neither scheduler may retry or reclaim it automatically. |

The Windows/Cloudflare cross-platform switch has no provider-supported atomic
transaction. The runbook therefore permits only a bounded maintenance handoff
outside every eligible slot, with the rollback package verified first and an
immediate restore on any activation/read-back failure. The validator rejects
unsafe stable states; the maintenance interval is not a canary and must never
be left unresolved. This is the residual operational constraint before any
production attempt, not evidence of a production cutover.

## Validation evidence

At candidate HEAD `3125246c5db905adb73ca4e0ef02f18255492c74`:

- Cloudflare Node suite: **104/104 passed**.
- Full Python suite with the checkout on `PYTHONPATH`: **406 passed**, with the
  existing three `FutureWarning` messages from `stockbit_intraday_eod_gate.py`.
- Raw `pytest -q` without the checkout import path failed collection because the
  shell resolved `scripts`/`tests` as namespaces; this was an environment
  invocation issue, not a test assertion failure. The corrected repository
  invocation passed.
- `npm ci`: passed; audit reported 0 vulnerabilities.
- `node --check`: Worker entrypoint, core, GitHub client, readiness module, and
  readiness CLI passed.
- Wrangler `types`: baseline, staging-live, preparation, and production configs
  generated successfully. Wrangler printed its existing recommendation to
  install `@types/node`; no generated file is part of the candidate.
- Wrangler dry-run: staging-live, preparation, and production all passed with
  Wrangler `4.127.0`; no upload occurred.
- Production compiled bundle: **94,520 bytes**, SHA-256
  `f83fce1e9cf7683b5760f58c53e6b151e126270266e1f2425c60d75f221fe018`.
  It contains the scheduled handler and expected R2/DO references and is not the
  prior stub.
- Production config SHA-256:
  `ff677345605e10f2991b5f2fe20efd8e63fccf47bf18023accddab7c72db4fe7`.
- Preparation config SHA-256:
  `e463df0a8c5ea025f972edc0501a3e0638641072aa3737373d4792f74fffa1ce`.

## Lineage and blockers

PR #122 remains the cleanest review vehicle: open, draft, mergeable, and based
on `codex/cloud-runtime-recovery-integration-v1`. No successor branch was
created. The worktree contained a pre-existing uncommitted change to the
2026-09-07 canary authorization packet; it was preserved and is not silently
included in this remediation. No push or merge was performed during this run.

Before a production attempt, reviewers must still verify the merged `main` SHA,
production credentials/binding authorization, post-deploy read-back, the
maintenance-window handoff, and a genuine natural canary. Production remains
blocked until those external facts are proven; the local remediation is ready
for review only.
