# Ranking V3-B Structure-Lite F1-F4 Discovery Result

Date: 2026-08-10 (Asia/Jakarta)

Status: **`V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`**

Evidence class: historical development evidence only; not independent
validation and not a calibrated probability result.

## Scope and source identity

- repository: `samindriano/idx-trade`;
- branch: `research/idx-ranking-v2-spec-v1`;
- run/implementation HEAD: `eee4ed0458fdfdea5fdc0f5335ec211efd3dd80b`;
- hypothesis: `V3-B-STRUCTURE-LITE-V1`;
- candidates: exact V2 control ordinal `004`, one Structure-Lite candidate
  ordinal `005`;
- folds scored: `V2F1`, `V2F2`, `V2F3`, `V2F4` only;
- V2F5/V2F6: not loaded, scored, or summarized;
- reserved post-2026-07-31 V2 forward outcomes: not accessed.

The source-layout runner required `PYTHONPATH=src` for local module discovery.
No source, spec, gate, or research definition was changed to accommodate this
environment detail.

## Preflight

Full repository pytest from the explicit IDX Trade root:

**`252 passed, 0 failed, 3 warnings in 32.16 s`**

The wrapper wall-clock duration was `36.29 s`. The three warnings are existing
pandas `FutureWarning` instances in curated-identity and tradability-anchor
concatenation tests. Because pytest passed, cache preparation and the frozen
runner were allowed to proceed.

## Frozen input artifact verification

| Artifact | Path | SHA-256 |
|---|---|---|
| signal panel | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| security master | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv` | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| V2 prepared table | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet` | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` |
| V2 prepared manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_cache_manifest.json` | `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143` |
| frozen V2 HGB summary | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_candidate_orchestra_20260810\HGB_XS_MARKET\ranking_v2_hgb_xs_market_summary.json` | `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d` |
| frozen V2 HGB predictions | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_candidate_orchestra_20260810\HGB_XS_MARKET\ranking_v2_hgb_xs_market_predictions.parquet` | `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179` |

All seven required artifacts were found unambiguously and matched exactly.

## V3-B discovery cache

