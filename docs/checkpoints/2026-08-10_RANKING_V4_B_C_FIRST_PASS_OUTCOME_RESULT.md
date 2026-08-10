# Ranking V4-B + V4-C First-Pass Outcome Result

Date: 2026-08-10 (Asia/Jakarta)
Status: COMPLETE — FROZEN HISTORICAL-DEVELOPMENT FIRST PASS

## Decision

The separately authorized atomic first pass completed for both frozen families.
All three challengers failed the unchanged runner gate:

- V4-B ordinal 016 B1 Path Coherence / Jump Concentration: FAIL;
- V4-B ordinal 017 B2 Range Acceptance / Rejection: FAIL;
- V4-C ordinal 019 Cross-Sectional Opportunity Dispersion: FAIL.

The exact controls passed V3-B equivalence in both runners. No survivor exists,
so no B1+B2 integration and no B/C integration was created.

## Execution identity and preflight

- branch: research/idx-ranking-v2-spec-v1;
- execution HEAD before documentation: f605e1be5964714db3038a2e6b315b9256315c40;
- full pytest: 357 passed, 0 failed, 3 warnings, 15.87s;
- pytest shell duration: 18.100s;
- warnings: three existing pandas FutureWarnings in the curated-identity and
  tradability-anchor reconstruction tests.

All pinned identities matched before either runner:

| Artifact | Path | SHA-256 / Git blob |
|---|---|---|
| V4-C cache | D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_c_cross_sectional_context_prepare_20260810_001\ranking_v4_c_cross_sectional_context_prepared_cache.parquet | 480f09488c89128859921abe0617e51d04ac05d0ddfc42fb8f4d0c063f2b255e |
| V4-C manifest | D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_c_cross_sectional_context_prepare_20260810_001\ranking_v4_c_cross_sectional_context_prepared_cache_manifest.json | 33ba2b39ce10476bea0566b2d240806a9d258ebe8c5f1b61733a539a397b7737 |
| V4-C spec Git blob | docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md | 43f222f31c7c0ea15e870d22b066aae95858c81f |
| V4-B cache | D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_price_path_prepare_20260810_001\ranking_v4_b_price_path_prepared_cache.parquet | 8c59200d284e73867a3ff3566473f7dc7dd4aa0a2bfd42917ef4e08c761d1c68 |
| V4-B manifest | D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_price_path_prepare_20260810_001\ranking_v4_b_price_path_prepared_cache_manifest.json | d30c7e4f0841bbddd479fdc0b8c62b1028dcf8f107277b5a8a250d9725243b2f |
| V4-B spec Git blob | docs/RANKING_V4_B_PRICE_PATH_SPEC_V1.md | a750c28831b95b1c88640c5879289da5f2c05446 |
| V3-B F1-F4 metrics | D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1\ranking_v3_b_structure_lite_f1_f4_metrics.csv | 0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357 |
| V3-B F1-F4 predictions | D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1\ranking_v3_b_structure_lite_f1_f4_predictions.parquet | c7761dd0bd93340381b28234537bf7a42e829eae0f214ec8173d8bc1f6f2e4e1 |
| V3-B F5-F6 metrics | D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_run_20260810_001\ranking_v3_final_structure_lite_f5_f6_metrics.csv | 5e758e468cf883212fdb11c64d63f8ab3cf86c20a04a60edbc651205bc8f6d25 |
| V3-B F5-F6 predictions | D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_final_structure_lite_late_dev_run_20260810_001\ranking_v3_final_structure_lite_f5_f6_predictions.parquet | 64cf1c04640740c5906db03e1ba86290790904daca2971e61c00212de893715b |

Both manifests were still pre-outcome: post_1224_materialized=false,
outcome_metrics_computed=false, fresh_forward_accessed=false, and
integration_candidate_materialized=false.

## Frozen execution sequence

V4-C ran first with all stdout/stderr redirected and was not opened before
V4-B completed:

- output: D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_c_first_pass_run_20260810_002
- redirected stdout: D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_c_first_pass_run_20260810_002.stdout.json
- exit code: 0;
- shell duration: 42.470s.

V4-B then ran in a separate output directory without inspecting V4-C:

- output: D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_first_pass_run_20260810_002
- redirected stdout: D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_first_pass_run_20260810_002.stdout.json
- exit code: 0;
- shell duration: 63.862s.

