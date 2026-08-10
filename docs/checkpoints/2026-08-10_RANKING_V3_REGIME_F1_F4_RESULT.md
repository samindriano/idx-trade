# Ranking V3-C Regime-Specialization F1-F4 Discovery Result

Date: 2026-08-10 (Asia/Jakarta)

Status: **`V3_C_REGIME_KILL_KEEP_V2_CONTROL`**

Evidence class: historical development evidence only; not independent
validation, probability calibration, execution evidence, or deployment
authorization.

## Scope and frozen contract

- repository: `samindriano/idx-trade`;
- branch: `research/idx-ranking-v2-spec-v1`;
- run/code commit: `619b511f14d8e929f8f23ed7c001f72fe730566f`;
- hypothesis: `V3-C-REGIME-V1`;
- candidates: exact V2 control ordinal `006`; one NORMAL/STRESS two-expert
  candidate ordinal `007`;
- folds scored: `V2F1`, `V2F2`, `V2F3`, `V2F4` only;
- no Structure-Lite, recency, score alignment, rescaling, blending, or
  fallback was used;
- V2F5/V2F6 and reserved post-2026-07-31 V2 forward outcomes were not
  accessed.

Frozen spec identities:

- spec Git blob: `2a2f48d68f5d3df839c61191d4a11fa870470b00`;
- review-addendum Git blob: `a13c5ae103908311968e38c6ded233b7a1cbd901`.

## Preflight

An unscoped `python -m pytest` invocation selected the parent Project root and
collected unrelated sibling repositories, producing 370 collection errors.
That was an invocation-scope issue, not the IDX Trade suite. The authoritative
rerun used the explicit IDX Trade `pyproject.toml` and `tests` path from the
IDX Trade checkout, with `PYTHONPATH=src` for the source layout:

**`264 passed, 0 failed, 3 warnings in 22.26 s`**

Wrapper wall duration: **24.85 s**. The three warnings are existing pandas
`FutureWarning` instances in curated-identity and tradability-anchor
concatenation tests.

Before cache work, a NumPy 2.4/pandas mixed-row dtype compatibility failure was
found in two V3-C causal-threshold tests. The minimal engineering correction
converts the selected threshold rows to `float` before `np.allclose`; no
regime definition, candidate, model semantics, or gate changed. The
correction is in `tests/test_ranking_v3_regime.py` and is included in the run
commit lineage.

## Frozen input artifact verification

| Artifact | SHA-256 |
|---|---|
| signal-research panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| V2 prepared table | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` |
| V2 prepared manifest | `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143` |
| frozen V2 HGB summary | `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d` |
| frozen V2 HGB predictions | `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179` |

All seven artifacts were found unambiguously and matched exactly.

## Outcome-independent V3-C cache

Output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_regime_prepare_20260810_run1`

- status: `RANKING_V3_C_REGIME_DISCOVERY_CACHE_FROZEN`;
- cache: `216,472` rows / `674` tickers / signal sessions `20..984`;
- cache SHA-256: `1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`;
- manifest SHA-256: `c4b090de65c291af21ea0a49f63d5d2d0dc1acbd18fff1c995494e1212f1418b`;
- context equivalence max absolute differences: `0.0` for all three source
  fields;
- states: `MISSING_WARMUP`, `NORMAL`, `STRESS` only;
- observed stress votes: `{0,1,2,3}`;
- `v2f5_v2f6_materialized=false`;
- `outcome_metrics_computed=false`.

Independent cache checks all passed: exact V2 row identity/order and 25-feature
prefix, no duplicate ticker/date rows, no identity/state nulls, no numeric
infinity, official-session date alignment, and coverage-gate PASS. Null audit
threshold/vote fields in `MISSING_WARMUP` rows are expected and were not
collapsed into a valid state.

### Fragmentation coverage gate

| Fold | Train NORMAL rows/dates | Train STRESS rows/dates | Train MISSING_WARMUP rows/dates | Validation NORMAL rows/dates | Validation STRESS rows/dates | Validation MISSING_WARMUP rows/dates | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| V2F1 | 57,608 / 240 | 28,632 / 118 | 28,124 / 127 | 18,762 / 82 | 3,802 / 18 | 0 / 0 | PASS |
| V2F2 | 80,662 / 342 | 32,434 / 136 | 28,124 / 127 | 14,832 / 71 | 5,924 / 29 | 0 / 0 | PASS |
| V2F3 | 99,949 / 432 | 38,559 / 166 | 28,124 / 127 | 18,912 / 90 | 2,104 / 10 | 0 / 0 | PASS |
| V2F4 | 120,485 / 530 | 42,992 / 188 | 28,124 / 127 | 10,511 / 52 | 9,885 / 48 | 0 / 0 | PASS |

