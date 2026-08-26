# Handoff

from: Codex
to: ChatGPT
task_id: CA-FEATURE-BASIS-INTEGRITY-AUDIT-V1
model_used: GPT-5.6 with read-only Luna xhigh investigation workers
reasoning_level: high
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: abef0d47b0f728adcffbb7c4e6353b09739fa66f
branch: audit/ca-feature-basis-integrity-v1
head_commit: pending final audit commit
scope: Outcome-blind forensic audit of corporate-action price-basis integrity, backward feature-window exposure, BBCA 2021, strict event-family evidence, and exact accepted V4-X1 final-fit input identities using immutable local artifacts only.
files_changed: scripts/run_ca_feature_basis_integrity_audit_v1.py; tests/test_ca_feature_basis_integrity_audit.py; docs/checkpoints/2026-08-26_CA_FEATURE_BASIS_INTEGRITY_AUDIT_V1.md; coordination/handoffs/CA-FEATURE-BASIS-INTEGRITY-AUDIT-V1.md; coordination/TEAM_STATUS.md
findings: Backward CA feature-window risk is present because no CA-aware reset/quarantine was found. Exact v1.2 basis-overlay impact is material for 12 accepted basis tickers: union 56,602 changed rows across 486 tickers and 290 dates, including 681 direct and 55,921 spillover rows. BBCA 2021 has a recorded IDX 1:5 split and 61 traced post-event rows with five/14/20/60-session backward exposure, but zero exact H5/H10 final-fit rows because combined continuity support is false. Strict CA evidence contains 26 rows with unresolved generic effective dates; rights/bonus/mandatory-conversion semantics are not interchangeable.
decisions_made: No provider call, no canonical overwrite, no model/outcome access, no feature mutation, and no remediation/refit. External v4 artifacts remain the audit evidence root. Final status is AUDIT_COMPLETE_REVIEW_REQUIRED.
decisions_needed: Independently decide whether to freeze a CA-aware backward feature-window remediation contract and which event-specific effective-date evidence is admissible. Do not treat this audit as blanket authority to correct prices or rerun a model.
blocking_risks: Current target-window continuity guards do not cover backward feature windows. Strict market-wide event dates remain unresolved. A local event can cause broad rank/context spillover. No blanket price-basis repair is defensible from this audit alone.
validation_run: Focused audit tests 2 passed; full pytest passed with clean basetemp and exit code 0; py_compile passed; git diff --check to be rerun after docs/status edits. Audit runner completed once against pinned external artifacts; no provider/outcome/model access.
recommended_next_action: ChatGPT independent review. If accepted, freeze a narrowly scoped remediation specification before any code/data rerun. Do not refit, rescore, reacquire, or alter V4-X1 inputs yet.
