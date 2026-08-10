# Web Forward Session Monitoring V1 Spec

Date: 2026-08-10 (Asia/Jakarta)
Status: UX/runtime contract frozen for implementation
Scope: local research monitoring only; no fresh-forward outcome access

## Why this exists

The previous Market Movement Analyzer Next.js monitoring flow bundled market-data refresh, completeness checks, prediction preparation, ledger recording, and outcome updates behind one global `DAILY_ROUTINE` job. The UI then polled that single job until a terminal state. That design made it difficult for the operator to know whether a failure belonged to data acquisition, one model, ledger state, or outcome processing.

IDX-Trade must not repeat that coupling.

## Core operator rule

The primary **Monitor / Ambil Data** button has exactly one responsibility:

> acquire and freeze the market-data snapshot for one explicit IDX session date.

It does not mean that model monitoring is complete.

After the data snapshot becomes `DATA_READY`, every eligible frozen champion model is automatically queued to score the same immutable session snapshot. Model runs execute independently and may progress or fail independently.

A model's monitoring session is complete only when that model has finished scoring and its immutable prediction/ranking snapshot has been persisted and verified.

## Two-layer state model

### Layer 1 — session data

One record per IDX session date.

States:

- `AVAILABLE` — closed IDX session exists but local frozen snapshot does not.
- `FETCHING` — exact target session data is being acquired/validated.
- `DATA_READY` — immutable input snapshot exists and passed completeness/provenance checks.
- `DATA_FAILED` — data acquisition/validation failed; no model is marked failed because models have not started.

The data layer never reports model progress.

### Layer 2 — per-model run

One record per `(session_date, model_id)`.

States:

- `NOT_STARTED`
- `QUEUED`
- `PREPARING`
- `SCORING`
- `WRITING`
- `DONE`
- `FAILED`

Failure of one model must not cancel or relabel other model runs for the same date.

Retry is per model. A successful frozen data snapshot must not be downloaded again merely because one model run failed.

## Backfill / missed-date behavior

The dashboard must expose the earliest missing eligible session as the default target.

Example:

- last completed data session: 2026-08-12
- today: 2026-08-17
- eligible closed IDX sessions missing: 2026-08-13, 2026-08-14, 2026-08-17

The primary action initially becomes:

`Ambil Data 13 Aug`

After the 13 Aug snapshot reaches `DATA_READY`, the next default target becomes 14 Aug, then 17 Aug.

The operator may inspect other dates, but normal one-button operation must never silently skip an earlier missing eligible session.

Historical/backfill acquisition must use data as-of the selected session and must not use future bars/features relative to that session.

## Automatic parallel model execution

When a session transitions to `DATA_READY`:

1. resolve the frozen champion registry;
2. identify models eligible to monitor that date;
3. enqueue all eligible models from the same immutable session snapshot;
4. execute with a bounded process scheduler;
5. persist atomic per-model progress/status;
6. do not wait for all models before publishing a model's own `DONE` state.

The UI must render progress independently, e.g.:

- `V2 · HGB_XS_MARKET` — DONE
- `V3 · future champion` — SCORING 64%
- `V4 · future champion` — FAILED · Retry model

There is no single global progress bar whose completion implies every model succeeded.

A lightweight text summary such as `2 of 3 models complete` is allowed, but it must not replace the independent model states.

## V2 100-session contract

The V2 champion `HGB_XS_MARKET` remains the frozen independent-forward model.

Its 100-session progress increments only when the V2 run for a qualifying session is `DONE` and the prediction/ranking artifact is persisted and verified.

`DATA_READY` alone does not increment the V2 model counter.

The dashboard may show signal-side/session-side progress and provenance. It must not expose reserved H10 labels/outcomes, aggregate PASS/MIXED/FAIL metrics, or write `FORWARD_OUTCOME_ACCESS_STARTED` without the separate outcome-access authorization.

## Model registry semantics

The dashboard is designed for multiple model generations.

Each registered monitorable model needs at minimum:

- `model_id`
- `generation`
- `display_name`
- frozen model artifact fingerprint
- frozen feature/config fingerprint
- monitoring start session
- monitoring status
- target forward sessions if applicable

A newly frozen V3/V4 model starts its own forward sequence from its own authorized start session. It does not retroactively become part of V2's independent test.

## Minimal UI

The monitoring page should remain simple.

### Session control

- selected/default target date
- state chip: `Missing data`, `Fetching`, `Data ready`, `Failed`
- one primary button: `Ambil Data <date>` or `Coba Ambil Lagi`
- compact calendar/session strip for recorded, missing, and future sessions

### Model runs for selected date

One row/card per champion model:

- generation + model name
- independent status
- independent progress/stage
- start/end time
- retry button only for failed model
- artifact verification status

### V2 forward progress

Show:

- `N / 100 model sessions complete`
- last completed V2 session
- next missing session
- outcome access: `LOCKED`

Do not show a live outcome metric.

## Color direction

Avoid generic white + green fintech styling.

Preferred light identity:

- warm ivory/off-white page background
- white surfaces
- deep ink/navy primary text/navigation
- cobalt/indigo primary accent
- amber/coral for pending/warnings
- green only for true success states
- red only for failures

## Implementation preference

Keep the local stack materially simpler than the previous Market Movement Analyzer migration.

Preferred structure:

- Next.js UI and thin local route handlers;
- one Python monitoring domain/orchestrator as source of truth;
- immutable filesystem/runtime artifacts or another minimal atomic registry;
- no separate FastAPI service unless a concrete requirement proves it necessary;
- no single mega-job combining data acquisition, all model inference, and outcome evaluation;
- bounded parallel Python processes for model scoring;
- atomic per-session and per-model status writes so refresh/restart can recover state.

The frontend must never infer success from process disappearance. `DONE` requires an explicit verified artifact/status from the Python domain.

## Explicitly rejected legacy behavior

Do not reproduce:

- one global `DAILY_ROUTINE` progress bar for data + prediction + outcomes;
- a Monitor button whose meaning is "run everything";
- global failure when only one model fails;
- forced data redownload to retry one model;
- hidden catch-up based only on backend `pending_session` with no visible target date;
- counting a session complete before the model actually finished and persisted its result;
- coupling signal collection with reserved outcome evaluation.

## Next implementation task

Implement the session-data contract and the monitoring UI against real local status endpoints first. Use synthetic/temp fixtures only in tests. Do not fabricate runtime market/model state in the production UI.

Then implement bounded per-model parallel execution using the frozen champion registry. V2 outcome access remains blocked.