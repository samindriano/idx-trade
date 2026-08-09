# Ranking V2 — Frozen Spec / Candidate Implementation Draft

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-ranking-v2-spec-v1`

## Status

`RANKING_V2_SPEC_FROZEN_IMPLEMENTATION_UNDER_TEST`

The Ranking V2 historical-development specification was frozen before any V2
candidate outcome run. Four candidate architectures plus one non-eligible V1
control are now implemented for deterministic execution against a future
immutable prepared cache.

No V2 candidate has been run against historical outcomes through the new runner
at this checkpoint.

## Frozen candidates

- control: `V1_HGB_CONTROL`;
- V2-A: `LOGISTIC_XS`;
- V2-B: `HGB_XS`;
- V2-C: `HGB_XS_MARKET`;
- V2-D: `PAIRWISE_LOGISTIC_XS`.

The exact feature sets, hyperparameters, six V2 folds, metrics, eligibility gate,
and champion-selection rule are frozen in `docs/RANKING_V2_RESEARCH_SPEC_V1.md`.

## Implemented code

- `src/idx_trade/research_v2_features.py`
  - ten same-date primary-universe percentile-rank features;
  - nine causal continuous market-context variables;
  - six stock-minus-market relative variables;
  - explicit exclusion of the two time-proxy features from V2 core.
- `src/idx_trade/research_v2_models.py`
  - exact pointwise Logistic/HGB candidates;
  - deterministic within-date pairwise logistic ranker with maximum 256 unique
    positive-negative pairs/date.
- `src/idx_trade/research_v2_validation.py`
  - six fixed expanding chronological folds with 20-session gaps;
  - ranking metrics and frozen champion-selection logic.
- `src/idx_trade/ranking_v2_candidate.py`
  - isolated one-candidate runner requiring an exact prepared-cache SHA;
  - common prediction/metric/bucket/model-artifact schema.
- `src/idx_trade/ranking_v2_integrate.py`
  - metrics-only integrator; does not rerun/tune models.

## Still blocked before outcome execution

The separate performance track must still complete:

1. full frozen-panel legacy-vs-fast label equivalence;
2. wall-clock and peak-memory benchmark;
3. immutable prepared Ranking-V2 cache materialization and SHA freeze.

Only after those are complete should the control and four V2 candidates be run,
preferably in parallel isolated workers.

## Safety

- Ranking V1 remains FAILED;
- consumed Stage-5 holdout remains development/diagnostic knowledge only;
- Probability V1 remains `PROBABILITY_V1_NOT_READY_DEFERRED`;
- no calibrated probability claim;
- no Stage 6;
- no `IDX-VAL-002`;
- no execution-PnL;
- no paper/live trading;
- no merge to `main`.
