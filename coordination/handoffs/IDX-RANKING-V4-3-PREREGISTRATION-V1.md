# V4-3 preregistration handoff

Date: 2026-08-17 (Asia/Jakarta)
Owner: `ChatGPT/V4-3-Preregistration`
Branch: `research/idx-ranking-v4-3-preregistration-v1`
Scientific parent: `review/idx-v4-target-support-census-acceptance-v1@34fc78fa6234cdcc5093e8c4ea36a444b358cec7`
Status: `ACTIVE_OUTCOME_BLIND_PREREGISTRATION`

## Scope

Freeze the initial V4 universe, validation/fold-selection policy, control, one challenger, learner/preprocessing policy, paired comparison rules, and numerical promotion thresholds before any V4 historical target value, model fit, prediction, IC, or performance result is materialized.

The lane may implement outcome-blind support/fold materialization tooling and restore exact provenance bytes. It may not inspect `R5`, `R10`, target ranks, model predictions, IC, Top-30 performance, raw-return diagnostics, protected/fresh-forward outcomes, or any result-derived alternative configuration.

## Non-collision check

Latest canonical `main:coordination/TEAM_STATUS.md` was read before branch creation. Existing V4 target-support lanes are `REVIEW`; no V4-3 preregistration/model-family lane was present. The canonical ledger is not safely patchable through the current GitHub connector without replacing the full ~90 KB shared file; the eventual bounded local materialization step must refetch `origin/main` and add/update the V4-3 row before execution. No other lane is to be overwritten.

## Planned boundary

1. Restore the exact historical `SIGNAL_RESEARCH_HLCV_CONTRACT.md` bytes by pinned Git identity; no semantic edits.
2. Freeze the primary-liquid decision universe and one shared validation-date policy.
3. Freeze V4 Control and exactly one initial challenger.
4. Freeze target-rank normalization, training weights, preprocessing, learner family/configuration, bootstrap implementation, and promotion gates.
5. Implement an outcome-blind primary-liquid support/fold materializer.
6. Stop before target materialization/model fitting until the exact small fold-identity artifacts are hash-pinned.
