# Ranking V3-E True Ranking F1-F4 Result

Date: 2026-08-10 (Asia/Jakarta)
Branch: `research/idx-ranking-v2-spec-v1`
Run commit: `adc4dbde92aa42aba31626cc0c8c6f681a735e88`
Implementation commit used: `d6d727758a5d90c673e0e7c3845cb282a2fc221b`

## Decision

Final verdict: `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`.

The exact V2 HGB_XS_MARKET control passed equivalence. The frozen LambdaMART
candidate passed absolute sanity but failed the frozen paired promotion gate.
No rescue, second ranker, integration, calibration, Stage 6, or later stage was
started. V2 HGB_XS_MARKET remains the active ranking control.

## Preflight and environment

- latest remote was fetched; branch was already at remote HEAD;
- initial post-install pytest passed, but the first runner attempt stopped before
  outcome access because pip had installed NumPy `2.5.2` while the frozen
  numerical environment requires NumPy `2.4.2`;
- only NumPy was corrected to `2.4.2`; the full suite was rerun;
- final pytest: `307 passed, 0 failed, 3 warnings, 14.08s`;
- Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`, PyArrow `23.0.1`,
  scikit-learn `1.8.0`, XGBoost `3.2.0`;
- no candidate outcome was read during the failed environment preflight.

## Frozen identities

| Artifact | SHA-256 | Git blob where applicable |
|---|---|---|
| V2 prepared table | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` | - |
| V2 prepared manifest | `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143` | - |
| V2 HGB summary | `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d` | - |
| V2 HGB predictions | `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179` | - |
| V3-E original spec | `79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55` | `20df2927b6663ea16955919760db9c1429cff3a5` |
| V3-E review addendum | `6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812` | `01c4dca87ff52fca678c948e4ee23d3e3c82dbcd` |
| Dependency erratum | `bd029458f7a7cd14424af9b748cb7522f1d23b0fe8eaf20ad8f6b44d48894bea` | `327e053c2a1b4270acc4e7de313bba97680eff8b` |

The erratum changed only the impossible package identity from `xgboost==3.2.1`
to `xgboost==3.2.0`. Research semantics and ranker parameters remained frozen.

## Discovery and control equivalence

- output directory:
  `D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_e_true_ranking_erratum_run_20260810_002`;
- combined prediction rows: `169,464` (`84,732` control + `84,732`
  LambdaMART);
- unique tickers: `474`;
- unique signal dates: `400`;
- session indices: `525..984`;
- dates: `2023-06-23..2025-06-05`;
- folds: `V2F1..V2F4` only;
- control equivalence: PASS on `84,732` rows;
- max score absolute difference: `0.0`;
- max absolute difference for every metric (prevalence, PR-AUC, PR delta,
  ROC-AUC, Q1 TP rate, Q5 TP rate, Q5-Q1, top-decile TP rate, top-decile lift):
  `0.0`.

## F1-F4 metrics

`pr_auc_delta` is relative to the frozen base prevalence metric.

| Fold | Candidate | PR-AUC | PR delta | ROC-AUC | Q5-Q1 | Top-decile lift |
|---|---|---:|---:|---:|---:|---:|
| V2F1 | Control | 0.4018405834 | 0.0216774918 | 0.5255579873 | 0.0840171804 | 0.0570381252 |
| V2F1 | LambdaMART | 0.4079461371 | 0.0277830454 | 0.5228451105 | 0.0691133109 | 0.0557343442 |
| V2F2 | Control | 0.4178986854 | 0.0289990901 | 0.5232616177 | 0.0703112098 | 0.0510438809 |
| V2F2 | LambdaMART | 0.4216774218 | 0.0327778265 | 0.5319873572 | 0.0581374123 | 0.0552831649 |
| V2F3 | Control | 0.4227122109 | 0.0087894853 | 0.5273786275 | 0.0386511099 | 0.0426599075 |
| V2F3 | LambdaMART | 0.4418709712 | 0.0279482457 | 0.5260509152 | 0.0499122464 | 0.0389250802 |
| V2F4 | Control | 0.4229291271 | 0.0382948851 | 0.5128270182 | 0.0575345910 | 0.0239988515 |
| V2F4 | LambdaMART | 0.3975937517 | 0.0129595097 | 0.5250259147 | 0.0552858136 | 0.0072122808 |

## Paired deltas versus control

| Fold | PR improvement | ROC change | Q5-Q1 change | Top-decile lift change |
|---|---:|---:|---:|---:|
| V2F1 | +0.0061055536 | -0.0027128768 | -0.0149038695 | -0.0013037810 |
| V2F2 | +0.0037787365 | +0.0087257395 | -0.0121737975 | +0.0042392840 |
| V2F3 | +0.0191587603 | -0.0013277122 | +0.0112611365 | -0.0037348273 |
| V2F4 | -0.0253353754 | +0.0121988964 | -0.0022487774 | -0.0167865707 |

