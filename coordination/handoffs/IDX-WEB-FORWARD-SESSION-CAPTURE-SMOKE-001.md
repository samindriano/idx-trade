# Handoff

from: MAIN / parent ChatGPT
to: LOCAL / Codex verification only
task_id: IDX-WEB-FORWARD-SESSION-CAPTURE-SMOKE-001
model_used: GPT-5.6 Sol
reasoning_level: controlled local runtime smoke test
source_repository: samindriano/idx-trade
source_commit: latest `frontend/model-monitoring-v1` after pull
branch: frontend/model-monitoring-v1
head_commit: resolve after pull
scope: Execute exactly one real outcome-blind session-data capture through the implemented local monitoring API, then inspect/verify the resulting canonical input artifact. Do not implement or edit repository code.

preconditions:
- pull fast-forward only;
- `apps/web/.env.local` already contains the verified local runtime root and Python executable;
- targeted/full tests and Next.js build previously passed;
- fresh-forward outcomes remain locked and must not be accessed.

important clarification:
- `calendar_ready=false` before the first capture is expected and is not a blocker.
- The POST capture path synchronizes the official forward calendar before selecting the earliest missing closed IDX session.
- Do not run a separate manual calendar bootstrap/copy from the historical `runtime_root/sessions` artifact.

allowed local actions:
1. Pull latest `origin/frontend/model-monitoring-v1`; verify branch/HEAD and clean tracked state.
2. Restart the existing Next.js dev server if needed so current code/env are loaded.
3. GET `http://127.0.0.1:3000/api/monitor/status` and record the pre-capture body summary.
4. Execute exactly one POST to `http://127.0.0.1:3000/api/monitor/capture` with JSON body `{}` so the runtime chooses the earliest missing official session automatically.
5. Record the HTTP response and returned `target_session`.
6. Poll `/api/monitor/status` every ~3 seconds until that target session reaches one terminal state: `DATA_READY` or `DATA_FAILED`. Do not submit a second capture while it is `FETCHING`.
7. If `DATA_READY`, read-only inspect:
   - `forward_monitoring/sessions/<target>/manifest.json`;
   - `model_input.parquet` row count/columns/date range/ticker uniqueness;
   - `session_evidence.parquet` state counts;
   - the canonical registry row in `monitor.sqlite3`;
   - SHA-256 verification of snapshot/evidence/manifest against the registry;
   - the generated forward calendar first/last session and checked range.
8. Confirm explicitly that the model input contains no outcome/label columns and no date later than the target session.
9. Confirm `FORWARD_OUTCOME_ACCESS_STARTED` remains absent and no H10 outcome/label source was read.
10. If `DATA_FAILED`, stop. Report exact `error_code`, `error_message`, target session, and relevant read-only `failure.json`/registry details. Do not retry and do not modify code/data manually.

prohibited:
- no repository source edits;
- no push;
- no second capture attempt;
- no model scoring/inference yet;
- no V2/V3/V4 model-run creation;
- no model refit/retraining;
- no H10 label/outcome access;
- no `FORWARD_OUTCOME_ACCESS_STARTED` write;
- no manual alteration of existing research artifacts;
- no force/reset/clean/rebase.

expected report:
- local/remote HEAD + git status;
- pre-capture status summary;
- POST HTTP status/body;
- chosen target session;
- terminal session state + elapsed time;
- if PASS: rows/tickers/columns, evidence state counts, artifact paths and hash-verification result, calendar range, idempotency-safe registry state;
- if FAIL: exact failure details and where it occurred;
- confirmation that outcomes/models were untouched.

stop condition:
Stop after this single session reaches `DATA_READY` or `DATA_FAILED`. Return the report to parent ChatGPT. Parent ChatGPT owns all code fixes and decides whether V2 champion fan-out may be implemented next.
