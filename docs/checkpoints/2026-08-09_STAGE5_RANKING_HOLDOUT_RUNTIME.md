# Stage 5 Ranking-Only Holdout Runtime

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage5-ranking-holdout-v1`
Runtime code commit: `05c2bb549b446da374c13937a41aa6732cf71ec0`

## Decision

Automatic result: **`STAGE5_RANKING_HOLDOUT_FAIL`**.

The one-shot locked holdout was consumed for ranking V1 only. The runner
completed successfully after freezing and hashing the final development models
before reading any holdout outcome labels. No retry is permitted.

Probability V1 remains **`PROBABILITY_V1_NOT_READY_DEFERRED`**. This runtime
does not authorize Stage 6, Probability V2, `IDX-VAL-002`, execution-PnL
claims, paper/live trading, or a merge to `main`.

## Reproducibility and guards

Required environment:

- Python 3.13.5;
- NumPy 2.4.2;
- pandas 2.3.3;
- pyarrow 23.0.1;
- scikit-learn 1.8.0.

Full pytest: **206 passed, 0 failed**, with three existing pandas
FutureWarnings.

Frozen input hashes:

| input | SHA-256 |
|---|---|
| signal panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| research manifest | `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a` |
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| Stage-4B summary | `f9cbce089c21debd6420943ebf5cd647fc41942e4f210964ddbb5d165d10ebb7` |
| security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |

Research manifest verification was `valid=true`, with 15/15 artifacts
verified and no mismatches.

## Frozen development boundary

Final training stopped at signal session 988 (`2025-06-13`), with sessions
989-1008 reserved for the declared H20 purge/buffer. The development table
contained 217,352 rows and positive rate 0.3882319923.

The pre-holdout artifact hashes were:

| artifact | SHA-256 |
|---|---|
| final training table | `7c4e858feb9c66617e5894d53a1e120e1bc7a6536095bcf760ad307a37b96c1a` |
| frozen MOMENTUM_20 | `f3b966031b83a0a11bb6550a0993674f591ee64b31bd17e6f501c68c1ae0f89f` |
| frozen LOGISTIC_COMPACT | `0bda5fd491b0442645d48c79e304f4b7cc70fef8e13464c78b26edb5c55d3201` |
| frozen HGB_FULL | `bfc275072a11e793d388aa0414fc2c1d1b65d9439a0b5769fae0b060aa9ffefc` |
| pre-holdout freeze record | `c8eb0c13e1bf4100b6a2b757bdd46d739d5ea65e264c55af48e67324d14b7155` |

## Primary H10 result

Holdout signals were sessions 1009-1250 (`2025-07-15` to `2026-07-17`).
There were 71,420 resolved primary rows and positive rate 0.4071688603.

| model | rows | PR-AUC | ROC-AUC |
|---|---:|---:|---:|
| BASE_RATE | 71,420 | 0.4071688603 | 0.5000000000 |
| MOMENTUM_20 | 71,420 | 0.3966643214 | 0.4860543642 |
| LOGISTIC_COMPACT | 71,420 | 0.4051024048 | 0.4990938749 |
| HGB_FULL | 71,420 | 0.4073793720 | 0.4948433255 |

HGB beat base-rate PR-AUC by 0.0002105118 and beat momentum, but HGB
ROC-AUC was below the 0.5 gate. Decision checks were:

- HGB PR-AUC > base: pass;
- HGB PR-AUC > momentum: pass;
- HGB ROC-AUC > 0.5: fail;
- Q5 > Q1: pass;
- HOLDOUT_A PR-AUC > base: pass;
- HOLDOUT_B PR-AUC > base: fail;
- all metrics finite: pass;
- models frozen before holdout labels: pass.

Within-date HGB quintiles:

| bucket | rows | TP rate | lift vs overall |
|---:|---:|---:|---:|
| 1 | 14,185 | 0.4065562214 | -0.0006126389 |
| 2 | 14,280 | 0.3938375350 | -0.0133313252 |
| 3 | 14,293 | 0.4041139019 | -0.0030549584 |
| 4 | 14,280 | 0.4138655462 | 0.0066966860 |
| 5 | 14,382 | 0.4173967459 | 0.0102278857 |

Q5-Q1 was 0.0108405246. The top decile contained 7,249 rows, had TP rate
0.4323354946, and had lift 0.0251666343 versus overall.

Temporal halves:

| half | sessions | rows | positive rate | PR-AUC | ROC-AUC | PR-AUC delta vs base | Q5-Q1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| HOLDOUT_A | 1009-1129 | 33,003 | 0.4647456292 | 0.4866372564 | 0.5186811460 | 0.0218916273 | 0.0464755652 |
| HOLDOUT_B | 1130-1250 | 38,417 | 0.3577062238 | 0.3471254020 | 0.4810497816 | -0.0105808218 | -0.0198933303 |

## Sensitivity and outcomes

| horizon | rows | positive rate | PR-AUC | ROC-AUC | PR-AUC delta vs base |
|---:|---:|---:|---:|---:|---:|
| H5 | 56,762 | 0.3893978366 | 0.3934717252 | 0.5003881183 | 0.0040738886 |
| H20 | 76,458 | 0.4014883989 | 0.4031550698 | 0.4958467114 | 0.0016666710 |

H10 outcome status counts were:

| status | rows | share |
|---|---:|---:|
| AMBIGUOUS_SAME_BAR | 482 | 0.0056305122 |
| INVALID_BARRIER | 114 | 0.0013316979 |
| NO_BARRIER_HIT | 12,330 | 0.1440336429 |
| SL_FIRST | 42,340 | 0.4945972782 |
| TP_FIRST | 29,080 | 0.3396997839 |
| UNRESOLVED_PATH | 1,259 | 0.0147070849 |

Ambiguous and unresolved outcomes stayed explicit; they were not silently
converted into binary outcomes.

## One-shot markers and external artifacts

The output directory is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\stage5_ranking_holdout_v1_20260809`

