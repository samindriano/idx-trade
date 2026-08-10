# Ranking V3 Hypothesis Ledger V1

Status: **V3-A COMPLETE; V3-B PROMOTED; V3-C IMPLEMENTED / PREREGISTERED / NOT YET SCORED; 5 CANDIDATES EVALUATED**

Ordinals `001`-`003` were executed exactly once on V2F1-V2F4 after mandatory control equivalence. Ordinals `004`-`005` were then executed exactly once on V2F1-V2F4 under the frozen V3-B contract. The cumulative evaluated counter is now `5`. Ordinals `006`-`007` are preregistered for V3-C but remain unviewed. All results are historical development evidence, not independent validation.

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 001 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-CONTROL-001` | exact uniform V2 `HGB_XS_MARKET` control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 002 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL252-002` | normalized exponential decay, H=252 official sessions | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 003 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL504-003` | normalized exponential decay, H=504 official sessions | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 004 | `V3-B-STRUCTURE-LITE-V1` | `V3-B-STRUCTURE-LITE-V1-CONTROL-004` | exact frozen V2 `HGB_XS_MARKET` control on V2F1-V2F4 | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 005 | `V3-B-STRUCTURE-LITE-V1` | `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` | exact V2 25-feature prefix + fixed eight-feature causal Structure-Lite bundle | `COMPLETE` | `true` | `PROMOTE_FOR_NEXT_RESEARCH_STEP` |
| 006 | `V3-C-REGIME-V1` | `V3-C-REGIME-V1-CONTROL-006` | exact frozen V2 `HGB_XS_MARKET` control on V2F1-V2F4 | `IMPLEMENTED_NOT_RUN` | `false` | `PENDING_RUN` |
| 007 | `V3-C-REGIME-V1` | `V3-C-REGIME-V1-TWO-EXPERT-007` | one frozen NORMAL/STRESS two-expert architecture using exact V2 25 features | `IMPLEMENTED_NOT_RUN` | `false` | `PENDING_RUN` |

## V3-A executed result identity

- parent hypothesis: `RANKING_V2_HGB_XS_MARKET`;
- run/source commit: `362510997e3db41e81b21ec8e7422308338fbef1`;
- implementation code commit: `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`;
- spec SHA-256: `53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa`;
- review addendum Git blob: `1ee532c849636c47dab12ba3702ce7590abfcd74`;
- prepared cache SHA-256: `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- prepared manifest SHA-256: `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- fold set: `V2F1-V2F4` only;
- feature-order hash: `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72`;
- model identity: exact `HGB_XS_MARKET`, frozen V2 preprocessing/HGB parameters, random seed `42`;
- metrics artifact: `ranking_v3_a_recency_f1_f4_metrics.csv`;
- metrics artifact SHA-256: `fe22292ebad0d553042eb8f48faf3ddb13584e8062776a46d63adfd55bf8c603`;
- runtime environment: Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`, PyArrow `23.0.1`, scikit-learn `1.8.0`, Windows 11;
- output directory: `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_recency_discovery_20260810_retry1`.

V3-A deterministic result: `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`. No recency component survived. Cumulative candidate count after V3-A is `3`.

## V3-B executed result identity

Controlling specification:

`docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`

