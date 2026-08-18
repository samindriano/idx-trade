# Ranking V4-3 — Corporate-Action Admission Result

Date: 2026-08-18
Branch: `research/idx-ranking-v4-3-ca-admission-v1`

## Verdict

`V4_3_CA_ADMISSION_PASS_HISTORICAL_EXECUTION_AUTHORIZED`

The final Corporate Action continuity result is admitted into the frozen V4-3 historical-execution lineage. Historical H5/H10 target materialization, model fitting, prediction generation, and preregistered evaluation are now authorized under the already-frozen V4-3 scientific contract.

This checkpoint does **not** contain V4 historical outcomes or performance. The admission run itself remained outcome-blind.

## Local admission artifact

External artifact root:

`D:\Documents\Project\idx-v4-3-ca-admission-20260818-v1`

Manifest:

`v4_3_ca_admission_manifest.json`

Manifest SHA-256:

`b0e29702d0f284c050472d6bfe05a45477082ae6b2df30866bb3e66bb2888345`

## Accepted CA gate

- Coverage-certified tickers: **602 / 611**
- Coverage-unresolved tickers: **9 / 611**
- H5 minimum per-date continuity rate: **0.9134615384615384**
- H10 minimum per-date continuity rate: **0.9102564102564102**
- Consensus minimum per-date continuity rate: **0.9102564102564102**
- Frozen validation dates passing continuity gate: **600 / 600** for H5, H10, and consensus
- Required gate: `>= 0.90`
- Cross-source conflicts: **0**

The final admitted CA parent remains the FREN KSEI exact replay lineage with:

- FREN PMHMETD V exact Regular/Negotiated Market ex-right transition: `2024-04-17`
- official KSEI rights schedule PDF SHA-256: `5af9284d88a7621f3b400fe7f9a28e104459ae6e710e47bf765974c940daaa91`
- FREN merger/security cessation exact transition: `2025-04-16`
- no record-date inference
- no price inference
- no EXCL price stitching

## Admission run safety flags

The successful admission output recorded:

- `historical_target_loaded=false`
- `historical_model_fit=false`
- `historical_performance_computed=false`
- next action: `RUN_FROZEN_V4_3_HISTORICAL_EXECUTION`

## Scientific boundary after this checkpoint

The pre-target blockers are closed. The next execution must use the already-frozen V4-3 contract without outcome-driven changes:

- target: `Close_(t+5)/Open_(t+1)-1` and `Close_(t+10)/Open_(t+1)-1`
- validation: frozen last-600 consensus-eligible sessions, six chronological 100-session folds, official-session purge length 10
- control: Context25 HGBR
- challenger: Context25 + Geometry3 HGBR
- no hyperparameter search
- no feature subset rescue
- no Structure-Lite substitution
- no post-result change to target, learner, folds, observability gate, Top30 definition, preprocessing, or promotion thresholds

Any execution/orchestration code used for the first historical run must be frozen and synthetic-tested **before** historical target access. Once historical V4 outcomes are accessed, bug fixes may not be used to rescue the same V4 generation.
