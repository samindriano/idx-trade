# Handoff: Financial PIT Feature Materialization V1

from: Codex / Financial PIT Feature Materialization
to: ChatGPT independent review
task_id: IDX-FINANCIAL-PIT-FEATURE-MATERIALIZATION-V1
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `09e8e8eba738e4dcea3c871f0eda83b53cc07c42`
branch: `data/financial-pit-feature-materialization-v1`
scope: Offline materialization of the accepted 13 Financial PIT features from the immutable fact corpus and period-boundary sidecar, GENERAL + CONSOLIDATED only.

head_commit: `0fd2c34bb0b8cd9bbe31bbf69fdb6051f5227f33`

files_changed:

* `src/idx_trade/financial_feature_contract.py`
* `src/idx_trade/financial_feature_panel.py`
* `tests/test_financial_feature_panel.py`
* `docs/checkpoints/2026-08-14_FINANCIAL_PIT_FEATURE_MATERIALIZATION_RESULT.md`
* this handoff

findings:

* The accepted sidecar contains `37,239 / 37,246` fact rows with explicit
  verified boundaries; the seven unresolved rows remain fail-closed.
* The final sparse panel has `258,401` rows, `531` issuers, `478` exact UTC
  decision dates, `4,226` issuer × exact-as-of state keys, and `150,407`
  `AVAILABLE` feature values.
* Only `GENERAL + CONSOLIDATED` rows are materialized.
* Knowledge-time leakage audit is zero; reporting and available-input
  provenance completeness are both 100%.
* No revision transitions were observed within the accepted
  GENERAL + CONSOLIDATED corpus; revision-aware selection remains implemented
  and covered by the focused test fixture.
* Q1/H1/9M/FY remain explicit per-row strata; no cross-period pooling,
  annualization, TTM, interpolation, zero-fill, or carry-forward occurs.

decisions_made:

* Use exact UTC filing knowledge timestamps as the sparse change-point
  decision timeline. Do not invent publication times or daily timestamps.
* Preserve unavailable statuses instead of materializing synthetic values.
* Keep fact-level provenance in `feature_panel.parquet` and the compact
  materialized-value sidecar `feature_provenance.jsonl`.
* Use the accepted contract formulas only; no performance-driven selection.

decisions_needed:

* ChatGPT review of whether the sparse change-point representation is the
  preferred input boundary before a separately preregistered model experiment.
* Separate authorization/specification for any downstream as-of join,
  feature normalization, model, or outcome evaluation.

blocking_risks:

* The seven unresolved period-boundary fact rows cannot contribute values.
* Feature coverage remains status-dependent; missing and denominator-invalid
  states are genuine missingness, not zeroes.
* No performance or model evidence was produced in this lane.

validation_run:

* Focused: `18 passed`.
* Full: `550 passed, 0 failed, 3 warnings`.
* Independent offline rerun: all five core artifact hashes and manifest hash
  matched exactly.
* Network/provider calls: `0`.
* Protected outcomes/model work/O2 changes: `false / false / none`.

artifacts:

* External root:
  `D:\Documents\Project\idx-financial-pit-feature-materialization-20260814-v1-cert-a`
* `feature_panel.parquet` SHA-256:
  `1d60ee69070546d21040af8c61f2170c5cca2254f131626a19bf4c1d59f3f023`
* `feature_provenance.jsonl` SHA-256:
  `c92a58ffcb4e3a9be38482a3edd03e6bb74919f39ccea3a61a5c9763466d1d3a`
* `audit.json` SHA-256:
  `95d1b0a74388c07dbb9ad3a550a1a7d3c6748a670fcfbec4093eb359ad584c35`
* `decision_timestamps.jsonl` SHA-256:
  `52c34642c82c9a0fcf9a2e2e8d48a7e15dc012ad01153f1ae0cfefdc5687c80f`
* `revision_transitions.jsonl` SHA-256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
* `MANIFEST.json` SHA-256:
  `639fc6e6fe3f7f853d23b6f5244c98ec8ed5c63b219aa59e698c8db908fb2140`

recommended_next_action: Stop for ChatGPT review. If accepted, write a separate preregistered feature/model experiment contract; do not access protected outcomes or alter O2 from this handoff.
