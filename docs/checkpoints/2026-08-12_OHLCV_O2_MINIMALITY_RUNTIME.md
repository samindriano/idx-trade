# OHLCV O2 Minimality Ablation Runtime

Date: 2026-08-12 (Asia/Jakarta)  
Branch: `research/idx-ranking-ohlcv-o2-minimality-v1`  
Starting remote HEAD: `980c741c266c7ac4c17fc4496f41b797f6090a6b`  
Runtime status: `O2_MINIMALITY_EVIDENCE_COMPLETE`

## Scope and boundary

This run executed only the frozen eight-model O2 minimality ablation. It did
not make provider/network calls, access fresh-forward outcomes, tune HGB,
engineer new features, perform a final refit, replace canonical V3-B, or
select a final O2 representation. The status above is the only runtime
decision emitted by the frozen specification.

## Exact frozen inputs

- common-support rows: `278,168`;
- common-support tickers: `729`;
- common-support key SHA-256:
  `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- canonical V3-B feature order SHA-256:
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- accepted O2 feature order SHA-256:
  `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- H10 labels: `TP_FIRST=1`, `SL_FIRST=0`;
- six expanding folds: V2F1--V2F6, H20 purge, 100-session validation;
- HGB: learning rate `0.05`, `max_iter=200`, `max_leaf_nodes=31`,
  `l2_regularization=1.0`, `random_state=42`;
- accepted parent O2 artifact manifest SHA-256:
  `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`;
- all `10` artifacts listed by the accepted O2 manifest were re-hashed and
  matched before training;
- geometry formula checks were inherited from the accepted coverage artifact:
  `open_position` max error `7.105427357601002e-15`,
  `open_to_high` max error `3.191891195797325e-16`,
  `open_to_low` max error `3.0878077872387166e-16`.

## Models

The exact frozen order was:

1. `V3B_COMMON_SUPPORT_BASELINE`;
2. `O2_FULL_3`;
3. `O2_SINGLE_POSITION`;
4. `O2_SINGLE_TO_HIGH`;
5. `O2_SINGLE_TO_LOW`;
6. `O2_PAIR_POSITION_HIGH`;
7. `O2_PAIR_POSITION_LOW`;
8. `O2_PAIR_HIGH_LOW`.

All eight used identical row identities, labels, folds, preprocessing,
parameters, seed, and evaluator. Feature-order hashes are persisted in
`feature_manifest.json`.

## Accepted O2 reproduction

The rerun baseline and `O2_FULL_3` were compared with the accepted O2
`fold_metrics.csv` and `aggregate_metrics.csv`:

- fold rows compared: `12`;
- aggregate rows compared: `2`;
- maximum absolute fold PR-AUC difference:
  `9.367506770274758e-17`;
- maximum absolute aggregate difference:
  `7.979727989493313e-17`;
- all comparisons were within `1e-12` tolerance.

## Aggregate metrics

Paired deltas are candidate PR-AUC minus the named reference.

| model | mean PR-AUC | median PR-AUC | median delta vs baseline | lower quartile vs baseline | positive folds vs baseline | median delta vs full O2 |
|---|---:|---:|---:|---:|---:|---:|
| V3B baseline | 0.416115 | 0.415659 | -- | -- | -- | -0.007276 |
| O2 full 3 | 0.423568 | 0.421213 | +0.007276 | +0.004710 | 6/6 | -- |
| single position | 0.420904 | 0.417267 | +0.002095 | +0.001120 | 5/6 | -0.003946 |
| single to-high | 0.419756 | 0.415894 | +0.001606 | -0.000532 | 4/6 | -0.004494 |
| single to-low | 0.422543 | 0.419006 | +0.003348 | +0.002418 | 5/6 | -0.003612 |
| pair position/high | 0.423192 | 0.418306 | +0.003947 | +0.000205 | 4/6 | -0.004001 |
| pair position/low | 0.423092 | 0.419468 | +0.005940 | +0.003314 | 5/6 | -0.001513 |
| pair high/low | 0.423239 | 0.418059 | +0.004008 | +0.002359 | 6/6 | -0.001663 |

The complete unrounded aggregate metrics, including ROC-AUC, Q5-Q1,
top-decile lift, prevalence, row counts, feature hashes, and both paired
reference columns, are in `aggregate_metrics.csv`.

## Paired fold evidence

The exact unrounded fold-level comparison is in `paired_comparisons.csv`.
The following compact tables reproduce its PR-AUC deltas by fold.

### Delta versus V3-B baseline

