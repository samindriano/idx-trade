# V4-X critical alpha audit — start

Date: 2026-08-19 (Asia/Jakarta)
Branch: `research/v4x-critical-alpha-audit-v1`
Base: `research/idx-ranking-v4-3r-ca80-prereg-v1`
Status: `ACTIVE_INDEPENDENT_ADVERSARIAL_REVIEW`
Owner: `ChatGPT/V4X-Critical-Alpha-Audit`

## Scope

Independent red-team audit of the V4-3R Geometry3 historical alpha evidence carried into V4-X/V4-X1. The purpose is to find critical errors that could invalidate or materially inflate the reported historical rank IC before further scientific or production work.

Audit targets:

1. feature-time causality and future mutation invariance;
2. fold construction, training/validation separation, H5/H10 target overlap, and purge sufficiency;
3. cross-sectional normalization and target-rank construction;
4. preprocessing/imputation leakage across validation folds;
5. primary-liquid universe and listing-domain PIT semantics;
6. accepted Open / Geometry3 timing semantics;
7. target entry/terminal indexing and corporate-action continuity semantics;
8. missing-target / observability conditioning and possible selection bias;
9. scoring/evaluation identity alignment and duplicate/misalignment failure modes;
10. historical runner integrity, frozen artifact/hash enforcement, and any hidden reuse of validation outcomes.

## Boundaries

This audit does not rerun the consumed V4-3R historical experiment, does not change model features/learner/hyperparameters/targets/gates, does not access protected fresh-forward outcomes, and does not modify V4-X1 frozen model bytes.

Synthetic/unit/adversarial tests may be added when they test code semantics without touching consumed historical outcomes. Any critical finding will be documented before further forward-model integration work.

Canonical `main:coordination/TEAM_STATUS.md` is stale as of 2026-08-16 and shared-file replacement is unsafe from this branch; this branch/checkpoint is the explicit lane claim for the user-authorized independent adversarial review.