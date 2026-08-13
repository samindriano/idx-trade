# Checkpoint — Ranking V3-A Recency F1-F4 Discovery Result

Date: 2026-08-10 (Asia/Jakarta)

Status: **`V3_A_RECENCY_KILL_KEEP_V2_CONTROL`**

## Scope and source identity

- branch: `research/idx-ranking-v2-spec-v1`;
- source/run HEAD: `362510997e3db41e81b21ec8e7422308338fbef1`;
- implementation code commit: `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`;
- run mode: sequential reference Python runner;
- discovery folds: V2F1, V2F2, V2F3, V2F4 only;
- sealed folds: V2F5 and V2F6 were not scored, loaded, or summarized for V3-A.

This is historical development evidence only. No independent-validation claim
is made.

## Preflight and pytest

The exact prepared inputs were verified:

| Artifact | Path | SHA-256 |
|---|---|---|
| prepared table | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet` | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` |
| prepared manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_cache_manifest.json` | `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143` |
| V2 HGB summary | `...\ranking_v2_candidate_orchestra_20260810\HGB_XS_MARKET\ranking_v2_hgb_xs_market_summary.json` | `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d` |
| V2 HGB predictions | `...\ranking_v2_candidate_orchestra_20260810\HGB_XS_MARKET\ranking_v2_hgb_xs_market_predictions.parquet` | `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179` |

Full repository pytest, run from the explicit `idx-trade` root:

**`240 passed, 3 warnings in 19.04 s`**

Warnings were three existing pandas `FutureWarning` instances in curated
identity/tradability concatenation tests. No test failed.

The Windows checkout has `core.autocrlf=true`; the raw working-tree addendum
therefore did not reproduce its committed Git blob when the runner calculated a
raw blob hash. The run used an uncommitted runtime-only copy reconstructed from
the exact committed Git blob. The repo file and implementation were not
changed. The canonical addendum Git blob remained
`1ee532c849636c47dab12ba3702ce7590abfcd74`.

## Control equivalence

**`V3_A_CONTROL_EQUIVALENCE_PASS`**

- folds: V2F1-V2F4;
- rows: `84,732`;
- maximum row-level score absolute difference: `0.0`;
- maximum absolute difference for prevalence, PR-AUC, PR-AUC-minus-prevalence,
  ROC-AUC, Q1 TP rate, Q5 TP rate, Q5-Q1, top-decile TP rate, and top-decile
  lift: `0.0` for every metric;
- score tolerance: `1e-12`, `rtol=0`;
- metric tolerance: `1e-12`, `rtol=0`.

Only after this pass did the runner fit H=252 and H=504.

## F1-F4 fold metrics

| Candidate | Fold | Rows | Prevalence | PR-AUC | PR-AUC - base | ROC-AUC | Q1 TP | Q5 TP | Q5-Q1 | Top-decile TP | Top-decile lift |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Control | V2F1 | 22564 | 0.3801630916504166 | 0.40184058341126827 | 0.021677491760851653 | 0.5255579872914915 | 0.3370585605721949 | 0.42107574094401756 | 0.08401718037182265 | 0.4372012168622338 | 0.05703812521181717 |
| Control | V2F2 | 20756 | 0.3888995952977452 | 0.4178986853528688 | 0.028999090055123578 | 0.5232616177283664 | 0.3550583657587549 | 0.4253695755841679 | 0.070311209825413 | 0.43994347621290625 | 0.051043880915161044 |
| Control | V2F3 | 21016 | 0.41392272554244386 | 0.4227122108856597 | 0.00878948534321583 | 0.5273786274512129 | 0.39942390782525206 | 0.43807501769285206 | 0.03865110986760001 | 0.4565826330532213 | 0.04265990751077742 |
| Control | V2F4 | 20396 | 0.3846342420082369 | 0.42292912713729935 | 0.03829488512906243 | 0.5128270182194569 | 0.3481921743437345 | 0.40572676534821644 | 0.05753459100448194 | 0.40863309352517985 | 0.02399885151694292 |
| H252 | V2F1 | 22564 | 0.3801630916504166 | 0.4094349532012082 | 0.02927186155079159 | 0.5285419775102684 | 0.34689316048278945 | 0.41822173435784854 | 0.07132857387505909 | 0.4406779661016949 | 0.06051487445127829 |
| H252 | V2F2 | 20756 | 0.3888995952977452 | 0.42380798638584133 | 0.034908391088096125 | 0.5200698590875122 | 0.3523832684824903 | 0.43443013829279925 | 0.08204686981030895 | 0.45171926519076777 | 0.06281966989302257 |
| H252 | V2F3 | 21016 | 0.41392272554244386 | 0.4165005916122596 | 0.0025778660698157485 | 0.5160945785324627 | 0.3963034085453673 | 0.43713139891483843 | 0.04082799036947116 | 0.4449112978524743 | 0.030988572310030438 |
| H252 | V2F4 | 20396 | 0.3846342420082369 | 0.4137362061124752 | 0.029101964104238265 | 0.508352156471196 | 0.3514115898959881 | 0.4139771900024266 | 0.06256560010643852 | 0.40431654676258993 | 0.01968230475435301 |
| H504 | V2F1 | 22564 | 0.3801630916504166 | 0.4069646152202716 | 0.02680152356985499 | 0.5274416365871251 | 0.34309342869915066 | 0.41888035126234907 | 0.07578692256319841 | 0.4293785310734463 | 0.049215439423029694 |
| H504 | V2F2 | 20756 | 0.3888995952977452 | 0.41980033772442127 | 0.030900742426676064 | 0.5246111480825831 | 0.34922178988326846 | 0.43109203624225084 | 0.08187024635898238 | 0.43523316062176165 | 0.046333565324016446 |
| H504 | V2F3 | 21016 | 0.41392272554244386 | 0.4209242689352689 | 0.007001543392825049 | 0.5226580782149461 | 0.39702352376380223 | 0.4345364472753008 | 0.03751292351149854 | 0.43744164332399627 | 0.023518917781552406 |
| H504 | V2F4 | 20396 | 0.3846342420082369 | 0.38839902555209627 | 0.0037647835438593402 | 0.4787722891114133 | 0.3395245170876672 | 0.41494782819703957 | 0.07542331110937239 | 0.4119904076738609 | 0.027356165665623988 |

## Aggregates and paired deltas

| Candidate | Median PR delta | Q25 PR delta | Worst PR delta | Positive PR folds | Median ROC | ROC > .5 folds | Median Q5-Q1 | Worst Q5-Q1 | Positive Q5-Q1 folds | Median top-decile lift | Absolute gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Control | 0.025338290907987615 | 0.018455490156442697 | 0.00878948534321583 | 4 | 0.524409802509929 | 4 | 0.06392290041494747 | 0.03865110986760001 | 4 | 0.04685189421296923 | PASS |
| H252 | 0.029186912827514927 | 0.022470939595632636 | 0.0025778660698157485 | 4 | 0.5180822188099874 | 4 | 0.0669470869907488 | 0.04082799036947116 | 4 | 0.04575172338065436 | PASS |
| H504 | 0.01690153348134002 | 0.006192353430583622 | 0.0037647835438593402 | 4 | 0.5236346131487646 | 3 | 0.0756051168362854 | 0.03751292351149854 | 4 | 0.03684486549482022 | PASS |

| Candidate | Fold | PR delta improvement | ROC change | Q5-Q1 change | Top-decile lift change |
|---|---|---:|---:|---:|---:|
| H252 | V2F1 | 0.0075943697899399365 | 0.002983990218776933 | -0.012688606496763566 | 0.003476749239461119 |
| H252 | V2F2 | 0.005909301032972547 | -0.003191758640854192 | 0.011735659984895952 | 0.011775788977861523 |
| H252 | V2F3 | -0.006211619273400082 | -0.011284048918750234 | 0.002176880501871148 | -0.01167133520074698 |
| H252 | V2F4 | -0.009192921024824163 | -0.004474861748260839 | 0.005031009101956585 | -0.004316546762589912 |
| H504 | V2F1 | 0.005124031809003338 | 0.0018836492956335604 | -0.008230257808624242 | -0.007822685788787476 |
| H504 | V2F2 | 0.001901652371552487 | 0.0013495303542166992 | 0.011559036533569378 | -0.004710315591144598 |
| H504 | V2F3 | -0.0017879419503907812 | -0.004720549236266747 | -0.0011381863561014671 | -0.01914098972922501 |
| H504 | V2F4 | -0.03453010158520309 | -0.03405472910804358 | 0.017888720104890454 | 0.0033573141486810676 |

H252 paired aggregate: median PR improvement `-0.00015115912021376743`, q25
`-0.006956944711256102`, worst `-0.009192921024824163`, PR not below control
`2/4`, median ROC change `-0.0038333101945575154`, median Q5-Q1 change
`0.0036039448019138665`, Q5-Q1 not below control `3/4`.

H504 paired aggregate: median PR improvement `0.000056855210580852855`, q25
`-0.009973481859093858`, worst `-0.03453010158520309`, PR not below control
`2/4`, median ROC change `-0.0016855094410250238`, median Q5-Q1 change
`0.005210425088733955`, Q5-Q1 not below control `2/4`.

Both variants are clean and pass absolute sanity but fail the frozen paired
promotion gate. They are therefore `KEEP_DIAGNOSTIC`; neither is promoted.
The deterministic result is `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.

