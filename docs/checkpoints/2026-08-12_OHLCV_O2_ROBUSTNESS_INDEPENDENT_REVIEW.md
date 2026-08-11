# OHLCV O2 Robustness — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-robustness-v1`
Reviewed runtime HEAD: `199524f6bec44f01a00c8991f8369023ce44e9f2`
Decision: `O2_ROBUSTNESS_ACCEPTED_MINIMALITY_AUDIT_AUTHORIZED`

## Independent review verdict

The read-only robustness/provenance audit is accepted.

Accepted facts:

- exact common-support identity remained `278,168` rows;
- persisted O2 fold/aggregate metrics reproduced to numerical precision below `1e-16`;
- all geometry bounds and finite-value checks passed;
- the exact algebraic relation among `open_position`, `open_to_high`, and `open_to_low` was verified on all common-support rows with no tolerance violations;
- Open provenance composition was explicit and complete;
- excluding all `ZAPI_TRADINGVIEW` rows retained positive O2-vs-baseline paired PR-AUC uplift in all `6/6` folds;
- excluding all Yahoo split-scale reconstructed rows also retained positive uplift in all `6/6` folds;
- historical year diagnostics remained positive in 2023, 2024, 2025, and historical 2026 development rows;
- no model retraining, provider call, fresh-forward outcome access, final refit, or tuning occurred.

The small Yahoo split-scale provenance stratum has a negative descriptive paired delta, but this does not overturn the candidate: it is a small descriptive subgroup and the pre-frozen exclusion sensitivity removing the entire subgroup preserves positive uplift in every fold.

## Interpretation

`O2_OPEN_GEOMETRY` remains a credible historical-development survivor. The evidence does not support a provider-artifact explanation for the accepted uplift.

However, the three geometry columns are exactly algebraically redundant. This creates a legitimate model-minimality question because an HGB can distribute axis-aligned splits across redundant representations even when the underlying information dimension is smaller.

Therefore O2 is not yet authorized for final refit or champion replacement. A separately frozen minimality ablation is authorized.

## Authorization

Authorized next:

- exact same 278,168-row common-support population;
- exact same V3-B baseline, H10 labels, six folds, HGB parameters, evaluator;
- retrain only a bounded, predeclared set of O2 geometry ablations sufficient to determine whether the three-feature representation can be simplified without losing the robust historical-development signal;
- no new Open information beyond the existing three O2 geometry quantities;
- persist paired fold metrics and stop for independent review before any final freeze/refit.

Not authorized:

- O3 or new Open feature engineering;
- hyperparameter search;
- regime-conditioned Open features;
- fresh-forward outcome access;
- final refit/champion replacement;
- remaining Open repair/provider calls;
- execution/PnL, Path Risk, probability/payoff/reliability, paper/live or broker work.
