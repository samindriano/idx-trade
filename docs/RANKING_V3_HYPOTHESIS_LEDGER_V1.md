# Ranking V3 Hypothesis Ledger V1

Status: **V3-A COMPLETE/KILLED; V3-B COMPLETE/PROMOTED; V3-C COMPLETE/KILLED; V3-D AMENDED PRE-OUTCOME/NOT RUN; 7 CANDIDATES EVALUATED**

All results through V2F1-V2F4 are historical-development evidence only. The cumulative evaluated counter is `7`.

Ordinals `001`-`007` have been viewed. Ordinals `008`-`009` remain unviewed and are not counted. Pre-score engineering/data/provenance blocks do not increment the denominator.

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 001 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-CONTROL-001` | exact uniform V2 `HGB_XS_MARKET` control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 002 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL252-002` | normalized exponential decay H=252 | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 003 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL504-003` | normalized exponential decay H=504 | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 004 | `V3-B-STRUCTURE-LITE-V1` | `V3-B-STRUCTURE-LITE-V1-CONTROL-004` | exact V2 control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 005 | `V3-B-STRUCTURE-LITE-V1` | `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` | V2 25 + fixed 8-feature causal geometry bundle | `COMPLETE` | `true` | `PROMOTE_FOR_NEXT_RESEARCH_STEP` |
| 006 | `V3-C-REGIME-V1` | `V3-C-REGIME-V1-CONTROL-006` | exact V2 control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 007 | `V3-C-REGIME-V1` | `V3-C-REGIME-V1-TWO-EXPERT-007` | frozen NORMAL/STRESS two-expert architecture | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 008 | `V3-D-SECTOR-RELATIVE-V1` | `V3-D-SECTOR-RELATIVE-V1-CONTROL-008` | exact V2 control | `AMENDED_IMPLEMENTED_NOT_RUN` | `false` | `BLOCKED_PENDING_PIT_SECTOR_GATE` |
| 009 | `V3-D-SECTOR-RELATIVE-V1` | `V3-D-SECTOR-RELATIVE-V1-CANDIDATE-009` | V2 25 + fixed 6-feature PIT sector-relative bundle | `AMENDED_IMPLEMENTED_NOT_RUN` | `false` | `BLOCKED_PENDING_PIT_SECTOR_GATE` |

## V3-A Recency — executed identity

- run/source commit `362510997e3db41e81b21ec8e7422308338fbef1`;
- implementation commit `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`;
- spec SHA-256 `53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa`;
- V2 prepared cache SHA `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- control equivalence PASS on 84,732 F1-F4 rows, max diff `0.0`;
- H252/H504 both failed paired promotion;
- result `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.

No recency component survives. No new half-life/window rescue is allowed.

## V3-B Structure-Lite — executed identity

Controlling spec: `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`.

- spec SHA-256 `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- spec Git blob `0392ab506aa451355697327d416f8f2b2ea21d4f`;
- review-addendum Git blob `717871707e833ab9818c249d52aae5b234334fc4`;
- run HEAD `eee4ed0458fdfdea5fdc0f5335ec211efd3dd80b`;
- full pytest `252 passed, 0 failed, 3 warnings`;
- cache SHA `7084759fddaa20e82ec03e50205f2872520e6b3e11ea5f294033589a9c803405`;
- manifest SHA `e428cad0ff24b57977106482cef1478e60c0660adcee6dbf103803516b35aeb2`;
- control equivalence PASS on 84,732 rows, max diff `0.0`;
- median paired PR improvement `+0.0039258450`, q25 `+0.0026897894`, worst `+0.0018412974`, better `4/4`;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- median top-decile lift change `-0.0036228765` retained as warning;
- result `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`.

V3-B is the only surviving V3 component so far. Its viewed definition is closed.

## V3-C Regime — executed identity

Controlling spec: `docs/RANKING_V3_REGIME_SPEC_V1.md`.

