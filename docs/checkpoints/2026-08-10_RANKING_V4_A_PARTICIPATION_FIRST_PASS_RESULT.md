# Ranking V4-A Participation First-Pass Result

Date: 2026-08-10 (Asia/Jakarta)
Branch: `research/idx-ranking-v2-spec-v1`
Execution/code HEAD: `61dbfb19001598ee955430db9ee3a5b21e8290c5`

## Decision

`V4_A_FIRST_PASS_COMPLETE`

The authorized atomic first-pass runner executed exact V3-B control, A1, and
A2 in one invocation over V2F1..V2F6. Control equivalence passed. Both frozen
challengers failed their independent paired promotion gates:

- ordinal `012` exact control: reference-equivalent;
- ordinal `013` A1 Impact/Absorption: `FAIL`;
- ordinal `014` A2 Persistent Directional Participation: `FAIL`;
- survivors: `[]`;
- `integration_authorized_by_result=false`;
- `integration_executed=false`.

No rescue, redesign, second variant, or integration was run.

## Preflight and frozen inputs

- branch fetched and fast-forwarded to `61dbfb19001598ee955430db9ee3a5b21e8290c5`;
- tree was clean and synchronized before the run;
- full pytest: `337 passed, 0 failed, 3 warnings, 28.97s`;
- warnings were the existing pandas `FutureWarning`s in
  `curated_identity.py` and `tradability_anchor_reconstruction.py`;
- no engineering correction was required.

V4-A cache and manifest:

- cache:
  `D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v4_a_participation_prepare_20260810_001/ranking_v4_a_participation_prepared_cache.parquet`;
- cache SHA-256: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`;
- manifest:
  `D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v4_a_participation_prepare_20260810_001/ranking_v4_a_participation_prepared_cache_manifest.json`;
- manifest SHA-256: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`;
- spec Git blob: `e32fa69596291f418ae797613da219bd0d3cf69c`;
- cache rows/tickers/sessions: `286,453 / 737 / 20..1224`.

Frozen V3-B reference artifacts:

| Artifact | Path | SHA-256 |
|---|---|---|
| F1-F4 metrics | `D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_structure_lite_run_20260810_run1/ranking_v3_b_structure_lite_f1_f4_metrics.csv` | `0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357` |
| F1-F4 predictions | `D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_structure_lite_run_20260810_run1/ranking_v3_b_structure_lite_f1_f4_predictions.parquet` | `c7761dd0bd93340381b28234537bf7a42e829eae0f214ec8173d8bc1f6f2e4e1` |
| F5-F6 metrics | `D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_final_structure_lite_late_dev_run_20260810_001/ranking_v3_final_structure_lite_f5_f6_metrics.csv` | `5e758e468cf883212fdb11c64d63f8ab3cf86c20a04a60edbc651205bc8f6d25` |
| F5-F6 predictions | `D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_final_structure_lite_late_dev_run_20260810_001/ranking_v3_final_structure_lite_f5_f6_predictions.parquet` | `64cf1c04640740c5906db03e1ba86290790904daca2971e61c00212de893715b` |

## Control equivalence

- status: `V4_A_V3_B_CONTROL_EQUIVALENCE_PASS`;
- rows: `144,223`;
- max score absolute difference: `0.0`;
- max metric differences:
  - positive rate: `5.551115123125783e-17`;
  - PR-AUC: `5.551115123125783e-17`;
  - PR delta: `8.326672684688674e-17`;
  - ROC-AUC: `0.0`;
  - Q1 TP rate: `5.551115123125783e-17`;
  - Q5 TP rate: `5.551115123125783e-17`;
  - Q5-Q1: `8.326672684688674e-17`;
  - top-decile TP rate: `5.551115123125783e-17`;
  - top-decile lift: `8.326672684688674e-17`.

## Per-fold metrics

Values are prevalence, PR-AUC, PR delta, ROC-AUC, Q1 TP rate, Q5 TP rate,
Q5-Q1, top-decile TP rate, and top-decile lift.