Only after both exit codes were zero were the two result sets opened.

## V4-C result

Hypothesis: V4-C-CROSS-SECTIONAL-CONTEXT-V1.

Candidates 018 exact V3-B control and 019 frozen four-feature dispersion
challenger were run atomically over V2F1-V2F6.

### Control equivalence

- status: V4_C_V3_B_CONTROL_EQUIVALENCE_PASS;
- rows: 144,223;
- max score absolute difference: 0.0;
- maximum metric absolute differences:
  - positive_rate: 5.55111512312578e-17;
  - pr_auc: 5.55111512312578e-17;
  - pr_auc_delta_vs_base: 8.32667268468867e-17;
  - roc_auc: 0.0;
  - q1_tp_rate: 5.55111512312578e-17;
  - q5_tp_rate: 5.55111512312578e-17;
  - q5_minus_q1: 8.32667268468867e-17;
  - top_decile_tp_rate: 5.55111512312578e-17;
  - top_decile_lift: 8.32667268468867e-17.

### Per-fold metrics

Values are prevalence, PR-AUC, PR delta versus base, ROC-AUC, Q1 TP rate,
Q5 TP rate, Q5-Q1, and top-decile lift.

| Candidate | Fold | Prev | PR-AUC | PR delta | ROC-AUC | Q1 | Q5 | Q5-Q1 | Top lift |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 018 control | V2F1 | 0.380163092 | 0.409788783 | 0.029625692 | 0.528301475 | 0.329682611 | 0.426783754 | 0.097101143 | 0.070945122 |
| 018 control | V2F2 | 0.388899595 | 0.419739983 | 0.030840387 | 0.533043862 | 0.349464981 | 0.435383882 | 0.085918901 | 0.053870070 |
| 018 control | V2F3 | 0.413922726 | 0.427591281 | 0.013668555 | 0.528880383 | 0.391982717 | 0.440198160 | 0.048215443 | 0.028187452 |
| 018 control | V2F4 | 0.384634242 | 0.425901747 | 0.041267505 | 0.514575367 | 0.345220406 | 0.407910701 | 0.062690295 | 0.013926909 |
| 018 control | V2F5 | 0.462198308 | 0.489946120 | 0.027747812 | 0.533180622 | 0.438506876 | 0.492266048 | 0.053759172 | 0.038759914 |
| 018 control | V2F6 | 0.336898712 | 0.369058096 | 0.032159384 | 0.504982324 | 0.309109823 | 0.357814336 | 0.048704513 | 0.024641994 |
| 019 challenger | V2F1 | 0.380163092 | 0.420027241 | 0.039864149 | 0.528968436 | 0.333258829 | 0.435565313 | 0.102306484 | 0.083548338 |
| 019 challenger | V2F2 | 0.388899595 | 0.422049518 | 0.033149922 | 0.529946297 | 0.353599222 | 0.420839294 | 0.067240072 | 0.051985944 |
| 019 challenger | V2F3 | 0.413922726 | 0.420345957 | 0.006423232 | 0.518335982 | 0.389822372 | 0.431705591 | 0.041883219 | 0.036590813 |
| 019 challenger | V2F4 | 0.384634242 | 0.426532535 | 0.041898293 | 0.542692583 | 0.353392769 | 0.414705169 | 0.061312400 | 0.024478468 |
| 019 challenger | V2F5 | 0.462198308 | 0.498485923 | 0.036287615 | 0.531922123 | 0.423968566 | 0.506767208 | 0.082798642 | 0.065973406 |
| 019 challenger | V2F6 | 0.336898712 | 0.342478669 | 0.005579957 | 0.490599909 | 0.316540348 | 0.353407756 | 0.036867408 | 0.013845379 |

Top-decile TP rate:

| Fold | Control 018 | Challenger 019 |
|---|---:|---:|
| V2F1 | 0.451108214 | 0.463711430 |
| V2F2 | 0.442769666 | 0.440885539 |
| V2F3 | 0.442110177 | 0.450513539 |
| V2F4 | 0.398561151 | 0.409112710 |
| V2F5 | 0.500958222 | 0.528171713 |
| V2F6 | 0.361540706 | 0.350744091 |

