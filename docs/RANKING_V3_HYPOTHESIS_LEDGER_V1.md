# Ranking V3 Hypothesis Ledger V1

Status: **V3-A COMPLETE; V3-B PROMOTED; V3-C COMPLETE / KILLED KEEP V2 CONTROL; V3-D PROVISIONALLY IMPLEMENTED / NOT AUTHORIZED; 7 CANDIDATES EVALUATED**

All pre-2026-07-31 results in this ledger are historical-development evidence, not independent validation. The cumulative evaluated counter is currently `7`.

Ordinals `001`-`007` have been viewed. Provisional ordinals `008`-`009` remain unviewed and are not counted. Pre-score engineering/data/provenance blocks do not fabricate evaluated candidates.

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 001 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-CONTROL-001` | exact uniform V2 `HGB_XS_MARKET` control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 002 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL252-002` | normalized exponential decay, H=252 official sessions | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 003 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL504-003` | normalized exponential decay, H=504 official sessions | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 004 | `V3-B-STRUCTURE-LITE-V1` | `V3-B-STRUCTURE-LITE-V1-CONTROL-004` | exact frozen V2 `HGB_XS_MARKET` control on V2F1-V2F4 | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 005 | `V3-B-STRUCTURE-LITE-V1` | `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` | exact V2 25-feature prefix + fixed eight-feature causal Structure-Lite bundle | `COMPLETE` | `true` | `PROMOTE_FOR_NEXT_RESEARCH_STEP` |
| 006 | `V3-C-REGIME-V1` | `V3-C-REGIME-V1-CONTROL-006` | exact frozen V2 `HGB_XS_MARKET` control on V2F1-V2F4 | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 007 | `V3-C-REGIME-V1` | `V3-C-REGIME-V1-TWO-EXPERT-007` | one frozen NORMAL/STRESS two-expert architecture using exact V2 25 features | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 008 | `V3-D-SECTOR-RELATIVE-V1` | `V3-D-SECTOR-RELATIVE-V1-CONTROL-008` | exact V2 `HGB_XS_MARKET` control; provisional V3-D slot | `PROVISIONAL_IMPLEMENTED_NOT_RUN` | `false` | `BLOCKED_PENDING_V3_C_AND_SECTOR_GATE` |
| 009 | `V3-D-SECTOR-RELATIVE-V1` | `V3-D-SECTOR-RELATIVE-V1-CANDIDATE-009` | exact V2 25 features + fixed six-feature PIT sector-relative bundle | `PROVISIONAL_IMPLEMENTED_NOT_RUN` | `false` | `BLOCKED_PENDING_V3_C_AND_SECTOR_GATE` |

## V3-A executed result identity

- parent: `RANKING_V2_HGB_XS_MARKET`;
- run/source commit: `362510997e3db41e81b21ec8e7422308338fbef1`;
- implementation commit: `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`;
- spec SHA-256: `53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa`;
- prepared cache SHA-256: `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- prepared manifest SHA-256: `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- fold set: `V2F1-V2F4` only;
- feature-order hash: `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72`;
- model: exact V2 `HGB_XS_MARKET`, seed 42;
- metrics SHA-256: `fe22292ebad0d553042eb8f48faf3ddb13584e8062776a46d63adfd55bf8c603`;
- deterministic result: `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.

No recency component survives. Do not rescue with new half-lives/window/weight clipping.

## V3-B executed result identity

Controlling spec: `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`.

- reported spec SHA-256 `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- spec Git blob `0392ab506aa451355697327d416f8f2b2ea21d4f`;
- review-addendum Git blob `717871707e833ab9818c249d52aae5b234334fc4`;
- source/run HEAD `eee4ed0458fdfdea5fdc0f5335ec211efd3dd80b`;
- full pytest `252 passed, 0 failed, 3 warnings`;
- cache SHA-256 `7084759fddaa20e82ec03e50205f2872520e6b3e11ea5f294033589a9c803405`;
- cache manifest SHA-256 `e428cad0ff24b57977106482cef1478e60c0660adcee6dbf103803516b35aeb2`;
- control equivalence PASS on 84,732 rows, max score/metric diff `0.0`;
- paired median PR improvement `+0.0039258450`, q25 `+0.0026897894`, worst `+0.0018412974`, positive `4/4`;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`, nonnegative `4/4`;
- median top-decile lift change `-0.0036228765` retained as diagnostic warning;
- metrics SHA-256 `0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357`;
- summary SHA-256 `a8ca2fea755a98bc94ad2f1d4d5ae2a25db238a0aff57323014dd2a280d5368e`;
- deterministic result `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`.

V3-B is a surviving component. Its viewed feature/parameter definitions are closed.

## V3-C frozen preregistration identity

Controlling spec: `docs/RANKING_V3_REGIME_SPEC_V1.md`.

- spec Git blob `2a2f48d68f5d3df839c61191d4a11fa870470b00`;
- review-addendum Git blob `a13c5ae103908311968e38c6ded233b7a1cbd901`;
- causal context: breadth-20, market median return-20, market median ATR/close;
- threshold history: prior 252 official sessions, minimum 126 observations;
- STRESS votes: breadth<=q25, return<=q25, ATR>=q75; >=2 votes = STRESS;
- architecture: exact V2 global control vs NORMAL/STRESS exact-V2 HGB experts;
- regime is routing metadata only, not model feature;
- no Structure-Lite/recency/rescaling/blending/fallback.