| Fold | Candidate | Prev | PR-AUC | PR delta | ROC-AUC | Q1 | Q5 | Q5-Q1 | Top TP | Top lift |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V2F1 | Control-012 | .380163 | .409789 | .029626 | .528301 | .329683 | .426784 | .097101 | .451108 | .070945 |
| V2F2 | Control-012 | .388900 | .419740 | .030840 | .533044 | .349465 | .435384 | .085919 | .442770 | .053870 |
| V2F3 | Control-012 | .413923 | .427591 | .013669 | .528880 | .391983 | .440198 | .048215 | .442110 | .028187 |
| V2F4 | Control-012 | .384634 | .425902 | .041268 | .514575 | .345220 | .407911 | .062690 | .398561 | .013927 |
| V2F5 | Control-012 | .462198 | .489946 | .027748 | .533181 | .438507 | .492266 | .053759 | .500958 | .038760 |
| V2F6 | Control-012 | .336899 | .369058 | .032159 | .504982 | .309110 | .357814 | .048705 | .361541 | .024642 |
| V2F1 | A1-013 | .380163 | .413805 | .033642 | .531273 | .334823 | .427223 | .092399 | .438070 | .057907 |
| V2F2 | A1-013 | .388900 | .421274 | .032374 | .531308 | .363813 | .428708 | .064894 | .434762 | .045863 |
| V2F3 | A1-013 | .413923 | .426218 | .012295 | .526454 | .389822 | .435244 | .045422 | .443978 | .030055 |
| V2F4 | A1-013 | .384634 | .428122 | .043488 | .516850 | .339772 | .409852 | .070080 | .410072 | .025438 |
| V2F5 | A1-013 | .462198 | .488496 | .026298 | .531342 | .438507 | .489366 | .050859 | .490226 | .028028 |
| V2F6 | A1-013 | .336899 | .357381 | .020482 | .495456 | .310299 | .358402 | .048103 | .358039 | .021140 |
| V2F1 | A2-014 | .380163 | .413288 | .033125 | .532020 | .338623 | .430296 | .091673 | .455454 | .075291 |
| V2F2 | A2-014 | .388900 | .421886 | .032987 | .527647 | .341683 | .429900 | .088217 | .441357 | .052457 |
| V2F3 | A2-014 | .413923 | .422280 | .008357 | .525935 | .380461 | .424864 | .044403 | .440710 | .026787 |
| V2F4 | A2-014 | .384634 | .418663 | .034029 | .508007 | .359584 | .412279 | .052695 | .407194 | .022560 |
| V2F5 | A2-014 | .462198 | .491360 | .029162 | .530071 | .446365 | .492073 | .045707 | .498275 | .036077 |
| V2F6 | A2-014 | .336899 | .369678 | .032779 | .510771 | .309110 | .349589 | .040479 | .351328 | .014429 |

## Paired changes versus exact control

| Challenger | Fold | PR change | ROC change | Q5-Q1 change | Top-lift change |
|---|---|---:|---:|---:|---:|
| A1-013 | V2F1 | +.004016 | +.002971 | -.004702 | -.013038 |
| A1-013 | V2F2 | +.001534 | -.001735 | -.021024 | -.008008 |
| A1-013 | V2F3 | -.001373 | -.002427 | -.002794 | +.001867 |
| A1-013 | V2F4 | +.002221 | +.002275 | +.007390 | +.011511 |
| A1-013 | V2F5 | -.001450 | -.001839 | -.002900 | -.010732 |
| A1-013 | V2F6 | -.011678 | -.009526 | -.000601 | -.003502 |
| A2-014 | V2F1 | +.003499 | +.003719 | -.005428 | +.004346 |
| A2-014 | V2F2 | +.002146 | -.005397 | +.002298 | -.001413 |
| A2-014 | V2F3 | -.005312 | -.002945 | -.003812 | -.001401 |
| A2-014 | V2F4 | -.007239 | -.006568 | -.009996 | +.008633 |
| A2-014 | V2F5 | +.001414 | -.003110 | -.008052 | -.002683 |
| A2-014 | V2F6 | +.000620 | +.005789 | -.008226 | -.010213 |

