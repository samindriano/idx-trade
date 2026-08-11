# OHLCV O2 Geometry Historical-Development Runtime

Date: 2026-08-12 (Asia/Jakarta)  
Branch: `research/idx-ranking-ohlcv-o2-geometry-v1`  
Starting HEAD: `2d33bcbb4820761a561df57f23ae9f18a348b4ba`  
Decision: `O2_SURVIVOR`

## Scope and protected boundary

This run executed only the frozen single-candidate
`O2_OPEN_GEOMETRY` historical-development experiment. It did not access the
network, post-2026-07-31 fresh-forward outcomes, a forward-outcome marker, or
any sealed holdout. It did not overwrite canonical V3-B, perform a challenger
final refit, start O3, or run any Open interaction/regime/feature-mining work.

## Exact population and baseline

The population was loaded from the preserved coverage-gate artifact and joined
to the preserved V3-B final training table. It was not recomputed from the
panel:

- exact common-support rows: `278,168`;
- exact common-support tickers: `729`;
- common-support key SHA-256:
  `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- the emitted `common_support_rows.csv` hash is identical to the O1 runtime;
- baseline: `V3B_COMMON_SUPPORT_BASELINE`;
- challenger: `O2_OPEN_GEOMETRY`;
- signal history ends at `2026-07-17`; all labels are historical H10 labels
  mature by the 2026-07-31 boundary.

The baseline was refit in this run from the same rows and contract. O1 metrics
were not used to alter the decision rule.

## Frozen feature and model contract

Canonical V3-B baseline:

- 33 features, exact final-manifest order;
- feature-order SHA-256:
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`.

O2 appends exactly these three features, in this order:

1. `open_position = (Open_t - Low_t) / (High_t - Low_t)`;
2. `open_to_high = High_t / Open_t - 1`;
3. `open_to_low = Low_t / Open_t - 1`.

The 36-feature O2 order SHA-256 is:
`a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`.

Both models used the same frozen pipeline:

- `ColumnTransformer` with one numeric branch;
- `SimpleImputer(strategy="median", add_indicator=True,
  keep_empty_features=True)`;
- `HistGradientBoostingClassifier` with
  `learning_rate=0.05`, `max_iter=200`, `max_leaf_nodes=31`,
  `l2_regularization=1.0`, `random_state=42`;
- same H10 labels: `TP_FIRST=1`, `SL_FIRST=0`;
- same six expanding folds with 20-session purge and 100-session validation.

The certified geometry values were used directly from the coverage artifact.
Formula checks passed with maximum absolute errors:

| feature | max absolute error |
|---|---:|
| `open_position` | `7.105427357601002e-15` |
| `open_to_high` | `3.191891195797325e-16` |
| `open_to_low` | `3.0878077872387166e-16` |

## Paired fold metrics

The paired columns are `O2_OPEN_GEOMETRY PR-AUC - baseline PR-AUC`.

| fold | baseline PR-AUC | O2 PR-AUC | paired delta | O2 ROC-AUC | O2 Q5-Q1 | O2 top-decile lift |
|---|---:|---:|---:|---:|---:|---:|
| V2F1 | 0.411653 | 0.415518 | +0.003866 | 0.537553 | 0.089033 | 0.056979 |
| V2F2 | 0.410799 | 0.411250 | +0.000451 | 0.529555 | 0.093839 | 0.054837 |
| V2F3 | 0.419665 | 0.426907 | +0.007242 | 0.535664 | 0.056654 | 0.039286 |
| V2F4 | 0.428566 | 0.435877 | +0.007310 | 0.527712 | 0.042160 | 0.020915 |
| V2F5 | 0.489574 | 0.501605 | +0.012031 | 0.540882 | 0.081196 | 0.066006 |
| V2F6 | 0.336431 | 0.350254 | +0.013823 | 0.496630 | 0.041916 | 0.015057 |

Aggregate comparison:

| model | mean PR-AUC | median PR-AUC | mean ROC-AUC | median ROC-AUC | mean Q5-Q1 | median Q5-Q1 | mean top-decile lift |
|---|---:|---:|---:|---:|---:|---:|---:|
| V3B baseline | 0.416115 | 0.415659 | 0.521676 | 0.526775 | 0.057713 | 0.051143 | 0.034759 |
| O2 geometry | 0.423568 | 0.421213 | 0.527999 | 0.532609 | 0.067467 | 0.068925 | 0.042180 |

## Frozen survivor decision

`O2_OPEN_GEOMETRY` satisfies all four frozen conditions:

- median paired PR-AUC delta: `+0.0072762209098306` > 0;
- lower-quartile paired PR-AUC delta: `+0.0047096450033947` > 0;
- positive paired folds: `6/6`; not an isolated fold spike;
- aggregate ranking guardrail reversal: `false`.

Decision: `O2_SURVIVOR`.

The era diagnostic is persisted in `era_metrics.csv`. O2 is positive versus
the baseline in the persisted 2023, 2024, 2025 and 2026 historical diagnostics;
this is descriptive development evidence, not fresh-forward validation.

Because O2 survives, stop here for independent ChatGPT review. No combination,
final refit, O3, geometry interaction, regime adaptation, or fresh-forward
evaluation is authorized by this run.

## Validation

- focused pytest: `3 passed` (`tests/test_ohlcv_o2_geometry_research.py`);
- full pytest: `282 passed, 5 warnings`;
- runtime: two models across six folds, approximately `44.6` seconds;
- artifact manifest internal verification: `10/10` listed artifact hashes match.

## Input hashes

| artifact | SHA-256 |
|---|---|
| immutable model-safe panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official exchange calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| PIT security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| accepted Yahoo+TradingView Open panel | `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab` |
| accepted Open provenance | `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687` |
| coverage-gate readiness rows | `d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242` |
| V3-B training table | `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe` |
| V3-B final manifest | `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9` |
| parent O1 artifact manifest | `2441f9fcadc9a496ed5d15306bb7bbcb87c9978ecdc26033f5bd7619c2d08714` |

## External runtime artifacts

Root: `D:\Documents\Project\idx-trade-data-gate-20260808v\ohlcv_o2_geometry_v1_20260812`

| file | SHA-256 |
|---|---|
| `aggregate_metrics.csv` | `66ed45fd756b9b8a43372f44c83bacf3f301af68bed779667144839a50a754db` |
| `common_support_rows.csv` | `59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f` |
| `era_metrics.csv` | `6d31b4e209400f7041c988b3b261b4dff832fbf686fe4c602d93faa1b29d48e9` |
| `experiment_summary.json` | `0c0dc31ca28b2661410b58465e465878279c834f945695f6574858e059a5330f` |
| `feature_manifest.json` | `9014166635a7365d6f0a101132648c24637b04a6af2455063f3f37eee6586f04` |
| `fold_definitions.json` | `f16ddd1640701b206cb10418ca9fa7736695fe8268ac5c38213ba22b1fe76046` |
| `fold_metrics.csv` | `9bb41dd44121aeabc1d7b84281485b4ae80a6ec386d8d4475a9d8c05b9864671` |
| `fold_predictions.parquet` | `fe02c0c743e7bfc5a57b1c8e731c5685a4bff5f9854f910f88703b15a6ca8f0c` |
| `preflight_contract.json` | `2d00adaf26b01a5fed81eaae61e6d7c254093f353f05c633733f78bc28284555` |
| `survivor_decision.csv` | `f4b36a332df11f7c45f10b741d9e61f062c855655236954fa493b4e5b829f262` |
| `artifact_manifest.json` | `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a` |
