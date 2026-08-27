# Handoff

from: MAIN / Codex
to: ChatGPT independent review
task_id: IDX-CA-AWARE-FEATURE-BASIS-REMEDIATION-V1-R3
model_used: gpt-5.6-sol
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `5f95831949b475bee881be6969838196763375d3`
branch: `data/ca-aware-feature-basis-remediation-v1`
head_commit: `aa1bcd0ee32417aa4ec8ea48408c0e097d944beb` (substantive R3 implementation and audit commit; final branch may include the metadata-only formatting follow-up)

scope: |
  Outcome-blind R3 A-D reconciliation. Build the exact all-primary-liquid
  cross-sectional application population on accepted final-fit dates; compute
  observed-row backward dependency closure and separate primary-membership
  closure; reconcile old 241,487/239,836/241,724 support with current
  239,648/237,976/240,344 support; attest strict CA census identity and scope;
  reconcile KSEI coverage independently against fit, cross-section, and
  dependency-closure populations; and red-team the R2 under-scoping paths.
  Phase-E is explicitly not run.

files_changed:
  - `src/idx_trade/ca_aware_feature_basis_r3.py`
  - `scripts/run_ca_aware_feature_basis_reconciliation_v1.py`
  - `tests/test_ca_aware_feature_basis_reconciliation_v1.py`
  - `docs/checkpoints/2026-08-27_CA_AWARE_FEATURE_BASIS_REMEDIATION_V1_R3_A_D_AUDIT.md`
  - `coordination/handoffs/IDX-CA-AWARE-FEATURE-BASIS-REMEDIATION-V1-R3.md`

findings:
  - `H5=239648`, `H10=237976`, and deduplicated union `240344`, all with
    `629` unique tickers and support interval `2022-02-11`—`2026-07-17`.
  - Full primary-liquid cross-sectional application is `276153` rows,
    `716` tickers, and `980` fit dates; `35809` rows belong only to the
    cross-sectional application population.
  - Observed-row backward dependency closure is `365968` rows / `716`
    tickers, with separate frozen primary-membership closure of `364189`
    rows. No calendar-day subtraction was used.
  - KSEI coverage is `530/629` certified for fit, `567/716` certified for
    cross-section and closure, but all three remain unknown because the
    snapshot has no date-level/per-session as-of attestation.
  - Strict CA census has `26` complete input rows and all transition semantics
    remain unresolved; taxonomy/coverage is partial or contradictory.
  - Old support is a strict superset of current support: old-only rows are
    `1839` H5, `1860` H10, and `1380` union; current-only rows are zero.
  - The accepted `56602` old overlay is not proven applicable to current Phase-B
    support and was not recomputed.

decisions_made:
  - `DATA_ADMISSION=FAIL`.
  - `RESEARCH_ADMISSION=FAIL`.
  - `MODEL_PROMOTION=NOT_EVALUATED`.
  - `REFIT_AUTHORIZED=FALSE` and `COUNTER_ACTION=NONE`.
  - `HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN`.
  - No event date was promoted to a generic effective transition date; no
    family was collapsed; no partial source was promoted.

decisions_needed:
  - Independent ChatGPT review of the pinned R3 artifacts and population
    closure implementation.
  - If resumed, establish source-bound family taxonomy, effective-date/basis
    evidence, and KSEI per-session as-of/no-event coverage before any Phase-E
    application.

blocking_risks:
  - KSEI fit population is `629` tickers versus a `610`-ticker census and the
    census is not date/as-of attested.
  - Structural event dates and family transition semantics are unresolved,
    including conversion and capital-restructuring taxonomy conflicts.
  - Backward feature-window CA integrity is not globally certified; BBCA H/L/C
    equality does not certify Open basis continuity or the full dependency
    closure.
  - The R3 closure is an audit result, not authorization to rewrite historical
    features, rankings, or model identities.

artifact_root: |
  `D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v3-final`
  `MANIFEST.json` SHA-256:
  `198b619e7e465597de935837346a6369b0395162bc140fef1eb7ae5f8d0f690e`
  `r3_summary.json` SHA-256:
  `60ad6ad2c04482b09d8384966929d25be68915dfe00c983502d9149178cc41a9`
  Fresh rerun root:
  `D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v3-final-rerun`
  Fresh rerun output-hash mismatches: `0`.

validation_run:
  - `python -m pytest -q -rA --basetemp D:\Documents\Project\idx-ca-aware-feature-basis-pytest-ca-integrity-20260827-v2 tests/test_ca_aware_feature_basis_reconciliation_v1.py tests/test_ca_feature_basis_family_coverage_v1.py tests/test_ca_feature_basis_frozen_sources_v1.py tests/test_ca_feature_basis_gate_v1.py tests/test_ca_feature_basis_inputs_v1.py tests/test_ca_feature_basis_v1.py tests/test_ca_feature_basis_v4_contract_v1.py tests/test_ca_feature_basis_v4_recompute_v1.py tests/test_research_integrity_gate_v1.py tests/test_research_integrity_primitives_v1.py` — **95 passed**.
  - `python -m pytest -q --basetemp D:\Documents\Project\idx-ca-aware-feature-basis-pytest-full-20260827-v2` — **334 passed**.
  - `python -m py_compile src/idx_trade/ca_aware_feature_basis_r3.py scripts/run_ca_aware_feature_basis_reconciliation_v1.py` — **PASS**.
  - `git diff --check` — **PASS**.
  - R3 final runtime plus fresh-root deterministic rerun — **9/9 output hashes match**.

guardrails:
  - `PROVIDER_CALLS=FALSE`
  - `OUTCOMES_ACCESSED=FALSE`
  - `TARGET_VALUES_ACCESSED=FALSE`
  - `MODEL_FIT=FALSE`
  - `MODEL_SCORING=FALSE`
  - `HISTORICAL_FEATURE_RECOMPUTE=FALSE`
  - `PHASE_E_RUN=FALSE`
  - `COUNTER_MUTATED=FALSE`
  - `CANONICAL_ARTIFACTS_MUTATED=FALSE`

recommended_next_action: |
  Keep INC-001 open and historical CA-aware admission blocked. Review the R3
  manifest/summary and closure artifacts. Do not run Phase-E, acquire new
  providers, access outcomes, refit/score models, mutate counters, or rewrite
  canonical historical data.
