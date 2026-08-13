# Handoff — IDX Ranking V3-E True-Ranking Specification

Date: 2026-08-10 (Asia/Jakarta)

Status: **SPECIFICATION / DEFINITION AUDIT ONLY — NO OUTCOME RUN AUTHORIZED**

## Context

V3-A Recency is closed without promotion. V3-B Structure-Lite is the only surviving V3 component. V3-C Regime-Specialization is closed without promotion. V3-D Sector-Relative is parked at `BLOCKED_PIT_SECTOR_HISTORY`; ordinals 008/009 remain unviewed and do not count in the evaluated denominator.

The active next Tier-1 hypothesis is V3-E TRUE-RANKING, per `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`.

## Research question

> Does one tightly bounded nonlinear same-date ranking objective outperform the frozen binary HGB ranking score on identical causal rows and V2F1-V2F4 discovery folds?

This lane changes **objective/model formulation only**. It must not simultaneously add Structure-Lite, sector features, regime routing, recency weights, new labels, calibration, or execution logic.

## Mandatory reads

1. `docs/CURRENT_STATUS.md`
2. `docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_BLOCK_REVIEW_PASS_PARKED.md`
3. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
4. `docs/RANKING_V3_RESEARCH_BACKLOG.md`
5. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
6. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
7. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
8. frozen V2 model/feature/fold modules
9. existing pairwise-ranking implementation and historical pairwise results
10. legacy downside-ranking experiment only as failure evidence, not promotion evidence

## Specification task

Produce `docs/RANKING_V3_TRUE_RANKING_SPEC_V1.md` and freeze one tightly bounded nonlinear ranking candidate.

Preferred default formulation:

- exact V2 causal model table and H10 binary target;
- query/group = exact signal date;
- exact V2 25 ordered features only;
- one tree-based pairwise/listwise ranking estimator with deterministic seed and predeclared parameters;
- prediction = raw ranking score, not calibrated probability;
- exact V2F1-V2F4 discovery folds;
- exact V2 `HGB_XS_MARKET` control on identical validation rows.

Do **not** run a ranking library/model tournament. Normally allow exactly one true-ranking candidate plus the control. A second variant requires a strong pre-outcome reason and explicit candidate-budget justification.

## Key definition questions that must be frozen before implementation

The spec must explicitly define:

- chosen ranking objective/library and why it is the smallest defensible nonlinear ranking test;
- date-query grouping semantics;
- handling of dates with class imbalance or all-one/all-zero labels;
- minimum query size if any;
- train-row and validation-row preservation;
- deterministic feature missing-value handling;
- exact estimator parameters and random seed;
- score direction and finite-score contract;
- whether pair weights/label gains are used; default should be none unless required by the chosen objective;
- control-equivalence contract;
- runtime/provenance and artifact hashes;
- no F5/F6/fresh-forward access.

## Evaluation contract

Use the existing V3 absolute sanity + paired promotion gates against exact V2 control unless the ranking estimator requires an additional preregistered ranking-specific guard.

Mandatory diagnostics should include:

- median/q25/worst paired PR-delta improvement;
- positive paired PR folds;
- ROC change;
- Q5-Q1 change;
- top-decile lift change;
- same-date score diversity/tie rate;
- query/date coverage and rows dropped, which should normally be zero;
- F4 behavior;
- overlap/Jaccard of control vs true-ranker top decile.

A ranking-specific candidate may not be promoted merely because a pairwise/listwise training loss improves.

## Candidate accounting

V3-D ordinals 008/009 are reserved but unviewed. Do not silently reuse or renumber them as if they had been evaluated.

The V3-E spec must choose permanent new ordinals after those reserved slots, provisionally 010 control and 011 true-ranking candidate, and state clearly that cumulative evaluated count remains 7 until V3-E is actually run.

## Hard prohibitions

Do not:

- score V3-E during this task;
- add Structure-Lite to the V3-E discovery candidate;
- use V3-D sector features;
- reopen/tune V3-A/C;
- run multiple ranker libraries/objectives after seeing results;
- change H10 target/universe/folds;
- access V2F5/V2F6;
- access reserved post-2026-07-31 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start integration, calibration, Stage 6, IDX-VAL-002, execution/PnL, Kelly, paper/live, or main merge.

## Stop condition

Commit/push only the frozen V3-E spec, review checkpoint/handoff/ledger preregistration needed for continuity, then STOP for independent review before implementation or scoring.