Implementation lineage:

- `b92cb24367bcc675cd2bfba5bab636d239fa384a` — regime builder;
- `89ca64393d94bf294a1d437990242bd5d230c96f` — cache/runner;
- `7409bfc16914ce487fe39e393f1dd0bf62df4b29` — focused tests;
- `9c94678b970c271b6a9f85c8943e719a5b651bff` — repeated market-context target-key fix + expert class guards;
- `3406f835d9d6573bf320daee1edb058e14b1dd77` — regression coverage for repeated market dates.

The previously noted context-alignment engineering bug is fixed pre-outcome. The
authoritative V3-C result is recorded below and in the dated checkpoint and
result handoff.

## V3-D provisional preregistration identity

Provisional spec: `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_V1.md`.

Pre-outcome review addendum: `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_REVIEW_ADDENDUM_V1.md`.

Implementation checkpoint: `docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PROVISIONAL_IMPLEMENTED.md`.

Six provisional features:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

Implementation lineage:

- `670a4cbc7c9fdc98eb3d82dfc336a7b23624d8a0` — pre-outcome V3-D spec baseline;
- `ae8dcfe91e4656d4f8536d0fcf1f7fd7575ecb92` — PIT sector validator/assignment/features;
- `ca658e13d0d3ad4333820cab7ba9d2ef766c8ffc` — F1-F4-only cache, guarded runner, diagnostics;
- `28981a25a427f67db0fc940415d0d7c910a9ff84` — focused tests;
- `600c439c42e2a4452859ea7354e41d246db1e42e` — pre-outcome validation/schema/dtype hardening;
- `055cca747d5ee0ecc3209b8b0efb36dcf25ddd5d` — independent pre-outcome review addendum;
- `1f49929b67c87e5f86e0a28eb0f512c540c97ecb` — provisional implementation checkpoint.

Outcome-bearing folds remain V2F1-V2F4 only. V2F5/V2F6 and reserved forward outcomes remain sealed.

## V3-C executed result identity

- run/code commit: `619b511f14d8e929f8f23ed7c001f72fe730566f`;
- full IDX Trade pytest: `264 passed, 0 failed, 3 warnings`;
- cache SHA-256: `1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`;
- cache manifest SHA-256: `c4b090de65c291af21ea0a49f63d5d2d0dc1acbd18fff1c995494e1212f1418b`;
- rows/tickers/session range: `216,472 / 674 / 20..984`;
- fragmentation gate: PASS on V2F1-V2F4;
- control equivalence: `V3_C_CONTROL_EQUIVALENCE_PASS`, `84,732` rows, all max score/metric diffs `0.0` at `1e-12`;
- candidate absolute sanity: PASS;
- overall paired promotion: FAIL;
- regime-specific robustness: FAIL;
- deterministic result: `V3_C_REGIME_KILL_KEEP_V2_CONTROL`;
- candidate verdict: `KEEP_DIAGNOSTIC`;
- cumulative candidate count: `7`.

Aggregate paired diagnostics:

- overall median PR-delta improvement `-0.0123171892`, q25 `-0.0156725256`, worst `-0.0221428730`, PR not below control `1/4`;
- overall median ROC change `-0.0087919123`, median Q5-Q1 change `-0.0207539272`, Q5-Q1 not below control `0/4`;
- NORMAL median PR-delta improvement `-0.0014712226`, nonnegative folds `2/4`, median ROC change `-0.0086442462`, median Q5-Q1 change `-0.0146909836`;
- STRESS median PR-delta improvement `-0.0289646749`, nonnegative folds `1/4`, median ROC change `-0.0268295350`, median Q5-Q1 change `-0.0357468445`;
- worst fold-regime PR-delta improvement `-0.0372442541`.

Artifact hashes are recorded in the dated checkpoint and result handoff. The
two-expert candidate is closed; no rescue, second variant, threshold change,
score alignment, blending, or Structure-Lite inheritance is authorized under
this hypothesis.
V3-D hard prerequisite remains a real point-in-time historical sector artifact with effective dates, availability dates, and independently verified source-document/snapshot hashes. Current-sector backfill is prohibited.

The implemented `run` path requires a separate `V3_D_OUTCOME_RUN_AUTHORIZED` JSON pinning V3-C review, final spec, cache, manifest, and implementation identity. No such authorization exists. Therefore ordinals 008/009 cannot be accidentally outcome-scored under the controlling process.

One outcome-blind V3-D amendment is allowed after V3-C review and before any V3-D outcome access. Preferred scope is regime-stratified diagnostics/guardrails if V3-C reveals useful state dependence; do not silently inherit V3-C experts because integration is a separate hypothesis.

## Required row schema after execution

Every executed row must record, without deleting prior rows:

`hypothesis_id`, `parent_hypothesis`, `candidate_id`, `candidate_ordinal`, `spec_sha256/spec_blob`, `cache_sha256`, `cache_manifest_sha256`, `fold_set`, `feature_order_hash`, `model_identity`, `result_status`, `result_viewed`, `metrics_artifact`, `artifact_sha256`, `verdict`, `cumulative_candidate_count`, `code_commit`, `environment`, and `notes`.

The counter increments when a candidate is actually run. A failed run with viewed results, killed candidate, or diagnostic candidate stays in the denominator permanently. A pre-score engineering/data/provenance block does not fabricate an evaluated candidate result.
