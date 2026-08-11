# OHLCV O2 Geometry — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-geometry-v1`
Reviewed runtime HEAD: `a194deec7c5076f1bb1d077d2e6e5081e531bcff`
Decision: `O2_SURVIVOR_ACCEPTED_ROBUSTNESS_AUDIT_AUTHORIZED`

## Independent verdict

The frozen O2 geometry experiment is accepted as a valid historical-development survivor.

Key evidence:

- exact common-support population: 278,168 rows / 729 tickers;
- common-support key hash matches O1: `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- canonical V3-B baseline reproduced with exact 33-feature order/hash `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- challenger adds only the three preregistered geometry features;
- geometry formulas independently checked to floating-point tolerance;
- paired PR-AUC delta is positive in all six folds;
- median paired delta `+0.0072762209`;
- lower quartile paired delta `+0.0047096450`;
- aggregate ranking guardrail reversal is false;
- no network, sealed holdout, or post-2026-07-31 fresh-forward outcome was accessed.

The result is materially stronger and more temporally consistent than O1. It establishes that Open-derived daily geometry deserves continuation under the current V3-B/HGB/H10 architecture. It does not yet establish an independent champion replacement.

## Causality review

The three O2 features use only completed session-t Open/High/Low values:

- `open_position = (Open_t - Low_t) / (High_t - Low_t)`;
- `open_to_high = High_t / Open_t - 1`;
- `open_to_low = Low_t / Open_t - 1`.

The project signal is formed after the session-t close, so these quantities are known at signal time and do not consume H10 future outcomes.

## Remaining robustness questions before any final refit

1. Open provenance is mixed across canonical/original panel, Yahoo-derived evidence, and TradingView-derived evidence. The uplift must not be driven by provider-specific quirks or a small backfill subset.
2. Geometry feature distributions must be checked for source-specific discontinuities/outliers.
3. `open_position` is algebraically related to `open_to_high` and `open_to_low`; redundancy is not itself invalid for HGB, but feature-family robustness/minimality should be understood before freezing a candidate.
4. Existing fold predictions should be independently re-evaluated under bounded provenance/time diagnostics before any new final-refit or forward contract is created.

## Authorized next work

A bounded O2 robustness/provenance audit is authorized. It should reuse existing O2/baseline predictions and artifacts wherever possible and must not inspect fresh-forward outcomes.

Minimum diagnostics:

- independently reproduce accepted fold/aggregate metrics from persisted predictions;
- stratify row/feature distributions by Open provenance and historical era;
- report candidate performance/uplift diagnostics by provenance where statistically meaningful;
- recompute paired metrics after excluding TradingView-backed rows and other small/suspicious provenance subsets without retraining, clearly labeling these as descriptive sensitivity diagnostics;
- quantify geometry feature distribution shifts/outliers by provenance;
- document the exact algebraic dependency among the three geometry features and whether a minimality ablation is scientifically justified as a separate future experiment.

No candidate final refit, protected forward evaluation, O3 feature mining, parameter tuning, execution/PnL, or canonical V3-B overwrite is authorized by this review.
