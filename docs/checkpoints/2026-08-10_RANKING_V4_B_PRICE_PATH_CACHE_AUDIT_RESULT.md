# RANKING V4-B Price-Path Cache Audit Result

Date: 2026-08-10
Branch: `research/idx-ranking-v2-spec-v1`
HEAD at run: `f5c83022678030dc5d3894982136aa365aeb2dac`
Mode: outcome-blind cache preparation and feature audit only

## Decision boundary

This checkpoint records only the authorized V4-B pre-outcome cache and
feature audit. It does not contain a model fit, score, outcome metric, or
candidate verdict. The V4-B control/B1/B2 runner was not executed.

## Preflight

- full repository pytest: `348 passed`, `0 failed`, `3 warnings`;
- pytest reported runtime: `28.44s`;
- wrapper wall-clock runtime: `32.302s`;
- branch was clean and synchronized with `origin/research/idx-ranking-v2-spec-v1` before execution.

## Exact frozen inputs

| Input | Resolved path | SHA-256 / identity |
|---|---|---|
| signal panel | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| V3-B late cache | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\ranking_v3_final_structure_lite_late_dev_cache.parquet` | `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d` |
| V3-B late manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_prepare_20260810_001\ranking_v3_final_structure_lite_late_dev_cache_manifest.json` | `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880` |
| V4-B spec Git blob | `docs/RANKING_V4_B_PRICE_PATH_SPEC_V1.md` | `a750c28831b95b1c88640c5879289da5f2c05446` |

## Prepared cache

Command: `python -m idx_trade.ranking_v4_price_path_cli prepare` with the
exact inputs above and code commit `f5c83022678030dc5d3894982136aa365aeb2dac`.

- status: `RANKING_V4_B_PRICE_PATH_CACHE_FROZEN_PRE_OUTCOME`;
- cache:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_price_path_prepare_20260810_001\ranking_v4_b_price_path_prepared_cache.parquet`;
- cache SHA-256: `8c59200d284e73867a3ff3566473f7dc7dd4aa0a2bfd42917ef4e08c761d1c68`;
- manifest:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_price_path_prepare_20260810_001\ranking_v4_b_price_path_prepared_cache_manifest.json`;
- manifest SHA-256: `d30c7e4f0841bbddd479fdc0b8c62b1028dcf8f107277b5a8a250d9725243b2f`;
- rows/tickers/session range: `286,453 / 737 / 20..1224`;
- panel columns loaded: exactly `ticker,date,high,low,close`;
- prepare runtime: `83.575s`;
- `post_1224_materialized=false`;
- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`;
- `integration_candidate_materialized=false`.

## Outcome-blind audit

Command: `python -m idx_trade.ranking_v4_price_path_audit` using a separate
empty output directory.

- status: `RANKING_V4_B_PRICE_PATH_OUTCOME_BLIND_AUDIT_COMPLETE`;
- audit:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_price_path_audit_20260810_001\ranking_v4_b_price_path_outcome_blind_audit.json`;
- audit SHA-256: `b8facff42be8231e263c261f97e4c02d6b9db92e64ceee831d9ff27b5c7586d6`;
- audit runtime: `38.843s` internal / `42.520s` wrapper;
- audit loaded identity, exact V3-B 33 features, and exact six V4-B features;
- `binary_target_loaded=false`;
- `outcome_columns_loaded=false`;
- `fresh_forward_accessed=false`;
- `post_1224_materialized=false`;
- mechanical review required: `false`.

### V4-B feature coverage

| Feature | Finite | Missing | Finite rate | Unique finite | Constant |
|---|---:|---:|---:|---:|---|
| `v4b_path_efficiency_5` | 285,236 | 1,217 | 99.5751% | 192,035 | false |
| `v4b_path_efficiency_20` | 280,946 | 5,507 | 98.0775% | 266,361 | false |
| `v4b_largest_move_share_20` | 280,946 | 5,507 | 98.0775% | 272,534 | false |
| `v4b_range_acceptance_mean_5` | 281,020 | 5,433 | 98.1034% | 99,095 | false |
| `v4b_range_acceptance_mean_20` | 284,892 | 1,561 | 99.4551% | 217,883 | false |
| `v4b_extreme_close_balance_5` | 281,020 | 5,433 | 98.1034% | 11 | false |

No feature was constant, no feature had finite rate below 80%, and
`abs_spearman_ge_095=[]`.

### Highest 15 absolute Spearman correlations involving V4-B

| # | Left | Right | Spearman |
|---:|---|---|---:|
| 1 | `v4b_range_acceptance_mean_5` | `v4b_extreme_close_balance_5` | 0.940791493 |
| 2 | `v4b_range_acceptance_mean_5` | `v4b_range_acceptance_mean_20` | 0.640980586 |
| 3 | `v4b_range_acceptance_mean_20` | `v4b_extreme_close_balance_5` | 0.609508000 |
| 4 | `market_relative_close_return_5` | `v4b_range_acceptance_mean_5` | 0.529105108 |
| 5 | `xs_rank_close_return_5` | `v4b_range_acceptance_mean_5` | 0.527627389 |
| 6 | `market_relative_close_return_5` | `v4b_extreme_close_balance_5` | 0.499265114 |
| 7 | `xs_rank_close_return_5` | `v4b_extreme_close_balance_5` | 0.498127707 |
| 8 | `xs_rank_close_position_20` | `v4b_range_acceptance_mean_5` | 0.487633457 |
| 9 | `xs_rank_close_position_20` | `v4b_range_acceptance_mean_20` | 0.463698126 |
| 10 | `xs_rank_close_position_20` | `v4b_extreme_close_balance_5` | 0.463566310 |
| 11 | `market_relative_close_position_20` | `v4b_range_acceptance_mean_5` | 0.462194096 |
| 12 | `xs_rank_distance_low_20_atr` | `v4b_range_acceptance_mean_5` | 0.461718208 |
| 13 | `structure_support_touch_count_60` | `v4b_path_efficiency_20` | -0.457589876 |
| 14 | `xs_rank_distance_high_20_atr` | `v4b_range_acceptance_mean_20` | -0.446314549 |
| 15 | `market_relative_close_position_20` | `v4b_range_acceptance_mean_20` | 0.443659505 |

## Boundary confirmation

- V4-B control/B1/B2 were not fitted or scored.
- No V4-B PR-AUC, ROC-AUC, Q5-Q1, top-decile, paired, or gate result was
  computed.
- V4-B ordinals `015..017` remain `UNVIEWED_RESERVED`.
- Cumulative historical evaluated-candidate count remains `12`.
- Session `1225+` was not materialized.
- Post-2026-07-31 fresh-forward outcomes were not accessed.
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written.
- No integration candidate, calibration, Stage 6, IDX-VAL-002, execution/PnL,
  paper/live, or main merge was started.

## Next action

Stop for independent ChatGPT review. Any V4-B outcome run requires the
separate atomic first-pass authorization in the V4-B run handoff.
