# Handoff

from: MAIN / Research Integrity QA
to: MAIN / ChatGPT review
task_id: RESEARCH-INTEGRITY-INC-001-CA-PRICE-BASIS-AUDIT-V1
model_used: gpt-5.6-luna workers; main integration
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 540a129c350b4bce62a5304e80a9cba30c4771af
branch: audit/research-integrity-data-qa-gate-v1
head_commit: pending final documentation commit
scope: Phase-1 integrity-gate validation/hardening and Phase-2 outcome-blind HEAVY QA audit of INC-001 historical corporate-action / backward feature price-basis integrity
files_changed:
  - src/idx_trade/research_integrity_gate_v1.py
  - scripts/run_research_integrity_gate_v1.py
  - tests/test_research_integrity_gate_v1.py
  - tests/test_research_integrity_primitives_v1.py
  - docs/research_integrity/INTEGRITY_INCIDENT_LEDGER.md
  - docs/checkpoints/2026-08-27_RESEARCH_INTEGRITY_INC001_CA_PRICE_BASIS_AUDIT.md
  - coordination/handoffs/RESEARCH-INTEGRITY-INC-001-CA-PRICE-BASIS-AUDIT-V1.md
  - coordination/TEAM_STATUS.md
findings:
  - Phase-1 framework had false-pass paths for empty evidence/requirements, naive timestamps, non-finite values, empty datasets/hash expectations, and trusted serialized reports; these were remediated with focused regression tests.
  - Phase-1 focused tests passed 21/21; full pytest passed 260/260; py_compile and diff-check passed.
  - Pinned INC-001 audit inputs/outputs are hash-consistent for consumed artifacts.
  - The strict CA census has 26 rows and all 26 have unresolved market-effective-date/continuity semantics.
  - Historical feature construction has no CA-aware backward reset/quarantine; BBCA traces 5/14/20/60 lookback exposure.
  - Independent exact-fit identity recomputation reconciles H5/H10/UNION impact counts: 56,514 / 56,221 / 56,602 changed rows, 486 tickers, 290 dates.
  - A source taxonomy mismatch is confirmed for the SINI voluntary-conversion example; no generic conversion formula is safe.
decisions_made:
  - DATA_ADMISSION = FAIL.
  - RESEARCH_ADMISSION = FAIL.
  - MODEL_PROMOTION = NOT_EVALUATED.
  - MATERIALITY = MATERIAL.
  - REMEDIATION_REQUIRED = YES, targeted/quarantine only.
  - INC-001 status advanced from OPEN_AUDIT to CONFIRMED; closure remains NOT_CLOSED.
  - No blanket repair or model action was performed.
decisions_needed:
  - Independent ChatGPT review of the checkpoint and whether to authorize a separately scoped remediation/quarantine lane.
blocking_risks:
  - unresolved event-family effective dates and knowledge-time mapping;
  - unsupported market-wide no-event coverage (344,740 rows) and 50 event-window crossings;
  - 1,657 stable YAHOO_RAW scale rows across 12 tickers;
  - backward feature-window contamination risk and material cross-sectional spillover;
  - audit source pin abef0d47 differs from current origin/main 30d725ff.
validation_run:
  - python -m pytest -q --basetemp D:\Documents\Project\idx-research-integrity-qa-gate-pytest-20260826-v5 tests/test_research_integrity_gate_v1.py tests/test_research_integrity_primitives_v1.py -> 21 passed
  - python -m pytest -q --basetemp D:\Documents\Project\idx-research-integrity-qa-gate-full-pytest-20260826-v1 -> 260 passed, 0 failed
  - python -m py_compile src/idx_trade/research_integrity_gate_v1.py scripts/run_research_integrity_gate_v1.py -> PASS
  - python scripts/run_research_integrity_gate_v1.py --help -> PASS
  - synthetic CLI PASS smoke -> exit 0
  - synthetic CLI UNKNOWN smoke -> exit 2 with missing pit.knowledge_time blocker
  - INC-001 DATA_ADMISSION gate -> exit 2, report SHA 6d2429438e62196df327464a51f7be1763e435e353849e0c2894b5bca502630e
  - INC-001 RESEARCH_ADMISSION gate -> exit 2, corrected report SHA 09e7dc95304e04bcf3688ca0c5af86464e130897dcf3d4588abc86f09642619c
  - git diff --check -> PASS
recommended_next_action: Stop for ChatGPT independent review. Do not access outcomes, refit models, mutate counters/runtime, run providers, or perform historical CA remediation until a new lane is explicitly authorized.
