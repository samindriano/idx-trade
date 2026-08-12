# Handoff

from: MAIN / ChatGPT ARCHITECT-IMPLEMENTER
to: LOCAL / Codex verification agent
task_id: IDX-WEB-FORWARD-SESSION-MONITORING-V1
model_used: GPT-5.6 Sol
reasoning_level: local verification only
source_repository: samindriano/idx-trade
branch: frontend/model-monitoring-v1
head_commit: resolve after pull
scope: Verify the already-implemented Next.js monitoring UI locally and inventory the machine-local runtime/data/model paths needed for the next parent-ChatGPT implementation step. Do not take over repository implementation.

## Current division of labor

Parent ChatGPT is the default repository implementer. Codex is used only for local-only work that the parent cannot perform directly: pulling into the user's worktree, dependency/build/test execution, dev-server/browser checks, filesystem/runtime inspection, and later execution/testing against local market-data/model artifacts.

Do not implement the session registry/runtime adapter, scheduler, or new frontend architecture in this task unless the parent ChatGPT explicitly supplies a later bounded patch/fix request that genuinely requires local execution.

## Already implemented in GitHub

- Dedicated `/monitoring` route.
- Model selector grouped explicitly by generation: V2 models, V1 control, V3 backlog.
- Session-first monitoring UI with exact-date target surface.
- Independent champion-model progress rows; no global model progress bar.
- V2 counter semantics: only verified model `DONE` sessions count toward 100.
- Recovery/idempotency specifications:
  - `docs/WEB_FORWARD_SESSION_MONITORING_V1_SPEC.md`
  - `docs/WEB_FORWARD_SESSION_RECOVERY_V1.md`
- UI implementation checkpoint:
  - `docs/checkpoints/2026-08-10_WEB_FORWARD_MONITORING_UI_IMPLEMENTED.md`

## Local verification task now

1. In the existing frontend worktree, verify the checkout is on `frontend/model-monitoring-v1` and clean. If there are uncommitted/unpushed user changes, STOP and report them instead of overwriting anything.
2. Fetch/pull the latest remote branch by fast-forward only. No reset, rebase, force, or clean.
3. From `apps/web`, run the existing dependency install only if required by the current lockfile, then run production build/typecheck through the package scripts available in the repo.
4. Start the dev server and verify both:
   - `/`
   - `/monitoring`
   return successfully in the browser/HTTP.
5. Check the visible UI only for obvious compile/layout regressions. Do not redesign it locally.
6. Confirm the `/monitoring` `Ambil Data` button is intentionally disabled because the local adapter is not yet wired; this is expected, not a bug.
7. Inventory and report, without modifying them:
   - actual local path of the frozen V2 model artifact and manifest;
   - actual local path(s) of the current IDX raw/provider data used by the research runtime;
   - actual local Python executable/environment used for the 228-test research branch if still available;
   - whether the local worktree can import `idx_trade.ranking_v2_forward_runtime` successfully;
   - whether the local runtime contains the official exchange-session artifacts/calendar needed for exact-date targeting;
   - any existing local command/script that can refresh/download price data without reading forward outcomes.
8. Do NOT run fresh-forward scoring, do NOT read H10 outcomes/labels, do NOT write `FORWARD_OUTCOME_ACCESS_STARTED`, and do NOT mutate runtime research artifacts.
9. Keep the dev server running if convenient and report its URL.

## Required report back

Return:

- branch + local HEAD + remote HEAD;
- clean/dirty status;
- build/typecheck result;
- HTTP/browser result for `/` and `/monitoring`;
- screenshot if your local tooling can capture it, otherwise state that the server is ready for the user to screenshot;
- the local-only path/environment inventory above;
- exact error text for any blocker;
- no new commit unless a tiny build-only fix was explicitly necessary, in which case stop before push and describe the diff.

## Boundaries

- No fresh-forward outcome access.
- No model retraining/refit.
- No session scoring yet.
- No fake runtime/session data in the UI.
- No repository architecture changes.
- No push unless explicitly requested.

recommended_next_action_after_report:
Parent ChatGPT uses the local inventory to implement the real exact-date session registry/data adapter in GitHub. Codex is then called again only to execute/tests against the user's local runtime.