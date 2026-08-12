# Web Forward Session Recovery V1

Date: 2026-08-10 (Asia/Jakarta)
Status: recovery/idempotency contract frozen for implementation
Scope: local research monitoring only; no fresh-forward outcome access

## Objective

If the frontend, coordinator, Python worker, terminal, laptop, or dev server is interrupted, restarting monitoring must continue from durable canonical state rather than restarting the whole monitoring workflow.

Already completed session data must not be downloaded/recorded again. Already completed model runs must not be rerun. Only missing or genuinely incomplete work may be queued.

## Source of truth

Progress bars and in-memory process state are never the source of truth.

Use a small persistent registry (SQLite preferred) plus immutable session/model artifacts. The logical unique keys are:

- session data: `session_date`
- model result: `(session_date, model_id, model_fingerprint)`

A retry creates a new attempt record if audit history is desired, but it must not create a second canonical logical session/model result.

## Canonical tables / records

### `session_snapshots`

Minimum fields:

- `session_date` PRIMARY KEY
- `state`: `AVAILABLE | FETCHING | DATA_READY | DATA_FAILED`
- `snapshot_path`
- `snapshot_sha256`
- `manifest_path`
- `manifest_sha256`
- `started_at`
- `updated_at`
- `completed_at`
- `lease_owner`
- `heartbeat_at`
- `error_code`
- `error_message`

`DATA_READY` is immutable for normal operation. A second Monitor click for the same date verifies and returns the existing snapshot; it does not fetch it again.

### `model_runs`

Minimum fields:

- `session_date`
- `model_id`
- `model_fingerprint`
- unique constraint on `(session_date, model_id, model_fingerprint)`
- `state`: `NOT_STARTED | QUEUED | PREPARING | SCORING | WRITING | DONE | FAILED | INTERRUPTED`
- `progress_fraction`
- `artifact_path`
- `artifact_sha256`
- `manifest_path`
- `manifest_sha256`
- `started_at`
- `updated_at`
- `completed_at`
- `lease_owner`
- `heartbeat_at`
- `error_code`
- `error_message`

`DONE` requires a verified canonical artifact. Process disappearance is never enough to mark completion.

## Startup / reconnect reconciliation

Every coordinator startup performs reconciliation before accepting new work.

### Session reconciliation

For every eligible monitoring session date:

1. If registry says `DATA_READY`, verify the canonical snapshot + manifest hashes.
   - hashes valid -> keep `DATA_READY`; do nothing.
   - artifact missing/hash invalid -> fail closed as a data-integrity error; do not silently redownload/overwrite.
2. If state is `FETCHING` and the lease/heartbeat is stale:
   - if a complete canonical snapshot exists and hashes verify, promote/reconcile to `DATA_READY`;
   - if only temporary/incomplete files exist, discard/ignore the temporary attempt and set the logical session to retryable `DATA_FAILED`/`AVAILABLE`;
   - never create a duplicate canonical row.
3. If no canonical row exists, the date is `AVAILABLE` and may be fetched.

### Model-run reconciliation

For each `(DATA_READY session, eligible frozen model)`:

1. If registry says `DONE`, verify result artifact + manifest hashes.
   - valid -> skip forever for that model fingerprint/date.
   - invalid/missing -> integrity failure, not automatic success.
2. If state is `PREPARING`, `SCORING`, or `WRITING` with stale heartbeat:
   - if a complete canonical result artifact already exists and verifies, reconcile directly to `DONE` without rerunning;
   - otherwise mark `INTERRUPTED` and enqueue only this incomplete model run again from the existing immutable `DATA_READY` snapshot.
3. `FAILED`/`INTERRUPTED` retries must reuse the existing session snapshot; they must not trigger a data download.
4. `NOT_STARTED` runs are queued normally.

## Atomic completion protocol

Workers must never write directly into the final canonical artifact path while computing.

For a session snapshot or model result:

1. write to a temporary path on the same filesystem;
2. finish serialization;
3. calculate hashes and validate the artifact;
4. atomically replace/promote the temporary file into the canonical final path;
5. in one short registry transaction, store canonical path/hash and set `DATA_READY` or `DONE`.

