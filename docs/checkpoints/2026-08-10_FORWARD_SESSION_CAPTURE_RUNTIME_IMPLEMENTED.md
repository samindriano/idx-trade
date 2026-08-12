# Forward Session Capture Runtime Implemented

Date: 2026-08-10 (Asia/Jakarta)
Branch: `frontend/model-monitoring-v1`
Status: IMPLEMENTED — pending local runtime verification

## Scope completed directly by parent ChatGPT

A real local session-data monitoring layer now exists behind the Next.js `/monitoring` route.

Implemented:

- `src/idx_trade/forward_monitoring.py`
  - SQLite canonical registry under the local runtime root;
  - unique session identity by `session_date`;
  - model-run registry keyed by `(session_date, model_id, model_fingerprint)` for the next fan-out phase;
  - persistent states and stale-worker reconciliation;
  - official forward IDX Exchange-Day calendar synchronization;
  - earliest-missing-session calculation;
  - exact-date capture with no silent skip over earlier missing sessions;
  - official IDX Stock Summary point evidence for Regular-Market ACTIVE / NO_TRADE classification;
  - Yahoo raw OHLCV acquisition only for official ACTIVE rows;
  - local raw-price reuse before provider download;
  - unresolved point evidence and missing ACTIVE prices fail closed;
  - immutable per-session `model_input.parquet`, `session_evidence.parquet`, official stock-summary snapshot and manifest;
  - hash-pinned `DATA_READY` completion;
  - duplicate clicks on a verified DATA_READY session are idempotent no-ops;
  - interrupted FETCHING state reconciles from final artifacts when possible or becomes retryable DATA_FAILED otherwise;
  - no fresh-forward outcome access.

- Next.js thin local adapter:
  - `apps/web/lib/monitor-runtime.ts`;
  - `GET /api/monitor/status`;
  - `POST /api/monitor/capture`;
  - local-only mutation origin guard;
  - one-time local configuration via `IDX_TRADE_RUNTIME_ROOT` and `IDX_TRADE_PYTHON`;
  - no separate FastAPI service;
  - capture is launched as an independent local Python process and browser state is rebuilt from SQLite, not process memory.

- `/monitoring` now reads the real registry:
  - runtime connected/offline state;
  - real DATA_READY count;
  - real earliest missing session;
  - exact-date target selector;
  - one `Ambil Data <session>` action;
  - per-date FETCHING / DATA_READY / DATA_FAILED / AVAILABLE states;
  - errors remain attached to the relevant data session;
  - V2 counter remains based only on future verified model-run DONE rows;
  - no fake model progress is rendered.

## Recovery semantics

The implementation follows `docs/WEB_FORWARD_SESSION_RECOVERY_V1.md`:

- progress bars are not source of truth;
- verified DATA_READY sessions are skipped after restart;
- duplicate capture requests cannot create a second canonical session row;
- a crash before canonical promotion is retryable;
- a crash after final artifacts exist but before the registry commit is reconciled to DATA_READY;
- model-run schema is ready for independent later V2/V3/V4 workers.

## Tests added

`tests/test_forward_monitoring.py` covers:

1. successful exact-date capture;
2. repeated capture of a verified session is a no-op and does not refetch Stock Summary;
3. unresolved direct point evidence fails closed into DATA_FAILED;
4. stale FETCHING with complete final artifacts reconciles to DATA_READY;
5. stale FETCHING without canonical artifacts becomes an interrupted failure;
6. a later target cannot skip an earlier missing official session.

These tests have not yet been run on the user's local machine at this checkpoint.

## Deliberate sequencing decision

Champion-model fan-out is **not enabled yet**.

Reason: the user explicitly wants simple, reliable monitoring and the previous project failed operationally because too many stages were coupled before the data action itself was proven. The correct gate is:

`real exact-date capture PASS locally -> then attach independent champion runners`

No global mega-job will be introduced.

## Outcome boundary

No H10 forward outcomes/labels were read, summarized, scored or exposed.

`FORWARD_OUTCOME_ACCESS_STARTED` was not written.

## Next local-only verification

Local Codex may now be used only to:

1. pull the latest branch;
2. configure an untracked `apps/web/.env.local` with the already discovered runtime root and Python executable;
3. run the new Python monitoring tests plus the full existing pytest suite;
4. run Next.js build;
5. start the dev server;
6. test `GET /api/monitor/status` without capturing data first;
7. report the exact discovered security-master/tradability artifact selected by the runtime;
8. stop before a real provider-mutating capture unless parent ChatGPT explicitly authorizes that local test.

Parent ChatGPT remains the implementer and will fix repository code based on those local results.