### Paired changes and gate

| Fold | PR improvement | ROC change | Q5-Q1 change | Top lift change |
|---|---:|---:|---:|---:|
| V2F1 | 0.010238458 | 0.000666960 | 0.005205341 | 0.012603216 |
| V2F2 | 0.002309535 | -0.003097565 | -0.018678829 | -0.001884126 |
| V2F3 | -0.007245324 | -0.010544401 | -0.006332223 | 0.008403361 |
| V2F4 | 0.000630788 | 0.028117215 | -0.001377895 | 0.010551559 |
| V2F5 | 0.008539803 | -0.001258500 | 0.029039471 | 0.027213492 |
| V2F6 | -0.026579427 | -0.014382416 | -0.011837105 | -0.010796615 |

Frozen gate detail:

- absolute_all_metrics_finite=true;
- absolute_pr_delta_positive_6_of_6=true;
- absolute_q5_q1_positive_6_of_6=true;
- paired_pr_nonnegative_folds=4; required at least 5;
- median PR improvement=0.001470161; required at least 0.0015;
- q25 PR improvement=-0.005276296; required nonnegative;
- worst PR improvement=-0.026579427; allowed floor -0.003;
- median ROC change=-0.002178033; required at least -0.002;
- median Q5-Q1 change=-0.003855059; required nonnegative;
- Q5-Q1 nonnegative folds=2; required at least 4;
- late PR each at least -0.003=false;
- late median PR nonnegative=false;
- median top-decile lift change=0.009477460 (diagnostic only).

Final V4-C ordinal 019 verdict: FAIL. Top-decile Jaccard by fold was
V2F1 0.449449, V2F2 0.377677, V2F3 0.388655, V2F4 0.411168,
V2F5 0.409889, and V2F6 0.374649. Entrants/exits were respectively
874/874, 959/959, 943/943, 870/870, 1092/1092, and 1559/1559.

V4-C runner runtime was 40.226328s: control 19.795769s and challenger
18.955923s.

V4-C output hashes:

- control equivalence: 9e611bf64f2b5c8838c98e864c2ca656cc3146395c29d48479deb8a06543948e;
- metrics: e4112e377ee8d0fa4fdbc872a660f72c82abcbbd5ae0cc8e6cf7f5825e018d78;
- predictions: b7ed0c745aa1c68a84405d9f826a629afac96de862a5eeda1ac738e5bc848ea5;
- paired: e6336b83cb2f03c2eb2ed5f1553f26c6ffd347aa27c787e1d2dd50bdb0a0ec7a;
- top-decile overlap: fed699cdc645e0d85b0c70b6886d6cd92d25668a4bba811b5b133c1126a95511;
- verdict: ad88ec2bd4de561cea5d8860c49f7b575c80e03643cf803fea1f0d7de90e590f;
- runtime: e41b7f2208a147a7bfb8be630cc337a5b8401adfcad376a948d8e2bb7060e715;
- summary: bc5fd8a40c217aeef3fc3a2e85be5dfdbb6f96bd79c6b58271c884c079be005f.

The full per-fold model hash map is retained in the output summary's
artifact_sha256 field.

## V4-B result

Hypothesis: V4-B-PRICE-PATH-V1.

Candidates 015 exact V3-B control, 016 B1 Path Coherence / Jump
Concentration, and 017 B2 Range Acceptance / Rejection were run atomically
over V2F1-V2F6.

### Control equivalence

- status: V4_B_V3_B_CONTROL_EQUIVALENCE_PASS;
- rows: 144,223;
- max score absolute difference: 0.0;
- maximum metric differences matched the V4-C control values above:
  positive_rate 5.55111512312578e-17, PR-AUC 5.55111512312578e-17,
  PR delta 8.32667268468867e-17, ROC-AUC 0.0, Q1 5.55111512312578e-17,
  Q5 5.55111512312578e-17, Q5-Q1 8.32667268468867e-17,
  top-decile TP rate 5.55111512312578e-17, top-decile lift
  8.32667268468867e-17.

### Per-fold metrics — B1 ordinal 016