## Run result

Output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_regime_run_20260810_run1`

### Control equivalence

`V3_C_CONTROL_EQUIVALENCE_PASS` on `84,732` rows. Score tolerance and metric
tolerance were `1e-12`; maximum score absolute difference was `0.0`, and every
required metric maximum difference was `0.0` against the immutable V2 HGB
reference.

### Overall metrics

| Candidate | Fold | Rows | Prevalence | PR-AUC | PR-AUC - prevalence | ROC-AUC | Q1 TP | Q5 TP | Q5-Q1 | Top-decile lift |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Control-006 | V2F1 | 22,564 | 0.380163091650417 | 0.401840583411268 | 0.021677491760852 | 0.525557987291492 | 0.337058560572195 | 0.421075740944018 | 0.084017180371823 | 0.057038125211817 |
| Control-006 | V2F2 | 20,756 | 0.388899595297745 | 0.417898685352869 | 0.028999090055124 | 0.523261617728366 | 0.355058365758755 | 0.425369575584168 | 0.070311209825413 | 0.051043880915161 |
| Control-006 | V2F3 | 21,016 | 0.413922725542444 | 0.422712210885660 | 0.008789485343216 | 0.527378627451213 | 0.399423907825252 | 0.438075017692852 | 0.038651109867600 | 0.042659907510777 |
| Control-006 | V2F4 | 20,396 | 0.384634242008237 | 0.422929127137299 | 0.038294885129062 | 0.512827018219457 | 0.348192174343735 | 0.405726765348216 | 0.057534591004482 | 0.023998851516943 |
| Two-Expert-007 | V2F1 | 22,564 | 0.380163091650417 | 0.390721948188714 | 0.010558856538298 | 0.515855957713034 | 0.345105051408136 | 0.409879253567508 | 0.064774202159372 | 0.035308442465185 |
| Two-Expert-007 | V2F2 | 20,756 | 0.388899595297745 | 0.395755812361320 | 0.006856217063574 | 0.508415738759552 | 0.359678988326848 | 0.407725321888412 | 0.048046333561564 | 0.025608176722980 |
| Two-Expert-007 | V2F3 | 21,016 | 0.413922725542444 | 0.444919752796721 | 0.030997027254278 | 0.535441236994343 | 0.410705712914066 | 0.437603208303845 | 0.026897495389779 | 0.038458226838508 |
| Two-Expert-007 | V2F4 | 20,396 | 0.384634242008237 | 0.409413384010091 | 0.024779142001854 | 0.504945223107313 | 0.361069836552749 | 0.394079107012861 | 0.033009270460112 | 0.019202688447398 |

Aggregate overall paired deltas, candidate minus control:

| Fold | PR-delta improvement | ROC change | Q5-Q1 change | Top-decile lift change |
|---|---:|---:|---:|---:|
| V2F1 | -0.011118635222554 | -0.009702029578457 | -0.019242978212450 | -0.021729682746632 |
| V2F2 | -0.022142872991549 | -0.014845878968814 | -0.022264876263849 | -0.025435704192181 |
| V2F3 | 0.022207541911062 | 0.008062609543130 | -0.011753614477821 | -0.004201680672269 |
| V2F4 | -0.013515743127209 | -0.007881795112144 | -0.024525320544370 | -0.004796163069544 |

Aggregate: median PR improvement `-0.012317189174881`, q25
`-0.015672525593294`, worst `-0.022142872991549`, PR not below control `1/4`;
median ROC change `-0.008791912345301`; median Q5-Q1 change
`-0.020753927238150`, Q5-Q1 not below control `0/4`; median top-decile lift
change `-0.013262922908088`.

### Regime-specific paired deltas

| Fold | State | PR-delta improvement | ROC change | Q5-Q1 change | Top-decile lift change |
|---|---|---:|---:|---:|---:|
| V2F1 | NORMAL | -0.006752017213833 | -0.008300443319413 | -0.014186442029555 | -0.009404388714733 |
| V2F1 | STRESS | -0.032058717354413 | -0.020764868650787 | -0.044207351385419 | -0.082687338501292 |
| V2F2 | NORMAL | -0.009047966771130 | -0.008988049153956 | -0.006175484214103 | -0.023087071240105 |
| V2F2 | STRESS | -0.025870632354530 | -0.032894201360936 | -0.062517316389439 | -0.031301482701812 |
| V2F3 | NORMAL | 0.003809571919184 | -0.013624538849111 | -0.015195525257822 | -0.002593360995851 |
| V2F3 | STRESS | 0.046789128701151 | 0.057674215003463 | 0.019281674208145 | -0.018691588785047 |
| V2F4 | NORMAL | 0.047116695152989 | 0.033299784558720 | -0.021928226655719 | -0.011183597390494 |
| V2F4 | STRESS | -0.037244254140502 | -0.045850101097860 | -0.027286337669770 | 0.001976284584980 |

Aggregate by state:

- NORMAL: median PR improvement `-0.001471222647324`, q25
  `-0.007326004603157`, worst `-0.009047966771130`, nonnegative `2/4`;
  median ROC change `-0.008644246236685`; median Q5-Q1 change
  `-0.014690983643689`.
- STRESS: median PR improvement `-0.028964674854471`, q25
  `-0.033355101550935`, worst `-0.037244254140502`, nonnegative `1/4`;
  median ROC change `-0.026829535005862`; median Q5-Q1 change
  `-0.035746844527594`.

### Frozen gates and decision

- absolute sanity gate: **PASS**;
- overall paired promotion gate: **FAIL**;
- regime-specific robustness gate: **FAIL**;
- final deterministic verdict: **`V3_C_REGIME_KILL_KEEP_V2_CONTROL`**;
- candidate verdict: **`KEEP_DIAGNOSTIC`**;
- selected component: none;
- cumulative evaluated candidate count: **7**.

The failure is not rescued or redefined. The two-expert architecture is closed
under this hypothesis, and V2 remains the control.

## Runtime and artifact hashes

Runtime mode: `sequential_reference`; control `10.7048803 s`, two-expert
`8.9251570 s`, total `20.7985817 s`; Python `3.13.5`; NumPy `2.4.2`; pandas
`2.3.3`; PyArrow `23.0.1`; scikit-learn `1.8.0`; Windows 11.

Major result artifacts:

| Artifact | SHA-256 |
|---|---|
| control equivalence | `2264cfa0d898451f8a09e9a01360ec73ae6022f9e55b2e70c0a4f39e08e26930` |
| overall metrics CSV | `b869c1fe28be941be9c82745571569352f3db8c5c4118d620d97f90e4f31be9a` |
| predictions Parquet | `9dcc75743a5ef9d2805a06ec6a2debe7e015195f55c64e396eef43c727c8f1c3` |
| state metrics CSV | `cf42986d62c02f28d3d55e9091d497476024e8b7e48a3c1669e8f59bcab3ffd9` |
| paired overall CSV | `88b0707a0e2e693b5a2c5b35ddf0911140a1431cf9215ca1ec89221b271c547e` |
| paired by state CSV | `2fd8c402e41e5a13428df56f42c012ae0baae4146d20c7ee7290132aef50b68d` |
| training counts CSV | `82bb648d71e49309e5a486937f9ed9008bb9607118c6d0cb67fd84a712f07112` |
| aggregate JSON | `1566cd62bc04aa0745c66b210dac227f4422c0e4ab6d272181b813643d68bc90` |
| verdict JSON | `4550b7cbb7cc9d009fb291218a4871b1aa544250063f07aed8093e0354527e5e` |
| coverage JSON | `7ae995dd0a725f8d516fc7451db2a6628bbbb60cce453b8b7d9de2a270b5c1cb` |
| ledger rows JSON | `d6fbb5113b5c79e05fbdc4ad91e45d4e6d1d07f653b2d9b8433930eef8caeb62` |
| runtime JSON | `fc1d967401623bbe770a65d0011407105d0c6730d2e70198b9e771f394f8e5a4` |
| summary JSON | `ea6d67f09da7560f18696e2475565971ac8cae979ab9d0d1f42328814e7984f7` |

Model artifact hashes are preserved in `ranking_v3_c_regime_summary.json` and
the runtime output directory; runtime artifacts remain outside Git.

## Safety boundary

`V2F5/V2F6` were not loaded, scored, or summarized. Reserved post-2026-07-31
V2 fresh-forward outcomes were not accessed. `FORWARD_OUTCOME_ACCESS_STARTED`
was not written. V3-D/V3-E, integration, calibration, Stage 6,
`IDX-VAL-002`, execution-PnL, Kelly, paper/live, and main merge were not
started.