- reported SHA-256 `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- Git blob `0392ab506aa451355697327d416f8f2b2ea21d4f`.

Independent review addendum:

`docs/RANKING_V3_STRUCTURE_LITE_SPEC_REVIEW_ADDENDUM_V1.md`

- Git blob `717871707e833ab9818c249d52aae5b234334fc4`.

Implementation lineage:

- `d451befd10e32711fdaf7f468f6038e2e58f0376` — causal geometry engine;
- `837e5ce42e90825451b019517022db7d79a7bf81` — cache preparation and exact F1-F4 runner;
- `c06f1a32068e3b8ad7c09385709a7f80258d11b4` — focused tests;
- `885430ef9d2dbacd85af71fa1119be4a96c34752` — test-fixture correction only.

Frozen eight-feature order:

1. `structure_support_distance_atr`
2. `structure_resistance_distance_atr`
3. `structure_support_touch_count_60`
4. `structure_resistance_touch_count_60`
5. `structure_nearest_level_age_sessions`
6. `structure_role_reversal_count_120`
7. `structure_breakout_retest_state`
8. `structure_breakout_volume_confirmed`

The exact local run completed on V2F1-V2F4. Ordinals `004` and `005` are viewed exactly once and the cumulative evaluated denominator is `5`.

- source/run HEAD: `eee4ed0458fdfdea5fdc0f5335ec211efd3dd80b`;
- full pytest: `252 passed, 0 failed, 3 warnings`;
- cache SHA-256: `7084759fddaa20e82ec03e50205f2872520e6b3e11ea5f294033589a9c803405`;
- cache manifest SHA-256: `e428cad0ff24b57977106482cef1478e60c0660adcee6dbf103803516b35aeb2`;
- control equivalence: `V3_B_CONTROL_EQUIVALENCE_PASS`, 84,732 rows, max score/metric difference `0.0`;
- candidate verdict: `PROMOTE_FOR_NEXT_RESEARCH_STEP`;
- deterministic decision: `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`;
- metrics artifact SHA-256: `0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357`;
- summary artifact SHA-256: `a8ca2fea755a98bc94ad2f1d4d5ae2a25db238a0aff57323014dd2a280d5368e`.

The full result is in `docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_F1_F4_RESULT.md`. V2F5/V2F6 and reserved post-2026-07-31 V2 forward outcomes were not accessed.

## V3-C frozen preregistration identity

Controlling specification:

`docs/RANKING_V3_REGIME_SPEC_V1.md`

- Git blob `2a2f48d68f5d3df839c61191d4a11fa870470b00`.

Independent review addendum:

`docs/RANKING_V3_REGIME_SPEC_REVIEW_ADDENDUM_V1.md`

- Git blob `a13c5ae103908311968e38c6ded233b7a1cbd901`.

Frozen regime definition:

- source context: market breadth-20, market median return-20, market median ATR/close;
- trailing threshold history: prior 252 official sessions, minimum 126 observations;
- stress votes: breadth <= prior q25, return <= prior q25, ATR >= prior q75;
- `STRESS` if at least 2/3 votes, otherwise `NORMAL`;
- regime is a routing variable only, not a model feature.

Frozen architecture:

- exact V2 global control;
- one `NORMAL` exact-V2 HGB expert;
- one `STRESS` exact-V2 HGB expert;
- experts use only exact V2 25 features and frozen HGB parameters;
- no Structure-Lite, recency weighting, rescaling, blending, or fallback during validation.

Implementation lineage before local run:

- `b92cb24367bcc675cd2bfba5bab636d239fa384a` — causal outcome-blind regime builder;
- `89ca64393d94bf294a1d437990242bd5d230c96f` — F1-F4-only cache/runner;
- `7409bfc16914ce487fe39e393f1dd0bf62df4b29` — focused guardrail tests.

Known pre-outcome engineering correction required before local prepare/run: `_context_equivalence` must allow repeated `(signal_session_index,date)` target keys because many securities share one market-wide date context. This is an alignment bug only; the frozen regime/spec/gates must not change. The local run handoff controls the correction before any V3-C outcome is viewed.

Outcome-bearing folds remain V2F1-V2F4 only. V2F5/V2F6 and reserved forward outcomes remain sealed. Ordinals `006` and `007` do not increment the denominator until actually scored.

## Required row schema after execution

Every executed row must record, without deleting prior rows:

`hypothesis_id`, `parent_hypothesis`, `candidate_id`, `candidate_ordinal`, `spec_sha256/spec_blob`, `cache_sha256`, `cache_manifest_sha256`, `fold_set`, `feature_order_hash`, `model_identity`, `result_status`, `result_viewed`, `metrics_artifact`, `artifact_sha256`, `verdict`, `cumulative_candidate_count`, `code_commit`, `environment`, and `notes`.

The counter increments when a candidate is actually run. A failed run with viewed results, killed candidate, or diagnostic candidate stays in the denominator permanently. A pre-score engineering/data/provenance block does not fabricate an evaluated candidate result.