| Fold | Prev | PR-AUC | PR delta | ROC-AUC | Q1 | Q5 | Q5-Q1 | Top lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V2F1 | 0.380163092 | 0.412233709 | 0.032070617 | 0.529665453 | 0.333035315 | 0.431174533 | 0.098139218 | 0.087025087 |
| V2F2 | 0.388899595 | 0.422479110 | 0.033579515 | 0.531977869 | 0.350437743 | 0.432522651 | 0.082084908 | 0.061877607 |
| V2F3 | 0.413922726 | 0.423283260 | 0.009360535 | 0.522723181 | 0.396303409 | 0.432413305 | 0.036109896 | 0.022585211 |
| V2F4 | 0.384634242 | 0.414478774 | 0.029844532 | 0.506068127 | 0.361812779 | 0.404998787 | 0.043186008 | 0.014886142 |
| V2F5 | 0.462198308 | 0.491327173 | 0.029128865 | 0.536522357 | 0.433595285 | 0.495359629 | 0.061764344 | 0.066356694 |
| V2F6 | 0.336898712 | 0.365841758 | 0.028943047 | 0.506310926 | 0.308366771 | 0.356492362 | 0.048125591 | 0.018514186 |

### Per-fold metrics — B2 ordinal 017

| Fold | Prev | PR-AUC | PR delta | ROC-AUC | Q1 | Q5 | Q5-Q1 | Top lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V2F1 | 0.380163092 | 0.420183367 | 0.040020276 | 0.540223458 | 0.313142602 | 0.450933041 | 0.137790439 | 0.088328868 |
| V2F2 | 0.388899595 | 0.441634916 | 0.052735320 | 0.545019542 | 0.321984436 | 0.435383882 | 0.113399446 | 0.054812133 |
| V2F3 | 0.413922726 | 0.426186743 | 0.012264017 | 0.530862462 | 0.365578493 | 0.442793112 | 0.077214619 | 0.045927881 |
| V2F4 | 0.384634242 | 0.429110340 | 0.044476098 | 0.524218552 | 0.343239227 | 0.410822615 | 0.067583389 | 0.022080386 |
| V2F5 | 0.462198308 | 0.493919915 | 0.031721607 | 0.540166393 | 0.433595285 | 0.503673627 | 0.070078342 | 0.049875284 |
| V2F6 | 0.336898712 | 0.359340560 | 0.022441848 | 0.502719908 | 0.300341804 | 0.357814336 | 0.057472532 | 0.020556789 |

Top-decile TP rate:

| Fold | Control 015 | B1 016 | B2 017 |
|---|---:|---:|---:|
| V2F1 | 0.451108214 | 0.467188179 | 0.468491960 |
| V2F2 | 0.442769666 | 0.450777202 | 0.443711729 |
| V2F3 | 0.442110177 | 0.436507937 | 0.459850607 |
| V2F4 | 0.398561151 | 0.399520383 | 0.406714628 |
| V2F5 | 0.500958222 | 0.528555002 | 0.512073591 |
| V2F6 | 0.361540706 | 0.355412898 | 0.357455500 |

### Paired changes

| Candidate | Fold | PR improvement | ROC change | Q5-Q1 change | Top lift change |
|---|---|---:|---:|---:|---:|
| 016 | V2F1 | 0.002444925 | 0.001363978 | 0.001038075 | 0.016079965 |
| 016 | V2F2 | 0.002739127 | -0.001065993 | -0.003833993 | 0.008007537 |
| 016 | V2F3 | -0.004308021 | -0.006157202 | -0.012105546 | -0.005602241 |
| 016 | V2F4 | -0.011422974 | -0.008507241 | -0.019504287 | 0.000959233 |
| 016 | V2F5 | 0.001381054 | 0.003341734 | 0.008005172 | 0.027596780 |
| 016 | V2F6 | -0.003216338 | 0.001328602 | -0.000578922 | -0.006127809 |
| 017 | V2F1 | 0.010394584 | 0.011921983 | 0.040689295 | 0.017383746 |
| 017 | V2F2 | 0.021894933 | 0.011975680 | 0.027480545 | 0.000942063 |
| 017 | V2F3 | -0.001404538 | 0.001982079 | 0.028999176 | 0.017740430 |
| 017 | V2F4 | 0.003208593 | 0.009643185 | 0.004893093 | 0.008153477 |
| 017 | V2F5 | 0.003973795 | 0.006985771 | 0.016319171 | 0.011115370 |
| 017 | V2F6 | -0.009717536 | -0.002262417 | 0.008768019 | -0.004085206 |