Recovery handles the crash windows:

- crash before final promotion -> temporary attempt is ignored/retried;
- crash after final artifact promotion but before registry `DONE` commit -> startup verifies the final artifact and reconciles to `DONE` without recompute;
- crash after registry commit -> already complete and skipped.

Keep temporary and final paths on the same filesystem. Never treat a partial file as canonical.

## Database idempotency

Use database uniqueness constraints as the final guard, not only frontend checks.

- `session_snapshots.session_date` is unique.
- `(session_date, model_id, model_fingerprint)` is unique for canonical model runs.
- repeated create/enqueue operations use an idempotent insert/upsert/no-op behavior.

Therefore repeated clicks, browser refreshes, or duplicated enqueue requests cannot increment a forward counter twice.

## Coordinator / worker ownership

Preferred design for the local implementation:

- one lightweight coordinator owns canonical registry mutations and scheduling;
- bounded Python worker processes perform model computation;
- workers report progress/result back to the coordinator and write only attempt artifacts;
- coordinator verifies and commits canonical completion;
- workers do not independently decide that a logical session is complete.

This avoids multiple model processes competing as database writers while preserving independent per-model progress.

## Next-work computation

The dashboard derives work from durable state after every refresh/restart.

### Data button

Default target = earliest eligible closed IDX session whose canonical session state is not `DATA_READY`.

Example after restart:

- 13 Aug: `DATA_READY`
- 14 Aug: `DATA_READY`
- 17 Aug: missing

Primary button becomes `Ambil Data 17 Aug`.

It must not offer to redownload 13/14 Aug merely because the previous app process died.

### Model queue

For all `DATA_READY` dates, queue only model tuples that are not verified `DONE`.

Example after crash:

- 13 Aug / V2: `DONE` -> skip
- 13 Aug / V3: stale `SCORING`, no final artifact -> resume by rerunning only V3 on 13 Aug
- 14 Aug / V2: `DONE` -> skip
- 14 Aug / V3: `NOT_STARTED` -> queue
- 17 Aug: no data -> wait for Monitor button

No global restart is needed.

## Forward counters

A model generation's forward counter is calculated from durable unique verified results, never from attempt count.

For V2:

`completed_sessions = COUNT(unique session_date where model_id=HGB_XS_MARKET and frozen fingerprint matches and state=DONE and artifact_verified=true)`

Thus retrying the same date cannot turn `18/100` into `19/100`.

## UI recovery behavior

After browser/app restart, the page should immediately reconstruct:

- recorded/data-ready dates;
- earliest missing data date;
- per-model `DONE` dates;
- interrupted/retryable model runs;
- currently active workers if any are still valid;
- V2 `N/100` from verified canonical `DONE` rows.

Do not show a reset-to-zero progress state while durable records exist.

For a stale interrupted model, show for example:

`V3 · INTERRUPTED · safe to resume from 14 Aug snapshot` -> `Resume model`

For an already-complete model:

`V2 · DONE · artifact verified` with no rerun button by default.

## Tests required before promotion

At minimum simulate these interruption points with temporary runtime fixtures:

1. crash before session temp artifact is promoted;
2. crash after session final artifact exists but before `DATA_READY` registry commit;
3. crash after `DATA_READY` commit;
4. crash during one of several parallel model runs while another model already reached `DONE`;
5. crash after model final artifact promotion but before `DONE` registry commit;
6. duplicate Monitor clicks for the same date;
7. duplicate enqueue for the same `(date, model fingerprint)`;
8. restart with multiple missed dates and mixed per-model completion states;
9. hash mismatch on an alleged completed artifact must fail closed;
10. V2 100-session counter must remain unique/idempotent across retries.

## Outcome boundary

This recovery mechanism applies only to signal-side input snapshots and frozen model output snapshots. It must not read reserved H10 outcomes, compute forward verdict metrics, or write `FORWARD_OUTCOME_ACCESS_STARTED`.
