# OHLCV O1 Historical-Development Runtime

Date: 2026-08-12 (Asia/Jakarta)  
Branch: `research/idx-ranking-ohlcv-o1-v1`  
Expected starting HEAD: `b9567f212bf7af94ad58bd6b78bfe192ee52ee78`  
Decision: `O1_NO_SURVIVOR`

## Scope and boundary

This run executed only the frozen OHLCV O1 historical-development experiment
from `docs/checkpoints/2026-08-12_OHLCV_O1_RESEARCH_SPEC.md`. It used no network
calls and did not access any post-2026-07-31 fresh-forward outcome. The canonical
V3-B model and its final refit were not overwritten.

The exact common-support population was loaded from the preserved coverage-gate
artifact, not recomputed from the panel:

- source readiness rows: `292,633`;
- exact all-five-Open-feature-ready rows: `278,168`;
- common-support tickers: `729`;
- common-support key SHA-256: `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- training signal dates: `2021-06-02` through `2026-07-17` (all historical H10
  labels mature no later than 2026-07-31).

## Frozen contract verification

- V3-B identity: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- canonical V3-B feature order: 33 columns, exact manifest order;
- V3-B feature-order SHA-256:
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- HGB preprocessing: `ColumnTransformer` with one numeric pipeline,
  `SimpleImputer(strategy=median, add_indicator=True,
  keep_empty_features=True)`;
- HGB parameters: `learning_rate=0.05`, `max_iter=200`,
  `max_leaf_nodes=31`, `l2_regularization=1.0`, `random_state=42`;
- H10 target: `TP_FIRST=1`, `SL_FIRST=0`; no other label status entered the
  table;
- six folds: expanding train, 20-session H20 purge, 100-session validation:

| fold | train | purge | validation |
|---|---:|---:|---:|
| V2F1 | 1-504 | 505-524 | 525-624 |
| V2F2 | 1-624 | 625-644 | 645-744 |
| V2F3 | 1-744 | 745-764 | 765-864 |
| V2F4 | 1-864 | 865-884 | 885-984 |
| V2F5 | 1-984 | 985-1004 | 1005-1104 |
| V2F6 | 1-1104 | 1105-1124 | 1125-1224 |

All four models used identical row identities, folds, labels, evaluator, and
HGB parameters. Feature additions were limited to `overnight_gap` and/or
`intraday_return` exactly as specified.

## Paired fold results

Values below are challenger PR-AUC minus the same-fold
`V3B_COMMON_SUPPORT_BASELINE` PR-AUC. Full PR-AUC, ROC-AUC, Q5-Q1, top-decile
lift, row counts, feature hashes, and runtimes are in `fold_metrics.csv`.

| fold | baseline PR-AUC | O1A overnight | O1B intraday | O1C decomposition |
|---|---:|---:|---:|---:|
| V2F1 | 0.411653 | -0.001292 | 0.002337 | 0.000809 |
| V2F2 | 0.410799 | 0.002084 | -0.000978 | 0.003499 |
| V2F3 | 0.419665 | 0.001636 | 0.002112 | -0.000971 |
| V2F4 | 0.428566 | -0.014955 | -0.004234 | -0.012118 |
| V2F5 | 0.489574 | -0.001660 | 0.001520 | 0.003842 |
| V2F6 | 0.336431 | 0.012650 | 0.011821 | 0.025485 |

| model | median paired delta | lower quartile paired delta | positive folds | aggregate guardrail reversal | survivor |
|---|---:|---:|---:|---|---|
| O1A_OVERNIGHT | 0.000172 | -0.001568 | 3/6 | false | no |
| O1B_INTRADAY | 0.001816 | -0.000354 | 4/6 | true | no |
| O1C_DECOMPOSITION | 0.002154 | -0.000526 | 4/6 | false | no |

The aggregate guardrail is marked as a clear reversal only when both median
ROC-AUC and median Q5-Q1 are below the common-support baseline. Regardless,
all three challengers fail the frozen lower-quartile paired-improvement gate.
Therefore no O1 family survivor is authorized.

## Historical-era diagnostic

The persisted `era_metrics.csv` contains model/year rows for 2023-2026. The
2026 rows are not fresh-forward outcomes; they are historical H10 development
rows whose labels are available by the 2026-07-31 boundary. O1 uplifts are not
uniform across eras, and the negative V2F4 results plus negative lower quartiles
prevent a survivor decision.

## Validation

- focused: `5 passed` (`tests/test_ohlcv_o1_research.py`);
- full: `279 passed, 5 warnings`;
- warnings are pre-existing pandas deprecation warnings in unrelated modules;
- runtime: 24 HGB fits, six folds, approximately 80.8 seconds.

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

## External runtime artifacts

Root: `D:\Documents\Project\idx-trade-data-gate-20260808v\ohlcv_o1_research_v1_20260812`

| file | SHA-256 |
|---|---|
| `aggregate_metrics.csv` | `400867c9efb67824cc7437de9cab68181448a80f7125fc93e099954cb6bded78` |
| `common_support_rows.csv` | `59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f` |
| `era_metrics.csv` | `b693df6900de42d591e1abd153e71980e1fba1cbaf9ba0b1095b321f7cb96a4e` |
| `experiment_summary.json` | `76fbcbc4baaec436061b4e0beb43c130050e7c7a37de7ba3084d3f674ca056c5` |
| `feature_manifest.json` | `0874f2442002035e8c096442f9cac7a69f092434b71e5425ca6a2bb12bed7626` |
| `fold_definitions.json` | `f16ddd1640701b206cb10418ca9fa7736695fe8268ac5c38213ba22b1fe76046` |
| `fold_metrics.csv` | `c678802d999995031e0db50397120a7ee49a666774dd93d819fc4f39f877ec91` |
| `fold_predictions.parquet` | `1904ec81cd85c2cb8dcb864374a773fa110693ae047b19aadcef6c18e82955d3` |
| `preflight_contract.json` | `0981e2deffaade0da50831d8dc00db6652ae168ec3639a24aa8ee842188610b6` |
| `survivor_decision.csv` | `fa829de9d95000bcb8287f27a31cd84b31ebb04018f86e7662d01610c0e07023` |
| `artifact_manifest.json` | `2441f9fcadc9a496ed5d15306bb7bbcb87c9978ecdc26033f5bd7619c2d08714` |

The external artifact manifest was re-hashed after runtime and all ten listed
artifact hashes matched its internal manifest entries.

## Stop condition

`O1_NO_SURVIVOR`. Do not start O2/Open-geometry/interaction experiments from
this result without a new authorization and independent review.
