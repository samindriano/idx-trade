# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed and its consumed holdout is never rerun;
- Ranking V2 historical champion/control: exact `HGB_XS_MARKET`;
- Ranking V3 architecture search: **CLOSED**;
- final historical-development ranker: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- V3-B one-shot V2F5/V2F6 late-development confirmation: **PASS**;
- V3-A Recency: killed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked `BLOCKED_PIT_SECTOR_HISTORY`, outcomes unconsumed;
- V3-E True Ranking: killed;
- V4 final alpha-generation program: **CLOSED — NO SURVIVOR**;
- cumulative historical evaluated-candidate count: `17`;
- final V3-B refit / fresh-forward specification: **FROZEN + REVIEW PASS**;
- final V3-B refit/runtime: **FROZEN SUCCESSFULLY, NO PERFORMANCE METRICS COMPUTED**;
- Path Risk V1 implementation + feature cache: **FROZEN PRE-OUTCOME; PR-001 UNVIEWED**;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

## Final historical ranker

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

It is exact V2 `HGB_XS_MARKET` information plus eight frozen causal Structure-Lite geometry features. Across V3-B F1-F4, median paired PR improvement versus V2 was `+0.0039258450`; the one-shot F5/F6 late-development confirmation passed with median paired PR improvement `+0.0075911303`.

This is historical-development ranking evidence only. It is not calibrated probability, execution/PnL evidence, live readiness, or independent future validation.

Frozen signal-research identities:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Frozen V2 resolved-primary-H10 prepared cache for the final fit:

- cache SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- rows/tickers/sessions `292,633 / 737 / 20..1250`.

Final V3-B refit/runtime result:

- execution code HEAD `56e6aa43d318775a5abcf73c87401fafde993b82`;
- status `RANKING_V3_B_FINAL_REFIT_FROZEN`;
- final training table: `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_b_final_refit_20260810_001\ranking_v3_b_structure_lite_final_training_table.parquet`;
- training table SHA-256 `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe`;
- model SHA-256 `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`;
- model manifest SHA-256 `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9`;
- summary SHA-256 `e8e42dec10c73257fe4776f682f55d146ed8ca49b4aed7ce63ddb7488419e6a0`;
- `verify_final_v3_refit_artifacts`: `valid=true`;
- historical performance metrics: not computed; sessions `1225..1250` were training-only;
- fresh-forward outcomes: not accessed; `FORWARD_OUTCOME_ACCESS_STARTED`: not written.

Controlling checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REFIT_RUNTIME_RESULT.md`

## Path Risk V1

The separate Path Risk lane is implemented and its real outcome-blind discovery
feature cache is frozen through signal session `984`.

- hypothesis: `PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1`;
- reserved candidate: `PATH-RISK-A-Q75-HGB-001`;
- implementation: `src/idx_trade/path_risk_v1.py` and
  `src/idx_trade/path_risk_v1_prepare.py`;
- cache status: `PATH_RISK_V1_DISCOVERY_FEATURE_CACHE_FROZEN_PRE_OUTCOME`;
- cache rows/tickers/dates/sessions: `254,383 / 679 / 965 / 20..984`;
- primary-liquid count per date: `222 / 258 / 307` min/median/max;
- cache SHA-256 `74c300390dce542dad95ae204dd7663f5f780b09dd33c3514c5dd264f15cca08`;
- manifest SHA-256 `054ccff7676a744871b1f82a5b263898f9fa53c2d1ae1ac20a5659485466bed0`;
- audit SHA-256 `1bb6fecbae1733f7ab62022c5f50389ffdd2bfe1dcc68f98c9853c9d123d2807`;
- exact 33-feature order SHA-256 remains
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- infinity cells `0`; constant/all-null features `0/0`;
- real H10 labels, real Path Risk targets, PR-001, performance metrics, F5/F6,
  and fresh-forward outcomes: not accessed.

Controlling checkpoint:

`docs/checkpoints/2026-08-10_PATH_RISK_V1_DISCOVERY_CACHE_AUDIT_RESULT.md`

## V4 final alpha review — CLOSED

Controlling review:

`docs/checkpoints/2026-08-10_RANKING_V4_FINAL_ALPHA_REVIEW_CLOSED.md`

V4-A:

- `012` exact control: equivalence PASS;
- `013` Impact/Absorption: FAIL;
- `014` Persistent Directional Participation: FAIL.

V4-B:

- `015` exact control: equivalence PASS;
- `016` Path Coherence / Jump Concentration: FAIL;
- `017` Range Acceptance / Rejection: FAIL.

V4-C:

- `018` exact control: equivalence PASS;
- `019` Cross-Sectional Dispersion: FAIL.

No V4 survivor, B1+B2 integration, B/C integration, rescue, threshold relaxation, or additional post-result market-derived alpha family is authorized.

Ordinal `017` had positive aggregate diagnostics but failed temporal robustness/late-fold protection. Ordinal `019` is not treated as an almost-pass: besides missing the median PR threshold, it failed multiple q25/worst/ROC/Q5-Q1/late-fold gates. Failed candidates remain permanently in the denominator.

The frozen seven-family V4 arena was a shortlist, not seven automatic runs. The three planned main families have now been consumed. Peer/Sector remains PIT-data blocked; Fundamental/Catalyst and Flow/Ownership lack frozen admissible PIT data gates. Systematic-adjusted strength remains a future idea rather than an outcome-responsive fourth V4 run.

## V3-D PIT sector history

Status remains `BLOCKED_PIT_SECTOR_HISTORY`.

No complete immutable ticker-by-date IDX-IC source chain with defensible `effective_from`, `effective_to_exclusive`, and `available_at` was established. `validate-history` and V3-D `prepare` were not run; ordinals `008/009` remain unviewed.

Controlling checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PIT_DATA_GATE_BLOCKED_RERUN.md`