### Frozen gate detail

B1 ordinal 016:

- absolute_all_metrics_finite=true;
- absolute_pr_delta_positive_6_of_6=true;
- absolute_q5_q1_positive_6_of_6=true;
- paired PR nonnegative folds=3; required at least 5;
- median PR improvement=-0.000917642;
- q25 PR improvement=-0.004035100;
- worst PR improvement=-0.011422974;
- median ROC change=0.000131304;
- median Q5-Q1 change=-0.002206457;
- Q5-Q1 nonnegative folds=2; required at least 4;
- late PR each at least -0.003=false;
- late median PR nonnegative=false;
- median top-decile lift change=0.004483385 (diagnostic only).

B2 ordinal 017:

- absolute_all_metrics_finite=true;
- absolute_pr_delta_positive_6_of_6=true;
- absolute_q5_q1_positive_6_of_6=true;
- paired PR nonnegative folds=4; required at least 5;
- median PR improvement=0.003591194;
- q25 PR improvement=-0.000251256;
- worst PR improvement=-0.009717536;
- median ROC change=0.008314478;
- median Q5-Q1 change=0.021899858;
- Q5-Q1 nonnegative folds=6;
- late PR each at least -0.003=false;
- late median PR nonnegative=false;
- median top-decile lift change=0.009634424 (diagnostic only).

Final V4-B verdicts: 016 FAIL and 017 FAIL. Survivors=[] and
integration_candidate_materialized=false.

Top-decile Jaccard for B1 by V2F1..V2F6 was
0.465138, 0.425789, 0.373077, 0.453468, 0.467792, and 0.487736;
entrants/exits were 840/840, 855/855, 978/978, 784/784, 946/946, and
1180/1180.

Top-decile Jaccard for B2 by V2F1..V2F6 was
0.377432, 0.332287, 0.315321, 0.333973, 0.385555, and 0.436295;
entrants/exits were 1040/1040, 1064/1064, 1115/1115, 1041/1041,
1157/1157, and 1345/1345.

V4-B runner runtime was 61.380614s: control 20.127628s, B1 19.293055s,
and B2 19.486082s.

V4-B output hashes:

- control equivalence: 18c201ede7a6c82479e665a2112251726fae7d8783b1b92ccf6af84242559e1d;
- metrics: f6a7618e53d8ee1844aad9856ed7af33bb97b723b1dfc8ef4507a4e8ba95c73d;
- predictions: c2fe033d1cc37c75172d22fdb2071eb9460fd21ee3419d53c0c9953a7a76997c;
- paired: 65b172ff524ff4740d4afe8a671f7979c1054ed18ed0d416fc813814f030608e;
- top-decile overlap: bdf4ec43e2e4d0a39fcead57dec6c4beab973f055d3a71ce8a0f9c2eca2cad06;
- verdict: e3af53a7fe863f3976920180f3caa934da72f1997d045197775ba565bd41698a;
- runtime: 2be04fbd02399bd74a26e764836d380a90fcd409a9f85855bc9b4e554c707701;
- summary: 42ad48fda74b887e1bc5416e92c033036f33fb677d5326cbae27aae227a4b1ca.

The full per-fold model hash map is retained in the output summary's
artifact_sha256 field.

## Permanent accounting and boundary

Viewed candidate ordinals are 015, 016, 017, 018, and 019. The cumulative
historical evaluated-candidate count is now 17. V2F1-V2F6 remain historical
development evidence, not independent validation.

No rescue, alternate feature, threshold change, model change, B1+B2
integration, B/C integration, or additional V4 family was started.
post_1224_materialized=false, fresh_forward_accessed=false, and
forward_marker_written=false in both result manifests. Session 1225+ was not
materialized, post-2026-07-31 fresh-forward outcomes were not accessed, and
FORWARD_OUTCOME_ACCESS_STARTED was not written.

## Files

- V4-C output root:
  D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_c_first_pass_run_20260810_002
- V4-B output root:
  D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v4_b_first_pass_run_20260810_002
- result handoff:
  coordination/handoffs/IDX-RANKING-V4-B-C-FIRST-PASS-OUTCOME-RESULT.md
