# Handoff

from: MAIN / Codex  
to: ChatGPT independent review  
task_id: IDX-CA-AWARE-FEATURE-BASIS-REMEDIATION-V1-A-D-AUDIT  
model_used: gpt-5.6-sol  
reasoning_level: xhigh  
source_repository: `samindriano/idx-trade`  
source_commit: `8199e2477b764bd323f65265de9129e640c74f42`  
branch: `data/ca-aware-feature-basis-remediation-v1`  
head_commit: `7d725c1c2f816f51917a4f9df15a76bc0646321f`

scope: |
  Outcome-blind Phase-A exact-fit population reconciliation, Phase-B temporal/
  as-of coverage reconciliation, Phase-C structural family matrix, and Phase-D
  in-scope event classification using accepted local Phase-A/B and KSEI census
  artifacts. Phase-E historical application was conditionally evaluated and
  not run because A-D gates remain insufficient.

files_changed:
  - `scripts/run_ca_aware_feature_basis_reconciliation_v1.py`
  - `tests/test_ca_aware_feature_basis_reconciliation_v1.py`
  - `docs/checkpoints/2026-08-27_CA_AWARE_FEATURE_BASIS_REMEDIATION_V1_A_D_AUDIT.md`
  - `coordination/handoffs/IDX-CA-AWARE-FEATURE-BASIS-REMEDIATION-V1-A-D-AUDIT.md`
  - `docs/checkpoints/2026-08-27_CA_AWARE_FEATURE_BASIS_REMEDIATION_V1_A_D_AUDIT_R2.md`

findings:
  - `H5=239648` rows and `H10=237976` rows; deduplicated union `240344`; all have `629` unique tickers.
  - Frozen KSEI census has `610` tickers (`567` certified, `43` unresolved); `67` fit tickers are absent and `48` KSEI tickers are outside fit union.
  - Only `530/629` fit tickers are KSEI-certified; KSEI coverage has no per-session temporal/as-of/no-event attestation fields.
  - Strict CA census has `26` positive rows, all effective-date/continuity unresolved; `5` fall in exact fit population and support interval and remain `UNRESOLVED`.
  - Required family coverage is partial/contradictory: voluntary-vs-mandatory conversion taxonomy, capital restructuring-vs-reduction mapping, and no distinct certified merger contract.
  - Exact dependency geometry is preserved as `5/14/20/20/59` observed-row exposure counts for the relevant V4 features.

decisions_made:
  - `DATA_ADMISSION=FAIL`.
  - `RESEARCH_ADMISSION=FAIL`.
  - `MODEL_PROMOTION=NOT_EVALUATED`.
  - `MODEL_REFIT=NOT_AUTHORIZED` and `COUNTER_ACTION=NONE`.
  - Phase-E historical feature/rank/context recomputation was not run.
  - No source date was inferred, no family was collapsed, and no partial source was promoted globally.

decisions_needed:
  - Independent ChatGPT review of the A-D artifact hashes and fail-closed verdict.
  - If resumed, source-bound family taxonomy and per-session no-event/as-of coverage must be established before any Phase-E application.

blocking_risks:
  - Final-fit population is not equal to KSEI census population.
  - KSEI snapshot retrieval time is not historical publication/knowledge or per-session no-event coverage.
  - Transition dates and structural-family completeness are unresolved/contradictory.
  - Phase-A acceptance document is referenced by historical Git ref/blob but absent from this branch; identity artifacts remain hash-bound by Phase-B manifest.

validation_run:
  - `python -m pytest -q -rA --basetemp D:\Documents\Project\idx-ca-aware-feature-basis-pytest-20260827-v3 tests/test_ca_aware_feature_basis_reconciliation_v1.py tests/test_ca_feature_basis_v1.py tests/test_ca_feature_basis_inputs_v1.py tests/test_ca_feature_basis_frozen_sources_v1.py tests/test_ca_feature_basis_gate_v1.py tests/test_ca_feature_basis_family_coverage_v1.py tests/test_ca_feature_basis_v4_contract_v1.py tests/test_ca_feature_basis_v4_recompute_v1.py tests/test_research_integrity_gate_v1.py tests/test_research_integrity_primitives_v1.py` — **84 passed**.
  - `python -m py_compile scripts/run_ca_aware_feature_basis_reconciliation_v1.py ...` — **PASS**.
  - `git diff --check` — **PASS**.
  - Offline reconciliation run into `D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v1` — **complete**.
  - Fresh-root deterministic rerun — **0 output-hash mismatches**.
  - R2 runner correction verified the full clean-panel observation interval (`2021-04-29` — `2026-07-31`) from the hash-pinned date column only; fresh-root R2 rerun — **0 output-hash mismatches**. R2 output root: `D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v2`; manifest SHA: `0a83472bf04cdd8d7d62cfd0e59d8323ba46065f7079d3298059e7f1e60e6fb7`.
  - Focused post-R2 suite — **84 passed**; fresh-basetemp full repository suite — **323 passed**; `py_compile` — **PASS**; `git diff --check` — **PASS**.

recommended_next_action: |
  Keep INC-001 open and all historical CA-aware model admission blocked. Review
  the pinned A-D artifacts. Do not run Phase-E, acquire providers, access
  outcomes, refit/score models, mutate counters, or rewrite canonical data.
