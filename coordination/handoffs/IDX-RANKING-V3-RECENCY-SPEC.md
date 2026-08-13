# Handoff — IDX Ranking V3 Recency Specification

Date: 2026-08-10 (Asia/Jakarta)
Status: **AUTHORIZED FOR SPECIFICATION DRAFTING ONLY — NO V3 OUTCOME RUN**

## Required reads

Before changing anything, read and explicitly acknowledge:

1. `docs/CURRENT_STATUS.md`
2. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
3. `docs/RANKING_V3_RESEARCH_BACKLOG.md`
4. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
5. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
6. frozen V2 ranking/forward specification and relevant V2 candidate/validation code needed to preserve semantics
7. newest checkpoint, especially `docs/checkpoints/2026-08-10_RANKING_V3_ROADMAP_AUDIT_FROZEN.md`

## Task

Draft and freeze `docs/RANKING_V3_RECENCY_SPEC_V1.md` only.

The spec must answer exactly one hypothesis:

> Does deterministic recency weighting of training observations improve temporal robustness versus the exact frozen V2 `HGB_XS_MARKET` control while keeping label, universe, features, estimator architecture, scoring semantics, and evaluation semantics otherwise unchanged?

## Required specification content

Freeze before any V3 outcome run:

- exact development-data/cache boundary and hashes;
- exact V2 control identity;
- exact discovery-fold boundaries and purge/maturity semantics;
- explicit reserved late-development confirmation boundary, if retained after code inspection;
- at most two recency variants plus uniform control;
- exact official-session age formula;
- exact sample-weight formula for each variant;
- whether/how weights are normalized and the rationale, including interaction with HGB regularization/weight scale;
- exact estimator/preprocessor semantics inherited unchanged from V2;
- exact feature order (25 V2 features only);
- exact candidate count and no-search rule;
- primary and secondary metrics;
- robustness eligibility/promotion/kill rules;
- deterministic tie rule with simplicity preference;
- hypothesis/candidate ledger schema and cumulative V3 candidate counter;
- runtime/provenance/artifact requirements;
- explicit statement that all pre-2026-07-31 results are development evidence only;
- explicit prohibition on reserved post-2026-07-31 V2 forward outcome access;
- explicit prohibition on V3 fitting/scoring in this task.

## Design constraints

- Do not add features.
- Do not change H10 label semantics.
- Do not change HGB architecture/hyperparameters.
- Do not add another model family.
- Do not grid-search half-lives.
- Do not tune based on viewed fold outcomes.
- Do not inspect or summarize reserved V2 fresh-forward outcomes.
- Do not write `FORWARD_OUTCOME_ACCESS_STARTED`.
- Do not start Stage 6, probability calibration, execution-PnL, paper/live, or main merge.

If a proposed weight normalization could materially alter the intended comparison through effective regularization scale, document the issue and choose/freeze one defensible convention before outcomes. Do not resolve it using model scores.

## Deliverables

1. `docs/RANKING_V3_RECENCY_SPEC_V1.md`
2. dated checkpoint for the frozen spec
3. result handoff summarizing exact choices, hashes/commits, and authorization boundary
4. update continuity docs if needed so the new spec is discoverable

Stop after documentation/specification work. Do not implement candidate fitting or run any V3 score.