## Final V3-B refit / forward contract

Frozen specification:

`docs/RANKING_V3_FINAL_FORWARD_SPEC_V1.md`

Spec Git blob:

`024f1919de8d5ea4e2e9933a9e4c1a1ef9bbe4f4`

Review checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_FORWARD_SPEC_REVIEW_PASS.md`

Exact 33-feature order SHA-256:

`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`

Implemented pre-outcome runtime:

- `src/idx_trade/ranking_v3_forward_runtime.py`;
- `tests/test_ranking_v3_forward_runtime.py`.

The local Windows task must now run full pytest, verify frozen source/cache/spec identities, build the exact 292,633-row V3-B training table, fit the exact model once, and freeze/hash the model + manifest. It must compute **no historical performance metric** and must stop before any real fresh-forward outcome access.

Sessions `1225..1250` may participate only in this final training refit after architecture closure. They may not become another validation slice.

## Fresh-forward independent verdict

The first independent final-ranker verdict is frozen to the first exact **100 consecutive H10-mature official signal sessions strictly after 2026-07-31**.

The PASS/MIXED/FAIL semantics reuse the already-frozen V2 fresh-forward rule unchanged. No shorter interim verdict, rolling peek, alternate block, V2 fallback selection, or post-result rescue is allowed.

Because the current date is 2026-08-10, that 100-session H10-mature block cannot yet exist. No real forward access is authorized now.

Before future outcome access, the exact block and immutable source snapshots must be hash-pinned in a pre-outcome manifest, then the global `FORWARD_OUTCOME_ACCESS_STARTED` marker must be atomically written before labels/outcomes are loaded. A crash after the marker consumes the block.

## Immediate next action

Stop for ChatGPT review of the frozen Path Risk feature-only cache. A separate
authorization is required before loading the real H10 labels, constructing
adverse-excursion targets, fitting PR-001, or viewing any Path Risk outcome.
Any future fresh-forward work also requires its separately authorized
pre-outcome manifest and atomic outcome-access step.

## Hard boundary

Do not:

- reopen V3/V4 architecture selection;
- rescue V4-A/B/C or add a fourth V4 market-derived family after the viewed failures;
- bypass the V3-D PIT sector-history block;
- inspect sessions `1225..1250` as a validation slice;
- inspect or summarize post-2026-07-31 fresh-forward labels/outcomes;
- load the real H10 label parquet or compute real adverse-excursion targets;
- fit PR-001 or compute real Path Risk pinball/Spearman/quintile metrics;
- access Path Risk F5/F6 outcomes or create a risk-veto/integration rule;
- write the real `FORWARD_OUTCOME_ACCESS_STARTED` marker now;
- change the 33-feature ranker, model parameters, labels, universe, or fresh-forward verdict rule;
- start calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge automatically.
