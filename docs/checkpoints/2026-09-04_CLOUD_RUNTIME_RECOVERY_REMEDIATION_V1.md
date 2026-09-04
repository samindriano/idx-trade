# Cloud Runtime Recovery Remediation V1

Date: 2026-09-04 Asia/Jakarta
Branch: `remediation/main-cloud-runtime-recovery-v1`
Reviewed starting head: `7e6e14e3949d7f2589048dd46acb156457211bb1`
Current main comparison: `origin/main@9b070894535c0c0fc13bc441f004f5d0a8039cb9`

## Scope and safety boundary

This is a bounded correctness remediation for PR #121. Production remains
**NO-GO**. No workflow was dispatched manually; no provider, Cloudflare,
Windows Task Scheduler, secret, token, archive, R2, counter, outcome,
PaperState, or science state was accessed or mutated.

## Corrected contracts

- Preparation failures remain explicitly reacquirable only after the local
  path proves that no GitHub POST could begin.
- Every HTTP response after the POST boundary is fenced. `5xx`, `409`, `429`,
  and ordinary `4xx` responses are not treated as proof of zero side effect;
  historical `retryable_error`/`blocked` markers are also non-reclaimable.
- A known local rejection before `fetch`, including an expired dispatch window,
  is marked `post_attempted: false` and remains safely reacquirable. A rejected
  `fetch` remains POST-uncertain and keeps its fence.
- After active dispatch preparation and signing, the coordinator revalidates
  the existing canonical archive authority immediately before dispatch. A
  durable completion appearing while the owner was suspended prevents POST;
  ownership is checked again after that awaited validation to prevent an old
  owner overwriting a newer attempt.
- E2E durable completion now compares the canonical parent `code_identity`
  commit with the exact configured expected implementation pin. Missing or
  malformed identity remains fail-closed.
- Archive-writing E2E and Official Open jobs now require the production
  `refs/heads/main` ref; pinned code identity alone is not treated as a branch
  boundary. Schedules and producer pins are unchanged.

## Composition boundary

The Foreign Flow coordination row and the Actions Cost Optimization
measurement checkpoint match current `origin/main`; neither was rewritten as
part of this remediation. The pre-existing same-job Intraday completion
preflight remains a separate Phase-2 behavior and is not claimed here as new
cost evidence or as measured production savings.

## Official Open audit disposition

The reported native-versus-trusted-dispatch incompatibility was **disproven**
against the pinned E2E implementation `8bc3ee3efd65e8b16478e404e4b226451b105c48`.
Its `e2e_official_open_admission_v2.py` already admits native `schedule` and
producer-verified `workflow_dispatch` through distinct authorities, while
rejecting ordinary/manual dispatch and preserving exact slot, timing, producer
pin, and manifest/hash checks. The scheduler admission tests now cover the
narrow schema, slot, timing, and hash rejection cases; no event name was
rewritten and no new runtime layer was added.

## Remaining blockers

This remediation does not claim to solve Windows/Cloudflare cross-scheduler
exactly-once, native/recovery provider fencing, Intraday stale-claim liveness,
provider idempotency, the 2026-09-03 incident, operational credentials, or
genuine-session activation evidence. Stream remains outside Cloudflare
redundancy.