## Gate detail

### A1 Impact/Absorption — ordinal 013

Absolute sanity passed completely: all metrics finite, positive PR delta on
6/6, and positive Q5-Q1 on 6/6.

Paired gate failed:

- nonnegative PR folds: `3/6` (required `>=5/6`);
- median PR improvement: `+0.0000801749` (required `>=+0.0015`);
- q25 PR improvement: `-0.0014309018` (required `>=0`);
- worst PR improvement: `-0.0116775888` (required `>=-0.0030`);
- median ROC change: `-0.0017871283` (passes ROC threshold);
- median Q5-Q1 change: `-0.0028469425` (required `>=0`);
- nonnegative Q5-Q1 folds: `1/6` (required `>=4/6`);
- F5/F6 PR changes: `-0.0014500930`, `-0.0116775888`;
- F5/F6 each >= -0.0030: `false`;
- F5/F6 median PR change: `-0.0065638409` (required `>=0`);
- final verdict: `FAIL`.

### A2 Persistent Directional Participation — ordinal 014

Absolute sanity passed completely: all metrics finite, positive PR delta on
6/6, and positive Q5-Q1 on 6/6.

Paired gate failed:

- nonnegative PR folds: `4/6` (required `>=5/6`);
- median PR improvement: `+0.0010168334` (required `>=+0.0015`);
- q25 PR improvement: `-0.0038286813` (required `>=0`);
- worst PR improvement: `-0.0072388702` (required `>=-0.0030`);
- median ROC change: `-0.0030273322` (required `>=-0.0020`);
- median Q5-Q1 change: `-0.0067399084` (required `>=0`);
- nonnegative Q5-Q1 folds: `1/6` (required `>=4/6`);
- F5/F6 PR changes: `+0.0014138400`, `+0.0006198268`;
- F5/F6 each >= -0.0030: `true`;
- F5/F6 median PR change: `+0.0010168334` (passes late PR rule);
- final verdict: `FAIL`.

## Top-decile overlap diagnostics

| Challenger | Fold | Jaccard | Overlap rows | Entrants | Exits |
|---|---|---:|---:|---:|---:|
| A1-013 | V2F1 | .463741 | 1458 | 843 | 843 |
| A1-013 | V2F2 | .438347 | 1294 | 829 | 829 |
| A1-013 | V2F3 | .424202 | 1276 | 866 | 866 |
| A1-013 | V2F4 | .461619 | 1317 | 768 | 768 |
| A1-013 | V2F5 | .487881 | 1711 | 898 | 898 |
| A1-013 | V2F6 | .479706 | 2222 | 1205 | 1205 |
| A2-014 | V2F1 | .446715 | 1421 | 880 | 880 |
| A2-014 | V2F2 | .430593 | 1278 | 845 | 845 |
| A2-014 | V2F3 | .433735 | 1296 | 846 | 846 |
| A2-014 | V2F4 | .472458 | 1338 | 747 | 747 |
| A2-014 | V2F5 | .485340 | 1705 | 904 | 904 |
| A2-014 | V2F6 | .444164 | 2108 | 1319 | 1319 |

These are diagnostics only and were not promotion gates.

## Runtime and artifacts

Output directory:

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v4_a_participation_first_pass_run_20260810_001/`

Environment: Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`, PyArrow `23.0.1`,
scikit-learn `1.8.0`, Windows 11.

- control runtime: `34.6119712s`;
- A1 runtime: `33.0567386s`;
- A2 runtime: `34.9773359s`;
- total runtime: `108.8414925s`.

