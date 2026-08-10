# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed and its consumed holdout is never rerun;
- Ranking V2 frozen control remains exact `HGB_XS_MARKET`;
- Ranking V3 historical-development architecture search is **CLOSED**;
- final V3 historical-development architecture is `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- V3-B one-shot V2F5/V2F6 late-development confirmation: **PASS**;
- V3-A Recency: killed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked at `BLOCKED_PIT_SECTOR_HISTORY`, outcomes unconsumed;
- V3-E True Ranking: killed;
- V2F1..V2F6 are development knowledge and are not independent V4 holdouts;
- sessions `1225+` remain sealed from V4 historical-development materialization;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

## Frozen V3 conclusion

Final V3 architecture:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

Across V3-B historical-development F1-F6, paired PR improvement versus exact V2 control was positive on all six folds. F1-F4 median paired PR improvement was `+0.0039258450`; F5/F6 median was `+0.0075911303`. This is ranking evidence only, not calibrated probability, execution/PnL evidence, live readiness, or independent future validation.

Key checkpoints:

- `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REVIEW_PASS_CLOSED.md`;
- `docs/checkpoints/2026-08-10_RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_RESULT.md`.

## Frozen data/model identities

Signal-research source:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Frozen V3-B late-development cache used as the V4 base:

- SHA-256 `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- manifest SHA-256 `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`;
- rows/tickers/sessions `286,453 / 737 / 20..1224`;
- no session `1225+` materialized.

## V4 — final alpha program

V4 is the final bounded alpha-generation round before primary attention moves to fresh-forward validation and separate risk/uncertainty/portfolio/execution layers.

Frozen seven-family design arena:

`docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`

Families are a design shortlist, not seven automatic model runs:

1. Liquidity & Participation Quality;
2. Price-Path Quality;
3. Cross-Sectional Opportunity Context;
4. Peer / Sector Relative Strength, conditional on PIT sector history;
5. Systematic-Adjusted / Idiosyncratic Strength;
6. Catalyst / Fundamental Context, conditional on PIT provenance;
7. Flow / Ownership Information, conditional on data readiness.

Normal executable budget remains narrow: one frozen bundle per family, no model zoo, and only preregistered integration after independent survivor evidence.

## Current V4-A family

Family:

`V4-A-PARTICIPATION-V1` — Participation Quality / Price Impact.

Frozen first-pass candidates:

- ordinal `012`: exact V3-B 33-feature control;
- ordinal `013`: V3-B + three-feature A1 Impact/Absorption bundle;
- ordinal `014`: V3-B + four-feature A2 Persistent Directional Participation bundle.

No first-pass A1+A2 integration candidate exists. One integration may be designed later only if both 013 and 014 independently PASS.

Controlling files:

- `docs/RANKING_V4_A_PARTICIPATION_QUALITY_EXPERIMENT_MAP_V1.md`;
- `docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`;
- `docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_REVIEW_ADDENDUM_V1.md`;
- `docs/RANKING_V4_HYPOTHESIS_LEDGER_V1.md`.

## V4-A pre-outcome audit

The outcome-blind cache/data audit completed successfully:

- prepared cache status: `RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME`;
- cache rows/tickers/sessions: `286,453 / 737 / 20..1224`;
- cache SHA-256: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`;
- manifest SHA-256: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`;
- all seven V4-A features finite at least `98.5785%`;
- no constant feature;
- no feature below 80% finite coverage;
- no absolute Spearman correlation `>=0.95`;
- highest absolute correlation: `0.8942494476` between A2 persistence and acceleration;
- `mechanical_review_required=false`;
- official audit did not load `binary_target` or outcome columns;
- no V4-A candidate model/outcome has yet been viewed;
- audit SHA-256: `c89a19d1cce390b4734dc1de8c2cc08994217248478fd2e8025d94e90f93d31a`.

Audit result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_CACHE_AUDIT_RESULT.md`

The high but sub-threshold `0.8942` correlation is retained as documented redundancy inside the already-frozen A2 hypothesis; it is not a specification defect and is not grounds for post-freeze redesign.

## Current authorization

The pre-outcome review is complete and the **one atomic V4-A first-pass historical-development run is now AUTHORIZED**.

Authorization checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RUN_AUTHORIZED.md`

Execution handoff:

`coordination/handoffs/IDX-RANKING-V4-A-PARTICIPATION-FIRST-PASS-RUN.md`

The authorized run is exactly one invocation of exact V3-B control + A1 + A2 across V2F1..V2F6, with mandatory `1e-12` V3-B control equivalence before challenger interpretation and frozen independent PASS/FAIL gates for A1 and A2. There is no mid-run adaptation and no integration execution.

## Immediate next action

Run only the Windows-local procedure in:

`coordination/handoffs/IDX-RANKING-V4-A-PARTICIPATION-FIRST-PASS-RUN.md`

After the run, document/commit/push the result and STOP for ChatGPT review. Do not proceed automatically to integration or V4-B.

## Hard boundary

Do not:

- reopen/tune V3-A/B/C/E;
- treat V2F1..V2F6 as independent V4 validation;
- bypass V3-D PIT sector-history block;
- modify A1/A2 formulas, lookbacks, candidate IDs, model parameters, folds or gates based on V4 outcomes;
- run one challenger and then adapt the other;
- create/run A1+A2 integration before both independently pass and a separate integration spec/review exists;
- materialize/score session `1225+` for V4 development;
- access post-2026-07-31 fresh-forward outcomes or write `FORWARD_OUTCOME_ACCESS_STARTED`;
- begin V4-B automatically after the V4-A run;
- start calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge automatically.
