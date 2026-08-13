# Handoff

from: W4 runner / provenance / boundary hardening worker
to: MAIN
task_id: IDX-PRV2-HARDEN-W4
model_used: GPT-5
reasoning_level: high
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: 477b4411c8c294e9ca5012a3079248033de5641c
branch: worker/idx-prv2-hardening-w4
head_commit: 477b4411c8c294e9ca5012a3079248033de5641c (unchanged; changes remain uncommitted because focused validation exposes a production defect)
scope: Synthetic/static adversarial tests for runner import/provenance, immutable-input hashes and schema boundaries, F1-F4 fold/candidate boundaries, output-directory protection, sealed summary flags, deterministic hashing, and forbidden artifact-load inspection. No real outcomes or runtime artifacts were opened.
files_changed:
- tests/test_path_risk_v2_runner_hardening.py
- coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W4-RUNNER-RESULT.md
findings:
- Hash checks for the frozen V1 model table, official calendar, and V2 spec blob are covered and fail closed on synthetic mismatches.
- Synthetic row-count, session-985+, normalized duplicate-identity, calendar-column/coverage, output-rerun, exact PR-002/PR-003 candidate, exact F1-F4 fold, sealed-flag, import-resolution, forbidden-load, and deterministic-manifest/hash guards were added.
- Missing frozen feature columns fail closed through the Parquet reader.
- Proven production defect: `_read_v1_model_table` accepts a synthetic model table with an unexpected extra column and accepts a synthetic model table whose frozen feature columns are physically reordered. It calls `pd.read_parquet(path, columns=columns)`, which projects the expected columns before any source-schema exactness check.
- No other production defect was proven in this bounded audit.
decisions_made:
- Kept all changes inside the exclusive W4 test file and this handoff.
- Used only temporary synthetic Parquet/CSV/text fixtures and the repository's frozen spec text; no real V1 model-table Parquet, raw H10/path labels, real V2 output, PR-002/PR-003 outcomes, F5/F6, post-2026-07-31 outcomes, or `FORWARD_OUTCOME_ACCESS_STARTED` were accessed.
- Did not edit production code, frozen specs, shared status/ledger, final V3-B ranker, or integration rules.
decisions_needed:
- MAIN should decide and implement the minimal source-schema guard: inspect the actual Parquet schema before projected read and require the exact frozen required-column set and order, rejecting unexpected, missing, or reordered columns.
- After that fix, rerun this W4 file and the focused Path Risk V2 tests before any real discovery execution.
blocking_risks:
- Current W4 hardening is blocked by the proven immutable model-table schema acceptance defect; do not declare `PATH_RISK_V2_PARALLEL_HARDENING_PASS_READY_FOR_LOCAL_DISCOVERY` or start the real F1-F4 run until the guard is fixed and the adversarial tests pass.
validation_run:
- `python -m pytest tests/test_path_risk_v2_runner_hardening.py` -> 14 passed, 2 failed (the expected extra-column and reordered-feature defect cases).
- `python -m pytest tests/test_path_risk_v2_runner_hardening.py tests/test_path_risk_v2.py tests/test_path_risk_v2_discovery_run.py` -> 24 passed, 2 failed; all failures are the same two W4 schema cases.
- `git diff --check` -> passed for tracked diff state; both allowed files are currently untracked additions.
recommended_next_action: MAIN applies the minimal exact-Parquet-schema validation in the production runner, reruns the two focused commands until this handoff's tests are green, then recombines the other hardening-worker evidence. Stop before any real PR-002/PR-003 execution if any hardening or full-suite check remains red.

stopping_status: PATH_RISK_V2_PARALLEL_HARDENING_BLOCKED_IMPLEMENTATION_DEFECT