Aggregate paired diagnostics:

- median PR improvement `+0.0049421451`;
- q25 PR improvement `-0.0034997915`;
- worst PR improvement `-0.0253353754`;
- non-below-control PR folds `3/4`;
- median ROC change `+0.0036990136`;
- median Q5-Q1 change `-0.0072112874`;
- non-below-control Q5-Q1 folds `1/4`;
- median top-decile lift change `-0.0025193041`.

## Gates and F4

- absolute sanity gate: `PASS`;
- paired promotion gate: `FAIL`;
- F4 control: PR-AUC `0.4229291271`, PR delta `0.0382948851`, ROC-AUC
  `0.5128270182`, Q5-Q1 `0.0575345910`, top-decile lift `0.0239988515`;
- F4 LambdaMART: PR-AUC `0.3975937517`, PR delta `0.0129595097`, ROC-AUC
  `0.5250259147`, Q5-Q1 `0.0552858136`, top-decile lift `0.0072122808`;
- F4 paired PR change `-0.0253353754`, Q5-Q1 change `-0.0022487774`, and
  top-decile lift change `-0.0167865707`.

The paired gate fails because q25 PR improvement and worst-fold PR improvement
are negative, and only `1/4` folds are non-inferior on Q5-Q1. No gate was
weakened.

## Query, score, and top-decile diagnostics

| Fold | Train rows | Query dates | Mixed / all-zero / all-one queries | Query rows min / q25 / median / max | Rows dropped |
|---|---:|---:|---|---|---:|
| V2F1 | 114,364 | 485 | 485 / 0 / 0 | 171 / 218 / 233 / 286 | 0 |
| V2F2 | 141,220 | 605 | 605 / 0 / 0 | 171 / 217 / 231 / 286 | 0 |
| V2F3 | 166,632 | 725 | 725 / 0 / 0 | 171 / 212 / 227 / 286 | 0 |
| V2F4 | 191,601 | 845 | 845 / 0 / 0 | 171 / 208 / 224 / 286 | 0 |

Score diversity for LambdaMART had no all-tied dates. Global unique scores were
22,537 / 20,715 / 20,935 / 20,236 for V2F1..V2F4; minimum per-date unique
score fractions were 0.9950 / 0.994845 / 0.990099 / 0.985645.

Top-decile Jaccard and entrants/exits (control versus LambdaMART):

| Fold | Jaccard | Overlap rows | Entrants | Exits |
|---|---:|---:|---:|---:|
| V2F1 | 0.2712707182 | 982 | 1,319 | 1,319 |
| V2F2 | 0.3056580566 | 994 | 1,129 | 1,129 |
| V2F3 | 0.2970027248 | 981 | 1,161 | 1,161 |
| V2F4 | 0.2157434402 | 740 | 1,345 | 1,345 |

## Artifact hashes

Run artifact directory is external runtime evidence and is intentionally not
committed to the repository. Main artifact hashes:

- summary: `ca2e359aaf20089125f2b0606fa152a3042dcaec8249ffa5b5a16e50db28ba72`;
- dependency identity: `b7b0c41d30428ef71161e3d104e796a68ea48ffaaec13393007f9a182f4afe81`;
- control equivalence: `086f70141dceb4df5ba99e76e8877f59a186efcf44bffc3eabcb7849d1d246c3`;
- metrics: `34a9cdc0543ba441762dd3245e21a363086d9ec4de4ec3dbbb1caada0788e933`;
- predictions: `2b409764e73624a6897f1c72b2c77d0e6b5a7fe712c1be96fbf50901d1a9dd33`;
- paired comparison: `a0aa6c736cebcc1dbc9f83b928f7095103e6670661255656191e483f4dc38daf`;
- query diagnostics: `299e5ac46590060bcbac970502b422ff6e61422c16d478886c6e500e7e346c1d`;
- score diversity: `0e1e48e84e373f906368534fcb3797ec11d8b37dcba9db2e276302a765ef6cf8`;
- top-decile overlap: `cce4a7526c3ca35f15bdfd1bc40a930dc5a4bf5ef69d904625f5fafb8b23a548`;
- aggregate: `dc08cfa2175dc2a2616c0a0e936e9f0055af878f2e5c0df519e76858c0e1392e`;
- verdict: `e181fd1db9318d59bd47d65d52a2df686438de957da2f7ee3adcbcbb35d91d55`;
- runtime: `1683b040548f55eb58df84348427d60eebaed5d03a4c157559dea331770c518d`;
- run total: `65.05184059997555s` (control `11.2253216s`, LambdaMART
  `52.0476144s`).

The summary contains the hashes of all fold model/imputer/parameter files.

## Boundary confirmation

- V2F5/V2F6 were not materialized, scored, or summarized;
- reserved post-2026-07-31 V2 forward outcomes were not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written;
- V3-D remains blocked and unscored;
- V2 control remains active; no automatic integration was performed.