| Artifact | SHA-256 |
|---|---|
| summary | `eea9f1b9b8c0ed8a4d29e133e14621c2dbf9bf028e73e75b0096382bf4fe30da` |
| control equivalence | `ed15bef7b6bed9922bd0fafc68a6136dfa667b77e825759c5f9622fc76b821bd` |
| metrics | `2cdb44edf23f97a50c73ad12aa4e19277705caeee27b4e8507fa09fe2ac79a78` |
| predictions | `6c08c324deb38df5b1d4712a1e9e9a140698b281df18330e432a35bef5f7d8c7` |
| paired | `6fedb0ccebea548c9e93ba6c14ee5276c9909294eccae503ecc8f283d89a1796` |
| top-decile overlap | `1b13cde9ade3753b550468b54c63617cfa271a2f08183cea07656f5548796e80` |
| verdict | `5e03cb3e154096e1f4d7266e091bb273931765e1eb67491606e051919731a09e` |
| runtime | `1311a9ad5906f44c7d121bbee1db72fc9a161827a709a4b528d9b3b1ae883395` |

Model hashes for all 18 fold models:

| Candidate/fold | Model SHA-256 |
|---|---|
| control-012/V2F1 | `f8afbd95177332706bbe29968cb0af2444adaf37b5a131d808f9e258f2b9d2e3` |
| control-012/V2F2 | `569ae54c04659789920efa285d880295e1e0d548fb3d000739f879f69a58632a` |
| control-012/V2F3 | `16c275bb941c03c3e5d06c35217c021ee6c05eaa4c39278204a60401c3bfa437` |
| control-012/V2F4 | `7612a5c1007c29f2619d78f8af443f0e738b4f6791207261be521249a689703e` |
| control-012/V2F5 | `b502b8d05d48b21944ccdc64dfaee90fda6ed3bbe46e01ae0557ffb53de189ad` |
| control-012/V2F6 | `81899c997cbf861c561b27ba59445c2deacda51e6df7b47d204fdd96aea460f9` |
| A1-013/V2F1 | `fa9fdd8df8383b2a51b8af10ec2a76385d1fd705497a55e18ddef9776133723b` |
| A1-013/V2F2 | `9ebc6879236ce896b5572bf47e6d947e4054e2598fa42ba6a25925542583dadc` |
| A1-013/V2F3 | `55331a4a10a34c8e2447174ebfe94f7a653c5d667bd783206ccbbb7e07461cc3` |
| A1-013/V2F4 | `3860a0b0f87948cbb812faae1374b6c2140f9410bc05527232cabdde45ff6e46` |
| A1-013/V2F5 | `91d90dbabd22364570b187c644747f4840d598842fc25ace5688f8bd24543674` |
| A1-013/V2F6 | `792081be8c844576f21e6034f3c9983459ef1fd26f15d329302d1857d3a710ec` |
| A2-014/V2F1 | `e8fa691e20f6769a410819b3fd0e9037e825c08a6fc75b037ded0c90e084e9bf` |
| A2-014/V2F2 | `0f81e0cbac3ef3ec20af01a34fd83963a679aaebd5057f06e7531c14fe7b7fe8` |
| A2-014/V2F3 | `c58611651a4cc7b493b31e40aaa29942c75126945f7c22a190eaa8a49778318f` |
| A2-014/V2F4 | `96911f36774a510a3e4584304abda014e4b4c3b76417ee7a9fe373c8ab0b309d` |
| A2-014/V2F5 | `d38cbb544c0dc27ef6bec6648faa02585cdc329880bcc7f2e98bf16b20deba48` |
| A2-014/V2F6 | `eec4425675a1313bc407ea7be51abeaa2fcd4453a6091da2db87acf81f65c4a4` |

## Accounting and boundaries

- candidate ordinals viewed: `012`, `013`, `014`;
- cumulative historical evaluated-candidate count: `12`;
- V4-A survivors: none;
- integration authorized by result: `false`;
- integration executed: `false`;
- session `1225+`: not materialized or scored;
- post-2026-07-31 fresh-forward outcomes: untouched;
- `FORWARD_OUTCOME_ACCESS_STARTED`: not written;
- no V4-B, calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly,
  paper/live, or main merge started.

The V4-A Participation first-pass family has no surviving challenger under the
frozen gates. Stop for ChatGPT review; do not rescue or automatically start an
integration or later V4 family.
