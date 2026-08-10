# Ranking V3 Final Structure-Lite Late-Development Result

Date: 2026-08-10 (Asia/Jakarta)
Branch: `research/idx-ranking-v2-spec-v1`
Run HEAD/code commit: `bf9f7d311aacd08884d59abd0e3a16942add26cf`

## Final decision

`V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS`

The unchanged V3-B Structure-Lite candidate passed the one-shot V2F5/V2F6
late-development confirmation. It is the final historical-development V3
architecture. This is not independent forward validation and does not
authorize calibration, Stage 6, `IDX-VAL-002`, execution/PnL, paper/live, or a
main merge.

## Preflight

- branch fetched and fast-forwarded to `bf9f7d311aacd08884d59abd0e3a16942add26cf`;
- tree was clean and synchronized before execution;
- full pytest: `319 passed, 0 failed, 3 warnings, 14.42s`;
- environment during run: Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`,
  PyArrow `23.0.1`, scikit-learn `1.8.0`;
- no engineering correction was required.

## Frozen cache

Prepare output directory:

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_final_structure_lite_late_dev_prepare_20260810_001`

- status: `RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CACHE_FROZEN`;
- cache SHA-256: `af0ed60f55563a571bdd86c024d3087bd46fea50845343d285f9f93b72a21a4d`;
- manifest SHA-256: `1c629850a6b902442fa4cb17585c514de88e1f9d3a40c854b07cb1f01cc58880`;
- rows: `286,453`;
- tickers: `737`;
- signal-session range: `20..1224`;
- session `1225+` rows: `0`;
- duplicate `(ticker,date)` rows: `0`;
- infinity cells in eight Structure-Lite features: `0`;
- exact V2 25-feature prefix and exact frozen 25+8 feature order preserved;
- `outcome_metrics_computed=false`;
- `fresh_forward_accessed=false`.

Late validation feature rows/coverage:

| Fold | Rows | Dates | Tickers | Support distance/touch | Resistance distance/touch | Age/role/event/volume |
|---|---:|---:|---:|---:|---:|---:|
| V2F5 | 25,647 | 100 | 440 | 94.6193% | 96.0190% | 99.8245% |
| V2F6 | 33,844 | 100 | 499 | 90.8846% | 97.5358% | 99.8641% |

The paired distance/touch columns have identical coverage. Missing values were
preserved for the frozen training-only imputer contract.

## Atomic F5/F6 run

Run output directory:

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_final_structure_lite_late_dev_run_20260810_001`

The run materialized both folds atomically. Combined predictions contain
`118,982` rows: `59,491` control and `59,491` Structure-Lite, across `540`
tickers and `200` signal dates, session indices `1005..1224`.

Control equivalence:

- status: `V3_FINAL_LATE_DEV_CONTROL_EQUIVALENCE_PASS`;
- rows: `59,491`;
- max score absolute diff: `0.0`;
- max diff for prevalence, PR-AUC, PR delta, ROC-AUC, Q1/Q5 rates, Q5-Q1,
  top-decile TP rate and top-decile lift: `0.0`;
- immutable V2 reference summary/prediction hashes matched exactly.

## Metrics

| Fold | Candidate | PR-AUC | PR delta | ROC-AUC | Q5-Q1 | Top-decile lift |
|---|---|---:|---:|---:|---:|---:|
| V2F5 | Control | 0.4882799770 | 0.0260816692 | 0.5305788566 | 0.0321790904 | 0.0222785032 |
| V2F5 | Structure-Lite | 0.4899461196 | 0.0277478118 | 0.5331806225 | 0.0537591717 | 0.0387599137 |
| V2F6 | Control | 0.3555419780 | 0.0186432663 | 0.4931017075 | 0.0448561604 | 0.0290190005 |
| V2F6 | Structure-Lite | 0.3690580960 | 0.0321593843 | 0.5049823243 | 0.0487045129 | 0.0246419944 |

Paired changes versus exact control:

| Fold | PR improvement | ROC change | Q5-Q1 change | Top-decile lift change |
|---|---:|---:|---:|---:|
| V2F5 | +0.0016661426 | +0.0026017659 | +0.0215800814 | +0.0164814105 |
| V2F6 | +0.0135161180 | +0.0118806168 | +0.0038483525 | -0.0043770061 |

Aggregate paired diagnostics:

- median PR improvement: `+0.0075911303`;
- worst PR improvement: `+0.0016661426`;
- median ROC change: `+0.0072411913`;
- median Q5-Q1 change: `+0.0127142169`;
- worst Q5-Q1 change: `+0.0038483525`;
- median top-decile lift change: `+0.0060522022`.

Top-decile diagnostic overlap:

| Fold | Jaccard | Overlap rows | Entrants | Exits |
|---|---:|---:|---:|---:|
| V2F5 | 0.3335037056 | 1,305 | 1,304 | 1,304 |
| V2F6 | 0.3631662689 | 1,826 | 1,601 | 1,601 |

## Gates

- absolute gate: `PASS` — finite metrics, positive PR delta, ROC > 0.5 and
  positive Q5-Q1 on both folds;
- paired gate: `PASS` — PR nonnegative on both, median PR >= 0.001, median
  ROC change >= -0.005, Q5-Q1 nonnegative on both;
- final architecture: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- no new candidate ordinal; cumulative architecture-candidate count remains
  `9`.

## Runtime and artifact hashes

Runtime: `26.6248833s` total; control `12.3635518s`; Structure-Lite
`12.4577249s`; mode `sequential_reference`.

Main run artifact hashes:

- summary: `79f01660a2ef98b6de3ef38905adab7109a04afa78cb4969d323f92b618ff52e`;
- control equivalence: `d48fd50b7eeddd0cfcb1d6f107023a635fb709b03fe18a290da44e2cdf28d483`;
- metrics: `5e758e468cf883212fdb11c64d63f8ab3cf86c20a04a60edbc651205bc8f6d25`;
- predictions: `64cf1c04640740c5906db03e1ba86290790904daca2971e61c00212de893715b`;
- paired: `51fa9d893b32597ab30c67961811b42f107350587a30e726ec5bf8ec2e188c04`;
- top-decile overlap: `c6f77e3e19761aba43d1325d639c6eea62d9b7450ded5044a1b0c00d8773e530`;
- aggregate: `6f3e8c8505202d7fb210242b2a6d897a6c6e94e93153920b74429722520521d3`;
- verdict: `31fca13c6f0f40d3e6db7c4286617bc695b605f2ffedec9fbdd302f69b765997`;
- runtime: `b7f1f9725da55e25a4779bb1f95c3b9724e0ff6484011c703cde51c98ab18723`.

## Boundary confirmation

- V2F5/V2F6 were consumed exactly once by this atomic run;
- sessions `1225+` were not materialized or scored;
- V3-D remains blocked/unviewed;
- fresh-forward V2 outcomes were not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written;
- no forward validation, calibration, Stage 6, `IDX-VAL-002`, execution/PnL,
  paper/live, integration, or main merge was started.
