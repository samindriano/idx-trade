# Handoff

from: Codex  
to: MAIN / independent reviewer  
task_id: IDX-FORWARD-OFFICIAL-OPEN-RELIABILITY-REMEDIATION-V1  
model_used: GPT-5 Codex  
reasoning_level: high  
source_repository: `samindriano/idx-trade`  
source_commit: `32eaaa8e50d0521de7faef98faa8081219bc667b`  
branch: `fix/idx-e2e-forward-reliability-v1`  
head_commit: `PENDING_FINAL_COMMIT`

scope: Official Open transport retry/fallback hardening and idempotent manifest replay verification  
files_changed: `src/idx_trade/official_open_evidence_v1.py`, `src/idx_trade/official_open_capture_runtime_v2.py`, `scripts/run_official_open_capture.ps1`, `tests/test_official_open_evidence_v1.py`, `tests/test_e2e_dual_calendar_contract_v1.py`, `tests/test_official_open_scheduler_contract_v1.py`, plus the checkpoint

findings:
- existing manifest existence alone was insufficient for idempotent replay;
- direct retry/fallback boundaries needed explicit transient classification;
- empty/malformed direct HTTP 200 must not be treated as transport failure;
- Zapi transient attempts now remain auditable.
- the installed runner is now explicitly bound to `official_open_capture_runtime_v2`;
  the old v1 runtime is not used by the runner.

decisions_made:
- preserve `DIRECT_IDX_THEN_ZAPI_RAW_V1` and Official OpenPrice semantics;
- fail closed on malformed/incomplete direct 200;
- no scheduler mutation and no real provider capture.

decisions_needed:
- MAIN/reviewer acceptance and integration with the active E2E lane;
- separate outcome-blind evidence-health layer remains to be completed.

blocking_risks:
- current live 2026-08-24 failure remains external transport failure;
- deployed runtime checkout is an integration lineage separate from origin/main and must be reconciled explicitly.

validation_run: focused Official Open/E2E/Paper suite (61 passed); full pytest (760 passed, 3 pre-existing warnings); py_compile; diff-check
recommended_next_action: independent adversarial review, then selectively integrate into the active E2E lane and update the separate runtime checkout before the next genuine scheduled proof.