| model | V2F1 | V2F2 | V2F3 | V2F4 | V2F5 | V2F6 |
|---|---:|---:|---:|---:|---:|---:|
| O2 full 3 | +0.003866 | +0.000451 | +0.007242 | +0.007310 | +0.012031 | +0.013823 |
| single position | +0.002339 | +0.001851 | +0.000877 | -0.003495 | +0.003680 | +0.023486 |
| single to-high | -0.000805 | +0.000287 | +0.002925 | -0.007863 | +0.005803 | +0.021502 |
| single to-low | +0.003303 | -0.002922 | +0.003392 | +0.002123 | +0.005994 | +0.026679 |
| pair position/high | +0.002040 | +0.006556 | -0.000407 | -0.004217 | +0.005855 | +0.032640 |
| pair position/low | +0.002820 | -0.001529 | +0.004798 | +0.007083 | +0.007729 | +0.020964 |
| pair high/low | +0.002317 | +0.000253 | +0.002484 | +0.005532 | +0.008793 | +0.023367 |

### Reduced variants versus full O2

| model | V2F1 | V2F2 | V2F3 | V2F4 | V2F5 | V2F6 |
|---|---:|---:|---:|---:|---:|---:|
| single position | -0.001527 | +0.001400 | -0.006365 | -0.010805 | -0.008352 | +0.009663 |
| single to-high | -0.004671 | -0.000164 | -0.004317 | -0.015173 | -0.006228 | +0.007679 |
| single to-low | -0.000562 | -0.003373 | -0.003850 | -0.005188 | -0.006037 | +0.012857 |
| pair position/high | -0.001826 | +0.006105 | -0.007649 | -0.011527 | -0.006176 | +0.018817 |
| pair position/low | -0.001046 | -0.001980 | -0.002444 | -0.000227 | -0.004302 | +0.007141 |
| pair high/low | -0.001548 | -0.000198 | -0.004758 | -0.001779 | -0.003239 | +0.009544 |

## Original O2 survivor diagnostics applied as diagnostics only

| model | median delta vs baseline | lower quartile | positive folds | guardrail reversal | diagnostic pass |
|---|---:|---:|---:|---:|---:|
| O2 full 3 | +0.007276 | +0.004710 | 6/6 | false | true |
| single position | +0.002095 | +0.001120 | 5/6 | false | true |
| single to-high | +0.001606 | -0.000532 | 4/6 | false | false |
| single to-low | +0.003348 | +0.002418 | 5/6 | false | true |
| pair position/high | +0.003947 | +0.000205 | 4/6 | false | true |
| pair position/low | +0.005940 | +0.003314 | 5/6 | false | true |
| pair high/low | +0.004008 | +0.002359 | 6/6 | false | true |

These are diagnostics, not a final representation selection. No model was
declared champion or automatically advanced.

## Validation

- focused pytest: `3 passed`;
- full pytest: `286 passed, 5 warnings`;
- runtime: `227.78833329999907` seconds;
- provider/network calls: none;
- fresh-forward outcomes accessed: false;
- final representation selected: false.

## External runtime artifacts

Root: `D:\Documents\Project\idx-trade-data-gate-20260808v\ohlcv_o2_minimality_v1_20260812`

Artifact manifest SHA-256:
`919e35bb8d2fe68588db331e3de25f6c2a490c2727aea9f68e1179c0bcbe5183`

| file | SHA-256 |
|---|---|
| `aggregate_metrics.csv` | `62d9a4a75711184621e40b43741ffd32f412643a074e31b1d4ec56e14767fe63` |
| `common_support_rows.csv` | `59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f` |
| `era_metrics.csv` | `31af005823e302a5ccf4d4db1e4a0e24641b4912e52db388fd3c1de136c50951` |
| `experiment_summary.json` | `81f4b86700907d6d2e8e078cd972b72fd6012e33f061522434451d7036a8b9b4` |
| `feature_manifest.json` | `888d0cdd8f96e02ae539249e0f2d9625a1ba5dbfd46152ec4a2806501d6c6558` |
| `fold_definitions.json` | `f16ddd1640701b206cb10418ca9fa7736695fe8268ac5c38213ba22b1fe76046` |
| `fold_metrics.csv` | `2ff221ddb82c8acf1eba9c824f6e2299bfb6b0b2f1d4126f62c51779c502e3ea` |
| `fold_predictions.parquet` | `cc6d2d119ce6813c680625948857984d34a25d7a054f58b439b1d646ca0918c7` |
| `minimality_diagnostics.csv` | `1d39a48662d7795a0ceb6402c3ea4f977258778cf2e27ee594eb14430226f1a3` |
| `paired_comparisons.csv` | `f889c75492887ed30b5aa37e1062a4f140ad562da2f77f60fa6f23b670186230` |
| `preflight_contract.json` | `d85835c89da71c5473d7a5acd899c6dfe77af9dac8ec48c70ed8c6df4e65c535` |

The artifact manifest re-hash verified all `11/11` listed artifact files.

## Stop condition

This lane stops here for independent ChatGPT review. No final O2
representation, final-freeze review, final refit, or downstream experiment is
started by this runtime.
