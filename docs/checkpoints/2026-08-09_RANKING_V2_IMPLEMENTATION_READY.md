# Ranking V2 — Implementation Ready / Awaiting Prepared Cache

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-ranking-v2-spec-v1`
Substantive implementation HEAD before documentation: `5f2ed2f53aececfd7c338d3f9f65db1efae372b6`

## Status

**`RANKING_V2_IMPLEMENTATION_READY_BLOCKED_ON_PREPARED_CACHE`**

The Ranking-V2 specification, feature transforms, four candidate architectures,
V1 control, chronological fold contract, ranking metrics, eligibility gates,
champion-selection rule, prepared-cache builder, isolated candidate runner, and
metrics-only integrator are frozen/implemented before any Ranking-V2 outcome
run.

GitHub CI on the substantive implementation HEAD: **224 passed, 0 failed**.

No Ranking-V2 candidate outcome has been generated at this checkpoint.

## Frozen candidate set

Control, not champion-eligible:

- `V1_HGB_CONTROL`

Champion-eligible V2 candidates:

1. `LOGISTIC_XS`
2. `HGB_XS`
3. `HGB_XS_MARKET`
4. `PAIRWISE_LOGISTIC_XS`

No additional architecture, feature family, pair budget, hyperparameter search,
threshold search, or universe change may be introduced after outcome execution
begins.

See `docs/RANKING_V2_RESEARCH_SPEC_V1.md` for exact definitions.

## Feature design

Frozen V2 core:

- 10 same-date primary-universe percentile-rank stock features;
- 9 continuous causal market-state context features;
- 6 stock-minus-same-date-market-median relative features.

Excluded from V2 core:

- `observed_session_count`;
- `security_age_sessions_exact`.

Sector-relative features are deferred because no historical PIT-safe sector
mapping has been authorized.

## Historical development folds

Six fixed expanding-window folds with exact 20-session gaps and 100-session
validation windows:

- V2F1: train 1-504, gap 505-524, validation 525-624;
- V2F2: train 1-624, gap 625-644, validation 645-744;
- V2F3: train 1-744, gap 745-764, validation 765-864;
- V2F4: train 1-864, gap 865-884, validation 885-984;
- V2F5: train 1-984, gap 985-1004, validation 1005-1104;
- V2F6: train 1-1104, gap 1105-1124, validation 1125-1224.

The historical period through `2026-07-31` is development/research knowledge.
These folds are not an independent final validation.

## Prepared-cache prerequisite

Candidate workers are forbidden from rebuilding deterministic labels/features.
Before any outcome run, one immutable model-table cache must be materialized by:

`python -m idx_trade.ranking_v2_prepare_cache`

The cache builder fails closed unless the separate performance track proves:

- `FULL_PANEL_LEGACY_FAST_EQUIVALENT`;
- exact frozen panel/calendar hashes;
- exact H5/H10/H20 coverage in the equivalence report;
- matching fast-H10 label artifact SHA.

It then computes the frozen baseline + V2 features exactly once, joins resolved
primary H10 outcomes, writes `ranking_v2_prepared_model_table.parquet`, and
freezes its SHA in `ranking_v2_prepared_cache_manifest.json`.

## Parallel-run design after cache review

After the cache SHA is independently reviewed, parallel execution is authorized
in isolated workers:

- control worker: `V1_HGB_CONTROL`;
- worker A: `LOGISTIC_XS`;
- worker B: `HGB_XS`;
- worker C: `HGB_XS_MARKET`;
- worker D: `PAIRWISE_LOGISTIC_XS`.

All workers read the same cache hash and use separate output directories. They
may not alter code/spec/cache/model parameters. A final integrator only reads
metrics and applies the frozen selection rule.

## Champion gate

A V2 candidate is eligible only if all required metrics are finite and:

- median PR-AUC delta vs prevalence > 0;
- positive PR delta in >=4/6 folds;
- median ROC-AUC > 0.50;
- ROC-AUC >0.50 in >=4/6 folds;
- Q5-Q1 >0 in >=4/6 folds.

If none qualifies: `RANKING_V2_NO_CHAMPION`.

Any selected model is only a **historical-development champion**. Independent
Ranking-V2 validation still requires fresh forward data strictly after
`2026-07-31`, after the champion architecture is frozen.

## Safety

- Ranking V1 remains FAILED;
- consumed Stage-5 holdout cannot regain independent status;
- Probability V1 remains `PROBABILITY_V1_NOT_READY_DEFERRED`;
- no calibrated probability claim;
- no Stage 6 yet;
- no `IDX-VAL-002`;
- no execution-PnL;
- no paper/live trading;
- no main merge.
