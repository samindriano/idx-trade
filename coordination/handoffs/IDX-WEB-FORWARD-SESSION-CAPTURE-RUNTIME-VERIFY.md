# Handoff

from: MAIN / parent ChatGPT
to: LOCAL / Codex verification only
task_id: IDX-WEB-FORWARD-SESSION-CAPTURE-RUNTIME-VERIFY
model_used: GPT-5.6 Sol
reasoning_level: implementation complete; local verification
source_repository: samindriano/idx-trade
source_commit: resolve latest `frontend/model-monitoring-v1` after pull
branch: frontend/model-monitoring-v1
head_commit: resolve after pull
scope: Verify the newly implemented exact-date session-capture runtime against the user's local runtime. Do not take over implementation.

files_changed_by_parent:
- src/idx_trade/forward_monitoring.py
- tests/test_forward_monitoring.py
- apps/web/lib/monitor-runtime.ts
- apps/web/app/api/monitor/status/route.ts
- apps/web/app/api/monitor/capture/route.ts
- apps/web/app/monitoring/page.tsx
- apps/web/app/monitoring/monitoring.css
- apps/web/app/layout.tsx
- apps/web/.env.local.example
- docs/checkpoints/2026-08-10_FORWARD_SESSION_CAPTURE_RUNTIME_IMPLEMENTED.md

local configuration already discovered:
- runtime root: `D:\Documents\Project\idx-trade-data-gate-20260808v`
- Python: `C:\Users\Sam\AppData\Local\Programs\Python\Python313\python.exe`

allowed local actions:
1. fast-forward pull only; stop on dirty/diverged worktree;
2. create/update untracked `apps/web/.env.local` with the two local paths above;
3. run `python -m pytest tests/test_forward_monitoring.py`;
4. run the full existing pytest suite;
5. run `npm run build` in `apps/web`;
6. start the dev server;
7. GET `/api/monitor/status` and open `/monitoring`;
8. inspect which local security-master/tradability files the runtime discovery logic resolves to, if that can be done read-only;
9. report exact errors and stack traces if any.

prohibited:
- do not edit repository code;
- do not push;
- do not click or POST the real `Ambil Data` capture yet;
- do not fetch Stock Summary/Yahoo as part of a real forward session;
- do not score V2;
- do not read H10 outcomes/labels;
- do not write `FORWARD_OUTCOME_ACCESS_STARTED`;
- do not retrain/refit models;
- do not mutate existing research artifacts.

expected result:
- branch/HEAD/status;
- new monitoring test result;
- full pytest result;
- Next.js build result;
- `/api/monitor/status` HTTP/body summary;
- `/monitoring` HTTP result and screenshot if possible;
- resolved security-master/tradability artifact paths;
- exact blocker/error text, if any.

recommended_next_action:
Return the verification report to parent ChatGPT. Parent ChatGPT fixes any repo issues directly. After this gate passes, parent ChatGPT authorizes one controlled real `Ambil Data` session-capture smoke test; only after that passes should champion model fan-out be attached.