The summary SHA-256 is
`1a38171eead5a9c72de62da4f6ef486f35e3fba2e962c3b0bccac9fea033acd0`.

The global marker is beside the immutable panel and has SHA-256
`4afdfac7c0542391bd7b5787cd329ed4c3985402c0dea0547866597d52588d0d`.
The local marker has SHA-256
`1295ac4dedf60dbb3d576b9e007c8e3d67611ff74dd5b7207482b269825db543`.
Both markers record `holdout_consumed=true`,
`holdout_consumed_for=RANKING_V1_ONLY`, and
`models_frozen_before_holdout_labels=true`.

Runtime artifact hashes:

| artifact | SHA-256 |
|---|---|
| H10 predictions | `9d850776c98c07e069b32d606ad510d94a26435659da86997f5302d765d8ee8c` |
| H10 metrics | `1ce12ed641ea83deea9e5157e03f1576f95d6f4dc909d826aafd89108d3a52f7` |
| H10 quintiles | `22b36dedab78b93bbfe7e09d32f082e72a4833a597186026266766e85775b63f` |
| H10 deciles | `9b95be5635c6a3e640e09a218560303344548e6adeda3e08ba6eb6122450d894` |
| H10 temporal halves | `c90b81bd24ffbabfc7faf2806e741723bf216be037c1f5d57283ac9cb078e666` |
| H5/H20 sensitivity | `cb3c33eb973cacb26610be7435ac6c0198049a76ac05009cea155cb7d0b352f3` |
| outcome status summary | `17a8fbdfdc1852c1feb17d3ff5a781ea35270e5d11a77c4775aedcb07672a0c2` |

All runtime data, models, markers, and generated tables remain outside Git.

## Governance stop

The next action is independent ChatGPT review of this failed ranking-only
result. Do not rerun Stage 5, start Stage 6, validate Probability V2 on this
holdout, run `IDX-VAL-002`, make an execution-PnL claim, paper/live trade, or
merge to `main`. Any future Probability V2 validation must use fresh forward
data strictly after `2026-07-31`.
