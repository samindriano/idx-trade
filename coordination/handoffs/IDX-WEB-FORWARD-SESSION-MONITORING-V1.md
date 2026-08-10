# Handoff

from: MAIN / ChatGPT ARCHITECT
to: LOCAL / Codex implementation agent
task_id: IDX-WEB-FORWARD-SESSION-MONITORING-V1
model_used: GPT-5.6 Sol
reasoning_level: architect review
source_repository: samindriano/idx-trade
source_commit: frontend/model-monitoring-v1 after `docs/WEB_FORWARD_SESSION_MONITORING_V1_SPEC.md`
branch: frontend/model-monitoring-v1
head_commit: resolve after pull
scope: Implement simple date-targeted session-data acquisition and independent parallel champion-model monitoring UI/runtime. Preserve research boundaries and do not access fresh-forward outcomes.
files_changed:
- docs/WEB_FORWARD_SESSION_MONITORING_V1_SPEC.md
- coordination/handoffs/IDX-WEB-FORWARD-SESSION-MONITORING-V1.md
findings:
- The pushed Market Movement Analyzer Next.js branch `migration/nextjs-fastapi-monitoring-actions` confirms the legacy web flow used one `DAILY_ROUTINE` job that bundled benchmark/data refresh, completeness, prediction, monitoring ledger updates, and mature-outcome updates.
- Its frontend `MonitoringControl` polls one global job and derives the primary action from `pending_session`; this is intentionally not the IDX-Trade architecture.
- The user requires one-click exact-date data acquisition/backfill, followed by independent parallel champion-model execution with visible per-model progress.
decisions_made:
- The primary Monitor button means only `fetch/freeze exact session data`.
- Missed sessions are explicit; earliest missing eligible IDX session is the default target and catch-up proceeds in order.
- After `DATA_READY`, all eligible frozen champions auto-queue against the same immutable snapshot using bounded parallelism.
- Each `(session, model)` owns its own status/progress; one model failure cannot fail other models.
- Model completion requires persisted + verified model output. Data readiness alone is not model completion.
- V2 100-session counter advances only for verified `HGB_XS_MARKET` model sessions.
- Signal-side monitoring stays separated from reserved H10 outcome access.
- Preferred local architecture avoids a separate FastAPI service unless proven necessary; keep Next.js thin and Python domain logic authoritative.
- Visual direction: warm light base + deep ink/navy + cobalt/indigo + amber/coral; green only for success.
decisions_needed:
- Concrete local market-data acquisition adapter for exact historical session dates must be selected from existing IDX-Trade provider/runtime contracts without weakening provenance.
- Exact champion registry format and bounded scheduler slots should be implemented from existing frozen model manifests/runtime notes.
blocking_risks:
- Do not invent or display fake session/model progress in production.
- Do not use future bars when backfilling a selected historical session.
- Do not read or expose fresh-forward outcomes or write `FORWARD_OUTCOME_ACCESS_STARTED`.
- Do not couple outcome evaluation into the Monitor button.
validation_run:
- Documentation/spec only in this handoff; no runtime/model execution.
recommended_next_action:
1. Pull latest `frontend/model-monitoring-v1`.
2. Read `AGENTS.md`, `docs/CURRENT_STATUS.md`, `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`, and `docs/WEB_FORWARD_SESSION_MONITORING_V1_SPEC.md`.
3. Inspect existing IDX-Trade provider/runtime code for the smallest exact-date EOD snapshot adapter.
4. Implement real local session status + `Ambil Data <date>` first, with tests for skipped-date catch-up and idempotent retry.
5. Then implement independent bounded parallel champion runs and per-model status persistence/recovery.
6. Build/typecheck/test the Next.js UI and Python tests.
7. Stop before any fresh-forward outcome access.