# Ranking V4 Target-Support Census — Open-Lineage Remediation Prep

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-v4-target-support-census-remediation-v1`
Parent result: `research/idx-v4-target-support-census-v1@5f3c2d7b66cf66b2676ba0a409cdc2f4c9ca8f5d`
Status: `PREPARED_FOR_EXACT_OFFLINE_RERUN_PRIOR_BLOCKED_VERDICT_NOT_DECISION_VALID`

## Review finding

The prior `V4_TARGET_SUPPORT_BLOCKED_6X100_INFEASIBLE` result is not accepted for scientific decision use.

The census pinned the immutable signal panel (`67d3d2...`) and computed `base_open_support` directly from that panel, then added only the 2,184-row CA-scale overlay. It did **not** consume the already accepted Yahoo + TradingView Open derivative:

- `execution_open_candidate_panel_yahoo_tradingview.parquet`
- SHA-256 `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab`
- accepted Open coverage in its parent checkpoint: 938,139 / 981,940 = 95.5393%
- artifact-manifest SHA-256 `1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14`

That omission explains why the prior census reported only ~54% Open(t+1) support despite the accepted historical Open lineage already being near 95.5% at the same panel denominator.

This is an objective input-lineage implementation error, not a model/target/evaluator rescue. Correcting it and rerunning the unchanged outcome-blind support contract is scientifically permitted.

## Contract clarification

The locked V4-2 contract says each validation fold spans **100 consecutive eligible signal sessions**. Therefore technical six-by-100 feasibility is based on the ordered filtered eligible-session sequence. Official-calendar adjacency remains a useful diagnostic but is not a separate 600-calendar-session requirement.

Dates below the locked 90% observability gate stay visible in the full census and are excluded from the relevant eligible-session sequence exactly as V4-2 states.

The remediation does not yet force H5, H10, and consensus to share one identity list. It emits all three lists and tests each for >=600 eligible sessions; the final shared-vs-separate fold identity choice remains a pre-outcome V4-3 preregistration decision.

## Implementation prepared

`scripts/run_v4_target_support_census.py` now:

1. pins the accepted Yahoo + TradingView derivative panel and its immutable manifest;
2. requires exact one-to-one ticker/date identity with the immutable 981,940-row signal panel;
3. derives Open support from positive finite derivative Open values;
4. applies the verified CA-scale overlay only on derivative rows that are still missing Open;
5. rejects duplicate/out-of-panel overlay identities and never infers a factor or synthetic Open;
6. preserves immutable-panel, accepted-derivative, and final-overlay Open support separately for diagnostics;
7. emits H5, H10, and consensus eligible-session identities separately;
8. computes the six-by-100 support verdict dynamically instead of hard-coding `BLOCKED`.

Focused tests were added for derivative-first / incremental-overlay precedence and identity-mismatch rejection.

## Runtime boundary

The authoritative derivative and overlay parquet bytes live under the user's external Windows artifact roots and are not available to this GitHub-connected ChatGPT runtime. Therefore the exact census has **not** been rerun here and no replacement support counts are claimed yet.

The next action is one exact offline execution using the pinned external roots, with no provider/network call, no labels/outcomes, no model fit, no V4 contract changes, and a fresh immutable output directory. The prior 264-date result must not be used for V4 feasibility decisions after this finding.