- spec Git blob `2a2f48d68f5d3df839c61191d4a11fa870470b00`;
- review-addendum Git blob `a13c5ae103908311968e38c6ded233b7a1cbd901`;
- run/code commit `619b511f14d8e929f8f23ed7c001f72fe730566f`;
- V3-C run-tree pytest `264 passed, 0 failed, 3 warnings`;
- final merged-tree validation after concurrent V3-D engineering `277 passed, 0 failed, 3 warnings`;
- cache SHA `1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`;
- manifest SHA `c4b090de65c291af21ea0a49f63d5d2d0dc1acbd18fff1c995494e1212f1418b`;
- rows/tickers/sessions `216,472 / 674 / 20..984`;
- fragmentation gate PASS F1-F4;
- control equivalence PASS on 84,732 rows, max diff `0.0`;
- candidate absolute sanity PASS;
- overall paired promotion FAIL;
- regime robustness FAIL;
- overall median PR improvement `-0.0123171892`;
- NORMAL median PR improvement `-0.0014712226`;
- STRESS median PR improvement `-0.0289646749`;
- worst fold/state PR improvement `-0.0372442541`;
- result `V3_C_REGIME_KILL_KEEP_V2_CONTROL`.

The two-expert architecture is closed. No threshold/expert/blending/rescaling rescue is authorized.

## V3-D Sector-Relative — final pre-outcome identity

Base spec:

`docs/RANKING_V3_SECTOR_RELATIVE_SPEC_V1.md`

Initial review addendum:

`docs/RANKING_V3_SECTOR_RELATIVE_SPEC_REVIEW_ADDENDUM_V1.md`

The one allowed post-V3-C amendment has now been exercised and frozen:

`docs/RANKING_V3_SECTOR_RELATIVE_POST_V3C_AMENDMENT_V1.md`

Review checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_REGIME_REVIEW_PASS_V3D_AMENDED.md`

### Candidate definition — unchanged

Ordinal 009 remains exact V2 25 features plus:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

One global HGB only. No Structure-Lite or regime state is a model feature. No regime expert/router is used.

### Implementation lineage

- `670a4cbc7c9fdc98eb3d82dfc336a7b23624d8a0` — provisional V3-D spec baseline;
- `ae8dcfe91e4656d4f8536d0fcf1f7fd7575ecb92` — PIT sector validator/assignment/features;
- `ca658e13d0d3ad4333820cab7ba9d2ef766c8ffc` — cache/base runner/sector diagnostics;
- `28981a25a427f67db0fc940415d0d7c910a9ff84` — focused PIT/run guards;
- `600c439c42e2a4452859ea7354e41d246db1e42e` — pre-outcome PIT/schema/dtype hardening;
- `055cca747d5ee0ecc3209b8b0efb36dcf25ddd5d` — pre-outcome review addendum;
- `775c447e4e685420f7d5f62ac39483e702126efe` — post-V3-C amendment frozen;
- `1f5ec6ec24b53e5e66ceb20b8ecbf50123f5cf3e` — amended regime robustness wrapper;
- `59a9b47e9c47c2baa7c83c97e147c5e2da7dde05` — amendment guard tests;
- `4fd37155e617093cb557cb0a53a983983f28b93a` — V3-C review / V3-D amendment checkpoint.

### Post-V3-C evaluation guard

The exact frozen V3-C regime cache is pinned by SHA:

`1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`

It is evaluation metadata only.

Final V3-D promotion requires original data/control/absolute/paired gates plus:

- NORMAL median paired PR improvement >= `-0.005`;
- STRESS median paired PR improvement >= `-0.005`;
- NORMAL/STRESS median ROC change each >= `-0.005`;
- NORMAL/STRESS median Q5-Q1 change each >= `-0.005`;
- worst fold/state PR improvement >= `-0.015`.

Top-decile lift remains diagnostic only.

### Current blocker

A real point-in-time historical sector artifact has not yet passed provenance and coverage gates.

Required fields: `ticker`, `sector_code`, `effective_from`, `effective_to_exclusive`, `available_at`, `source_id`, `source_sha256`.

Current-sector backfill is prohibited. Every source hash must be independently evidenced against immutable source bytes or a trusted immutable archive identity.

No `V3_D_OUTCOME_RUN_AUTHORIZED` JSON exists. Ordinals 008/009 remain unviewed.

## Required row schema after future execution

Every executed row must record:

`hypothesis_id`, `parent_hypothesis`, `candidate_id`, `candidate_ordinal`, `spec/amendment identity`, `cache_sha256`, `cache_manifest_sha256`, `fold_set`, `feature_order_hash`, `model_identity`, `result_status`, `result_viewed`, `metrics_artifact`, `artifact_sha256`, `verdict`, `cumulative_candidate_count`, `code_commit`, `environment`, and `notes`.

The counter increments only when a candidate is actually run. A killed/viewed candidate remains in the denominator permanently; a pre-score data/provenance block does not.
