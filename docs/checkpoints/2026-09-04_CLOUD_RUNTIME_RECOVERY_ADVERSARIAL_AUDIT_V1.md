# Cloud Runtime Recovery Adversarial Audit V1

Date: 2026-09-04 Asia/Jakarta  
Audit checkout: `remediation/main-cloud-runtime-recovery-v1`  
Source under audit: PR #120, `ops/cloud-runtime-recovery-cutover-v1@c397c08aadc48adee53f635752ca38704c4c370b`  
Main comparison: `origin/main@00e6640578d70bfc3bf84d083838edbefb30708b`

## Status

This is a bounded code-level remediation candidate for independent review.
Operational activation remains **NO-GO**. No production scheduler, provider,
archive, Cloudflare resource, Windows task, secret, token, counter, outcome,
PaperState, or science state was changed.

## Current architecture reconstructed from the checkout

- GitHub Actions native schedules are the primary trigger surface for E2E,
  Official Open, Intraday, and Stream. Workflow metadata is provenance only.
- The Windows watchdog queries exact `IDX-SLOT:*` GitHub run metadata and uses
  an immutable local marker before requesting a workflow dispatch. Its marker
  is not visible to Cloudflare.
- The Cloudflare Worker routes all logical slots to one deterministic Durable
  Object coordinator. The coordinator reads GitHub metadata and the existing
  R2 archive authority, then dispatches only when the archive validator does not
  prove completion. Stream is intentionally absent from its slot table.
- Existing family validators remain the only completion authority. A
  `capture_complete` result requires a validated immutable parent and validated
  child identities/hashes; `covered_exact`, dispatch, and blocked markers are
  coordination/provenance states, not capture completion.
- Intraday uses the existing create-only claim/progress/commit hierarchy. A
  stale claim is currently rejected as
  `STOCKBIT_INTRADAY_STALE_CLAIM_FENCING_UNPROVEN`; there is no safe generation
  fence for taking over an external provider writer.

## Confirmed defects and bounded disposition

### Cloudflare same-slot dispatch race — corrected locally

At the source head, `processSlot()` read a marker and then awaited GitHub/R2
I/O before recording `dispatching`. Two same-slot requests could therefore
both observe no marker and both reach the GitHub dispatch side effect.

The remediation records a per-slot `dispatching` lease in the Durable Object's
synchronous prefix, before the first `await`. Subsequent same-slot requests
still perform read-only archive/GitHub observation so a newly visible durable
completion is not hidden, but they cannot dispatch while the lease is held.
All post-I/O marker transitions are owned by the same attempt. Because GitHub
workflow dispatch has no invalidating fence token, an old
`dispatching`/`dispatch_requested`/`dispatched` marker is never reclaimed by
age; it fails closed. This is an explicit safety-over-liveness boundary, not a
claim that stale recovery is solved.

Cloudflare's current Durable Object model supports this narrow change: the
object is single-threaded, synchronous storage operations are serialized, and
non-storage I/O can interleave requests. See the [Durable Objects rules](https://developers.cloudflare.com/durable-objects/best-practices/rules-of-durable-objects/)
and [SQLite storage API](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/).

### Intraday stale-claim takeover — deliberately remains fail-closed

The existing tests and implementation show that a fresh process after a hard
kill cannot enter the provider boundary, and an old claim cannot be silently
reclaimed. A create-only archive claim prevents two known contenders from
becoming owners, but it cannot fence a provider call that may still be active
after a process becomes stale. No unsafe takeover was added. Liveness of a
stale Intraday claim remains blocked until a separately proven external fence
exists.

### Cross-scheduler exactly-once — unresolved and activation-blocking

The new Durable Object lease protects competing Cloudflare requests only. The
Windows watchdog still has a separate local marker and can race a Cloudflare
request because neither shares the same lease/fence. Immutable create-only
archive commits protect canonical overwrite, but they do not prove that only
one provider stage ran before a commit. Production active fallback therefore
remains blocked for a full GitHub/Cloudflare/Windows exactly-once claim.

### 2026-09-03 E2E root-mismatch incident — not certified eliminated

This checkout contains no authoritative 2026-09-03 `x1_score` payload or
durable incident artifact from which to establish whether the run was
`NO_SCORE` or a scored run with an out-of-root pointer. The exact incident is
therefore **UNKNOWN**, not treated as fixed. The valid-scored path can still
reach the existing root-mismatch verifier; the V4 no-eligible/no-score branch
is only a safe early exit when the actual runtime status proves that case. No
production or protected evidence was accessed and no speculative E2E change
was made.

## Offline race and failure contract

The required safety outcomes are:

| Situation | Required outcome |
|---|---|
| Native exact on-time run | provenance only; archive validator decides completion |
| Native delayed/different-slot run | rejected as exact coverage |
| Windows exact workflow dispatch | provenance only; dispatch does not prove capture |
| Cloudflare observe-only | calculate `WOULD_DISPATCH`; never POST |
| Cloudflare active, first contender | acquire synchronous per-slot lease before I/O |
| Cloudflare active, same-slot contender | defer while lease is held |
| Fresh visible GitHub run | bounded in-flight grace only; no completion claim |
| Terminal/failed/cancelled run without archive completion | recovery remains eligible while the window is valid |
| Durable archive completion | final completion decision; no provider/dispatch needed |
| Stale Intraday claim without proven fence | fail closed before provider |
| Stream | excluded from Cloudflare redundancy |

The family grains remain unchanged: E2E session+stage, Official Open
session+exact slot, Intraday session recovery objective with slot provenance,
and Stream exact slot plus universe/source identity (outside this fallback).

## Validation boundary

The remediation adds only the Cloudflare coordinator lease decision/ownership
path and focused regression coverage. It does not alter production schedules,
workflow semantics, provider code, archive authority, Stream, Windows tasks,
or frozen science. Final validation results and exact commit identity are
reported with the independent-review handoff.

Pre-commit validation on this checkout:

- `npm ci`: PASS; 37 packages installed.
- Cloudflare Node suite: **73 passed, 0 failed**.
- Focused Python scheduler/recovery suite: **46 passed, 0 failed**.
- Full repository pytest: **406 passed, 0 failed**, with 3 pre-existing
  pandas `FutureWarning` messages.
- `python -m compileall -q src/idx_trade scripts`: PASS.
- Wrangler types for baseline staging, staging-live, and production: PASS
  (Wrangler emitted its existing advisory to install `@types/node`).
- Wrangler dry-run for baseline staging, staging-live, and production: PASS;
  no upload occurred.
- `npm audit --omit=dev`: 0 vulnerabilities. Full npm audit did not obtain a
  verdict because the registry advisory endpoint returned `ECONNRESET` and a
  retry did not complete; this remains an external-validation UNKNOWN.
- `git diff --check`: PASS.