Output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_prepare_20260810_run1`

- cache path: `ranking_v3_b_structure_lite_discovery_cache.parquet`;
- cache SHA-256: `7084759fddaa20e82ec03e50205f2872520e6b3e11ea5f294033589a9c803405`;
- manifest path: `ranking_v3_b_structure_lite_discovery_cache_manifest.json`;
- manifest SHA-256: `e428cad0ff24b57977106482cef1478e60c0660adcee6dbf103803516b35aeb2`;
- manifest status: `RANKING_V3_B_STRUCTURE_LITE_DISCOVERY_CACHE_FROZEN`;
- rows: `216,472`;
- tickers: `674`;
- session range: `20..984`;
- `v2f5_v2f6_materialized=false`;
- `outcome_metrics_computed=false`;
- candidate feature-order SHA-256: `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`.

Independent cache checks all passed:

- exact V2 row identity/order and V2 feature prefix preserved;
- no duplicate or orphan join rows;
- no infinite structure values;
- event states exactly within `{-2,-1,0,1,2}`;
- observed volume confirmation exactly within `{0,1}`;
- no row exceeded session `984`;
- all frozen source/spec/addendum identities matched.

### Feature coverage

| Feature | Finite rows | Finite rate | Missing rate |
|---|---:|---:|---:|
| `structure_support_distance_atr` | 198,190 | 91.5546% | 8.4454% |
| `structure_resistance_distance_atr` | 208,730 | 96.4236% | 3.5764% |
| `structure_support_touch_count_60` | 198,190 | 91.5546% | 8.4454% |
| `structure_resistance_touch_count_60` | 208,730 | 96.4236% | 3.5764% |
| `structure_nearest_level_age_sessions` | 216,316 | 99.9279% | 0.0721% |
| `structure_role_reversal_count_120` | 216,321 | 99.9302% | 0.0698% |
| `structure_breakout_retest_state` | 216,321 | 99.9302% | 0.0698% |
| `structure_breakout_volume_confirmed` | 216,321 | 99.9302% | 0.0698% |

Missing structure values remain missing and are handled by the frozen
training-only imputer. No rows were dropped for missing structure levels.

## Control equivalence

**`V3_B_CONTROL_EQUIVALENCE_PASS`**

- rows: `84,732` across V2F1-V2F4;
- score tolerance: `1e-12`, `rtol=0`;
- metric tolerance: `1e-12`, `rtol=0`;
- maximum row-level score absolute difference: `0.0`;
- maximum absolute difference for positive rate, PR-AUC, PR-AUC delta,
  ROC-AUC, Q1 TP, Q5 TP, Q5-Q1, top-decile TP, and top-decile lift: `0.0`.

Only after this gate passed did the runner fit/score the one Structure-Lite
candidate.

## Per-fold metrics

| Candidate | Fold | Rows | Prev. | PR-AUC | PR-AUC-prev. | ROC-AUC | Q1 TP | Q5 TP | Q5-Q1 | Top-decile TP | Lift |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Control | V2F1 | 22,564 | 0.380163 | 0.401841 | 0.021677 | 0.525558 | 0.337059 | 0.421076 | 0.084017 | 0.437201 | 0.057038 |
| Control | V2F2 | 20,756 | 0.388900 | 0.417899 | 0.028999 | 0.523262 | 0.355058 | 0.425370 | 0.070311 | 0.439943 | 0.051044 |
| Control | V2F3 | 21,016 | 0.413923 | 0.422712 | 0.008789 | 0.527379 | 0.399424 | 0.438075 | 0.038651 | 0.456583 | 0.042660 |
| Control | V2F4 | 20,396 | 0.384634 | 0.422929 | 0.038295 | 0.512827 | 0.348192 | 0.405727 | 0.057535 | 0.408633 | 0.023999 |
| Structure-Lite | V2F1 | 22,564 | 0.380163 | 0.409789 | 0.029626 | 0.528301 | 0.329683 | 0.426784 | 0.097101 | 0.451108 | 0.070945 |
| Structure-Lite | V2F2 | 20,756 | 0.388900 | 0.419740 | 0.030840 | 0.533044 | 0.349465 | 0.435384 | 0.085919 | 0.442770 | 0.053870 |
| Structure-Lite | V2F3 | 21,016 | 0.413923 | 0.427591 | 0.013669 | 0.528880 | 0.391983 | 0.440198 | 0.048215 | 0.442110 | 0.028187 |
| Structure-Lite | V2F4 | 20,396 | 0.384634 | 0.425902 | 0.041268 | 0.514575 | 0.345220 | 0.407911 | 0.062690 | 0.398561 | 0.013927 |

## Paired deltas versus exact V2 control

| Fold | PR-delta improvement | ROC change | Q5-Q1 change | Top-decile lift change |
|---|---:|---:|---:|---:|
| V2F1 | +0.007948 | +0.002743 | +0.013084 | +0.013907 |
| V2F2 | +0.001841 | +0.009782 | +0.015608 | +0.002826 |
| V2F3 | +0.004879 | +0.001502 | +0.009564 | -0.014472 |
| V2F4 | +0.002973 | +0.001748 | +0.005156 | -0.010072 |

Aggregate paired values:

- median PR-delta improvement: `+0.0039258450`;
- q25 PR-delta improvement: `+0.0026897894`;
- worst-fold PR-delta improvement: `+0.0018412974`;
- PR delta not below control: `4/4` folds;
- median ROC change: `+0.0022459186`;
- median Q5-Q1 change: `+0.0113241480`;
- Q5-Q1 not below control: `4/4` folds;
- median top-decile lift change: `-0.0036228765` (diagnostic only).

## Gates and decision

- candidate absolute sanity gate: **PASS**;
- candidate paired promotion gate: **PASS**;
- candidate verdict: `PROMOTE_FOR_NEXT_RESEARCH_STEP`;
- deterministic decision: **`V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`**;
- selected component: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- cumulative evaluated candidate count: `5`.

This promotion is a research-governance result for the next separately
authorized research step. It does not authorize independent validation,
probability calibration, fresh-forward access, F5/F6 confirmation, execution,
paper/live trading, or model deployment.

## Runtime and artifact inventory

Prepare output directory:
`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_prepare_20260810_run1`

Run output directory:
`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1`

Environment: Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`, PyArrow `23.0.1`,
scikit-learn `1.8.0`, Windows 11. Runner mode was `sequential_reference`:
control `10.3571 s`, Structure-Lite `11.1544 s`, total `22.5990 s`.

| Artifact | SHA-256 |
|---|---|
| control equivalence | `5d1b0b3ec93c4ce8556030c5332c471312ffbf87bd13473e3f2c569b56b0bdc3` |
| metrics CSV | `0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357` |
| predictions Parquet | `c7761dd0bd93340381b28234537bf7a42e829eae0f214ec8173d8bc1f6f2e4e1` |
| paired comparison CSV | `82cde407d4b52bbc28269ca97a9fd8eadd5b77cc8b97845992bbc6ee5dfcdb3f` |
| aggregate JSON | `18edea234b26b5c9c3063938b08ad0bd4feb00843cbb15541cb395b8077222e7` |
| coverage JSON | `32a9764fc4cd868c64549afbefc8270d8a7b3e656ca8983f7699761bb430c508` |
| verdict JSON | `bff66c17e2503678ce7a531115a2798cbe5e8f3e33dad84095ae3e03b1b55c12` |
| runtime JSON | `c7185d2e3c102f3756842fa709986487d8ebe65c1434af112e5ba44476c90f7c` |
| ledger rows JSON | `e615fa1db730cd1619eb07614187df5b949ee7ef34daff6c72ef37e4632821d5` |
| summary JSON | `a8ca2fea755a98bc94ad2f1d4d5ae2a25db238a0aff57323014dd2a280d5368e` |

The eight model hashes are recorded in the run summary and artifact inventory
under the run directory.

## Safety confirmations and stop boundary

`v2f5_v2f6_accessed=false` and `fresh_forward_accessed=false` are recorded in
the runner summary/verdict. `FORWARD_OUTCOME_ACCESS_STARTED` was not written.
V3-A Recency was not reopened or rescued. No V3-C/D/E, integration,
calibration, Stage 6, `IDX-VAL-002`, execution-PnL, Kelly, paper/live, or main
merge was started.

Stop after documentation and independent ChatGPT review. Do not start V3-C or
F5/F6 automatically.
