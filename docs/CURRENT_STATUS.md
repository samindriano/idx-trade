# IDX Trade — Current Status

Date: 2026-08-10 (Asia/Jakarta)

This is the authoritative short first-read layer. For chronology use `docs/PROJECT_CONTEXT_MASTER.md`, `docs/PROJECT_LEDGER.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, and the newest dated checkpoint/handoff. If older text conflicts, this file plus the newest controlling checkpoint wins.

## Current phase

- active research branch: `research/idx-ranking-v2-spec-v1`;
- Ranking V1 historical benchmark failed and its consumed holdout is never rerun;
- Ranking V2 frozen control remains exact `HGB_XS_MARKET`;
- Ranking V3 historical-development search is **CLOSED**;
- final V3 historical-development architecture is **`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`**;
- one-shot V2F5/V2F6 late-development confirmation: **PASS**;
- V3-A Recency: killed;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked at `BLOCKED_PIT_SECTOR_HISTORY`, outcomes unconsumed;
- V3-E True Ranking: killed;
- optional V3 integration: skipped because only one independent Tier-1 component survived;
- cumulative evaluated V3 architecture-candidate count remains `9`;
- V3-D ordinals 008/009 remain unviewed;
- V2F5/V2F6 are now consumed exactly once and may not be reused for model selection;
- sessions `1225+` remain outside the consumed late-development confirmation;
- post-2026-07-31 fresh-forward outcomes: **NOT ACCESSED**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **NOT WRITTEN**;
- calibration / Stage 6 / `IDX-VAL-002` / execution-PnL / Kelly / paper/live / main merge: not authorized.

## Frozen V3 conclusion

Final independent review checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_REVIEW_PASS_CLOSED.md`

Late-development result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_RESULT.md`

The defensible V3 conclusion is:

> Adding the frozen compact eight-feature causal Structure-Lite geometry bundle to the exact V2 HGB ranker produced robust incremental historical-development ranking value across discovery folds F1-F4 and reserved late-development folds F5-F6.

This remains a ranking result only. It is not calibrated probability, execution/PnL evidence, live-trading readiness, or independent future validation.

## V3-B historical evidence

### Discovery F1-F4

Paired versus exact V2 control:

- median PR improvement `+0.0039258450`;
- q25 `+0.0026897894`;
- worst `+0.0018412974`;
- PR improvement positive `4/4` folds;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- top-decile lift median change `-0.0036228765` remains a diagnostic warning.

### One-shot late-development F5/F6

Exact control equivalence PASS on `59,491` rows with max score and metric differences `0.0`.

Paired Structure-Lite changes:

- F5 PR `+0.0016661426`, ROC `+0.0026017659`, Q5-Q1 `+0.0215800814`, top-decile lift `+0.0164814105`;
- F6 PR `+0.0135161180`, ROC `+0.0118806168`, Q5-Q1 `+0.0038483525`, top-decile lift `-0.0043770061`;
- median PR improvement `+0.0075911303`, worst `+0.0016661426`;
- median ROC change `+0.0072411913`;
- median Q5-Q1 change `+0.0127142169`, worst `+0.0038483525`;
- absolute gate PASS;
- paired gate PASS;
- final `V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS`.

F6 is especially informative: exact V2 control ROC was `0.4931017075`, while Structure-Lite increased it to `0.5049823243` and also improved PR delta and Q5-Q1. This is useful historical robustness evidence but must not be relabeled independent future validation.

## Frozen data/model identities

Signal-research source:

- window `2021-04-29..2026-07-31`;
- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Immutable V2 prepared cache:

- SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb85cd4823e3?`;

Canonical V2 prepared cache identity remains the one recorded in the frozen V2/V3 checkpoints and hypothesis ledger; use those files rather than manually transcribing a path/hash from memory when running any future task.

Late-development Structure-Lite cache:

- status `RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CACHE_FROZEN`;
- SHA-256 `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- manifest SHA-256 `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`;
- rows/tickers/sessions `286,453 / 737 / 20..1224`;
- no session 1225+ materialized.

## Next research lane

The V3 ranking architecture is now a **fixed benchmark**, not a moving target.

While the separate post-2026-07-31 fresh-forward block accumulates toward its previously frozen independent-validation requirement, active research may continue only on orthogonal lanes that do not alter the V3-B ranker or consume reserved fresh-forward outcomes.

Preferred next lane:

**V4-A Path Risk / Adverse Excursion — SPECIFICATION FIRST.**

Research question:

> Conditional on a setup already ranked by frozen V3-B, can a separate model characterize adverse path risk, drawdown/excursion, time-to-resolution, or related path uncertainty without replacing the opportunity rank?

The first V4-A task must define target(s), path window, censoring/resolution semantics, causal feature boundary, validation design, model/candidate budget, and explicit separation from V3 opportunity ranking before any model is fitted.

Do not use V4-A outcomes to retune or reopen V3-B.

## Immediate next action

Prepare and independently review a V4-A Path Risk specification only. Do not fit/score V4-A until that specification is frozen.

Separately, do not authorize fresh-forward V3 outcome access until the already frozen future-session/maturity requirement is genuinely satisfied and explicitly authorized.

## Hard boundary

Do not:

- reopen/tune V3-A/B/C/E;
- reuse V2F5/V2F6 for candidate selection;
- bypass V3-D PIT sector-history block;
- materialize/score post-2026-07-31 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED` without explicit future authorization;
- conflate V4 path-risk targets with the frozen V3 opportunity score;
- start calibration/Stage 6/`IDX-VAL-002`/execution-PnL/Kelly/paper/live/main automatically.