## Runtime

- table read/normalize: `0.2806292 s`;
- Control: `13.9209669 s`;
- H252: `12.5646795 s`;
- H504: `12.5395652 s`;
- total: `40.3661506 s`;
- environment: Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`, PyArrow
  `23.0.1`, scikit-learn `1.8.0`, Windows 11 `10.0.26200`.

## Runtime artifact inventory

All runtime artifacts remain outside Git at:
`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_recency_discovery_20260810_retry1`.

| Relative artifact | SHA-256 |
|---|---|
| `ranking_v3_a_recency_aggregate.json` | `279235e350c30fd65d740675288e0f15589bbbef55dfa71ae63b412f0b66eea8` |
| `ranking_v3_a_recency_f1_f4_metrics.csv` | `fe22292ebad0d553042eb8f48faf3ddb13584e8062776a46d63adfd55bf8c603` |
| `ranking_v3_a_recency_f1_f4_predictions.parquet` | `15969fbc72aeb5fdadc03c75ff83810b92e0af59044ca2450156bed2123685a4` |
| `ranking_v3_a_recency_ledger_rows.json` | `2205fcc39beb944106852077673c3a4c7fdc393403d48012d9875c668ee4536f` |
| `ranking_v3_a_recency_paired_comparison.csv` | `f3730a5a8fa7545c9f863e4d9e65d05bc77ec724e407aedd73d0ad8e3748b33a` |
| `ranking_v3_a_recency_runtime.json` | `aa942d1f2a3a429fdae66bc728ff5abf245c58e5385274b2d501fd88f7ad65e7` |
| `ranking_v3_a_recency_summary.json` | `cf5d50c746ba9d88c74303193f770817588d6ad0fd23f24bb34baeb162e7519f` |
| `ranking_v3_a_recency_verdict.json` | `3b8038bdb9b8721f037c7557091f4c1a802f25688ab1cd13ff89f8ebb6ccbe19` |
| `ranking_v3_a_recency_weight_stats.csv` | `aafd9461fc0d43ce668051dead9db795b28f64ee0c105cd03a6c32755b5a8138` |
| `v3_a_control_equivalence.json` | `e7f2b036d2060de440c7fd8da3d63e1fbc9d8ba37ad2ab3257af4c7a4b89b07f` |
| `control/ranking_v3_recency_v3-a-recency-v1-control-001_v2f1.joblib` | `d8b8d33808d899cfebd050ae35e5cbca1f4c522241553067e7d94e9c70d3a4b3` |
| `control/ranking_v3_recency_v3-a-recency-v1-control-001_v2f2.joblib` | `81339da7d3c9561b60550e9ed5038da1ddcdd1295184edfc98de78d15b366296` |
| `control/ranking_v3_recency_v3-a-recency-v1-control-001_v2f3.joblib` | `90727054e6b409a9eb3d86e472b7d005cce9a2bd816d2349b4ee6a4ed1ad6fb8` |
| `control/ranking_v3_recency_v3-a-recency-v1-control-001_v2f4.joblib` | `53a4cac5cc6232c1d378a6c72b78961b42546abe53bba42687f5238d0e34a2b6` |
| `v3-a-recency-v1-hl252-002/ranking_v3_recency_v3-a-recency-v1-hl252-002_v2f1.joblib` | `cf05ab07890849fdb4a88a4361a424f291cf887f3a5afa3757bb40bd64d15cd1` |
| `v3-a-recency-v1-hl252-002/ranking_v3_recency_v3-a-recency-v1-hl252-002_v2f2.joblib` | `06fe4ecde26d8481cb78332972fb39734ada0ecf04a5f30e8b8691d721d588f5` |
| `v3-a-recency-v1-hl252-002/ranking_v3_recency_v3-a-recency-v1-hl252-002_v2f3.joblib` | `06b4c7125aa8a35de85bd94f27de5aac3d42448c196757b83b3c89d43014e2ef` |
| `v3-a-recency-v1-hl252-002/ranking_v3_recency_v3-a-recency-v1-hl252-002_v2f4.joblib` | `cb74a5d0e5f43e78ee4b138564f5741419911b93c9f2fe3345829c798b31e294` |
| `v3-a-recency-v1-hl504-003/ranking_v3_recency_v3-a-recency-v1-hl504-003_v2f1.joblib` | `06361fff02f16deaffdf33caf8e12560780064ab3131c893599b7006578236e2` |
| `v3-a-recency-v1-hl504-003/ranking_v3_recency_v3-a-recency-v1-hl504-003_v2f2.joblib` | `a88be63e68bd19acdbd7fc0f95dd2856805af29e6e46cb3c27` |
| `v3-a-recency-v1-hl504-003/ranking_v3_recency_v3-a-recency-v1-hl504-003_v2f3.joblib` | `bfe4a56330f018bf2bc1f147af462629961e353e540b6acaf86fdcf9e79cfa51` |
| `v3-a-recency-v1-hl504-003/ranking_v3_recency_v3-a-recency-v1-hl504-003_v2f4.joblib` | `5c07f9a3ef07b3fe469fcebca81972f46dbf78db6877e33c31639ef80f373aa1` |

## Safety confirmation and stop boundary

- F5/F6: not accessed; `f5_f6_scored=false`;
- reserved post-2026-07-31 V2 fresh-forward outcomes: not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED`: not written by this run;
- V3-B Structure-Lite, calibration, Stage 6, `IDX-VAL-002`, execution-PnL,
  paper/live, and main merge: not started;
- next action: stop for ChatGPT review.
