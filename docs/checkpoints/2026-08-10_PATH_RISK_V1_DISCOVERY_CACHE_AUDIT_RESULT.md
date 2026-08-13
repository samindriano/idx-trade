# Path Risk V1 Discovery Feature Cache Audit Result

Date: 2026-08-10 (Asia/Jakarta)  
Status: **COMPLETE — FEATURE CACHE FROZEN PRE-OUTCOME**

## Decision

Path Risk V1 implementation and real outcome-blind discovery-cache preparation
completed. The cache is frozen through signal session `984`. This is not a
Path Risk model result: no real H10 labels, adverse-excursion targets, PR-001
fit, performance metric, or Path Risk verdict was accessed.

Path Risk remains a separate lane and does not change the final ranking model
`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` or the permanent ranking denominator
`17`.

## Execution identity and pytest

- repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`;
- branch: `research/idx-ranking-v2-spec-v1`;
- implementation HEAD before documentation: `61991c80f95355b34824b5fe09aa8d8e4977aa82`;
- full pytest: `375 passed, 0 failed, 3 warnings`;
- pytest time: `16.44s`;
- warnings: three existing pandas `FutureWarning` instances in curated identity
  and tradability-anchor reconstruction tests.

Implemented files:

- `src/idx_trade/path_risk_v1.py`;
- `src/idx_trade/path_risk_v1_prepare.py`;
- `tests/test_path_risk_v1.py`.

The synthetic tests cover TP_FIRST, SL_FIRST, AMBIGUOUS_SAME_BAR,
NO_BARRIER_HIT, incomplete future paths, status/barrier identity mismatch,
Open-independence, q75 model semantics, pinball loss, quintile diagnostics, and
the frozen discovery gate.

## Frozen identities

| Artifact | SHA-256 / Git blob |
|---|---|
| signal panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| PIT security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| Path Risk spec normalized SHA-256 | `47b6cd66833f506264ca096c9a050a9e35142365fa5c158c414c5003c382c313` |
| Path Risk spec Git blob | `a0d9f23844d9f7f2c311e27a471a86d7f7f48395` |
| exact 33-feature order | `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e` |

The panel schema was inspected only for source-column selection. The cache
builder projected `ticker`, `date`, HLCV, and `regular_market_value`; source
`open` and other provenance columns were not propagated.

## Cache artifacts

Output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_feature_cache_prepare_20260810_001`

| Artifact | Path | SHA-256 |
|---|---|---|
| feature cache | `D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_feature_cache_prepare_20260810_001\path_risk_v1_discovery_feature_cache.parquet` | `74c300390dce542dad95ae204dd7663f5f780b09dd33c3514c5dd264f15cca08` |
| manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_feature_cache_prepare_20260810_001\path_risk_v1_discovery_feature_cache_manifest.json` | `054ccff7676a744871b1f82a5b263898f9fa53c2d1ae1ac20a5659485466bed0` |
| audit | `D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_feature_cache_prepare_20260810_001\path_risk_v1_discovery_feature_audit.json` | `1bb6fecbae1733f7ab62022c5f50389ffdd2bfe1dcc68f98c9853c9d123d2807` |

Cache facts:

- status: `PATH_RISK_V1_DISCOVERY_FEATURE_CACHE_FROZEN_PRE_OUTCOME`;
- rows/tickers/dates: `254,383 / 679 / 965`;
- signal-session range: `20..984`;
- primary-liquid count per date: min `222`, median `258`, max `307`;
- duplicate `(ticker,date)` rows: `0`;
- infinity cells: `0`;
- feature-order exact: `true`;
- forbidden outcome/label columns: `[]`;
- constant features: `[]`;
- all-null features: `[]`.

## Per-feature finite audit

`finite_rate` is the fraction of cache rows with a finite value. Missing values
are preserved for later training-only imputation, as required by the frozen
model contract.

| Feature | Finite rate | Unique finite values |
|---|---:|---:|
| xs_rank_close_return_5 | 1.000000000 | 27075 |
| xs_rank_close_return_20 | 0.998207427 | 25140 |
| xs_rank_atr14_over_close | 1.000000000 | 22656 |
| xs_rank_close_position_20 | 0.999025092 | 32906 |
| xs_rank_distance_high_20_atr | 0.998191703 | 28034 |
| xs_rank_distance_low_20_atr | 0.998191703 | 28530 |
| xs_rank_distance_high_60_atr | 0.929916700 | 23169 |
| xs_rank_distance_low_60_atr | 0.929916700 | 24671 |
| xs_rank_relative_volume_20 | 1.000000000 | 20504 |
| xs_rank_log_regular_value_relative_20 | 1.000000000 | 20504 |
| market_primary_liquid_count | 1.000000000 | 86 |
| market_breadth_return_5_positive | 1.000000000 | 890 |
| market_breadth_return_20_positive | 0.999103714 | 880 |
| market_median_close_return_5 | 1.000000000 | 712 |
| market_median_close_return_20 | 0.999103714 | 824 |
| market_median_atr14_over_close | 1.000000000 | 911 |
| market_median_close_position_20 | 1.000000000 | 581 |
| market_median_relative_volume_20 | 1.000000000 | 965 |
| market_median_log_regular_value_relative_20 | 1.000000000 | 965 |
| market_relative_close_return_5 | 1.000000000 | 190939 |
| market_relative_close_return_20 | 0.998207427 | 228098 |
| market_relative_atr14_over_close | 1.000000000 | 249019 |
| market_relative_close_position_20 | 0.999025092 | 140302 |
| market_relative_relative_volume_20 | 1.000000000 | 253863 |
| market_relative_log_regular_value_relative_20 | 1.000000000 | 253863 |
| structure_support_distance_atr | 0.911153654 | 25665 |
| structure_resistance_distance_atr | 0.964238963 | 27769 |
| structure_support_touch_count_60 | 0.912961951 | 20 |
| structure_resistance_touch_count_60 | 0.966027604 | 20 |
| structure_nearest_level_age_sessions | 0.997495902 | 60 |
| structure_role_reversal_count_120 | 0.999174473 | 14 |
| structure_breakout_retest_state | 0.997366176 | 5 |
| structure_breakout_volume_confirmed | 0.997366176 | 2 |

## Runtime and flags

- cache preparation runtime: `428.053400s`;
- Python: CPython `3.13.5`;
- platform: Windows 11;
- numpy/pandas/pyarrow: `2.4.2 / 2.3.3 / 23.0.1`.

Manifest and audit both record:

- `real_h10_labels_loaded=false`;
- `real_path_risk_target_computed=false`;
- `pr001_model_fitted=false`;
- `path_risk_performance_metrics_computed=false`;
- `f5_f6_path_risk_accessed=false`;
- `fresh_forward_accessed=false`;
- `forward_marker_written=false`.

No real Path Risk performance metric or verdict exists yet. PR-001 remains
reserved/unviewed and requires separate ChatGPT review/authorization before
real target construction or F1-F4 outcome access.
