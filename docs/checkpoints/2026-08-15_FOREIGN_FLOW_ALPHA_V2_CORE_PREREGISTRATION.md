# Foreign Flow V2 Core Alpha — Preregistration

Status: `FOREIGN_FLOW_V2_CORE_ALPHA_PREREGISTERED`

This document freezes the one paired historical-development experiment. It is
written before the runner reads historical target values. No provider call,
forward/O2 counter access, protected/fresh-forward outcome access, or
free-float/effective-supply feature is authorized by this experiment.

## Parent and immutable inputs

- Repository: `samindriano/idx-trade`
- Representation acceptance commit:
  `ceb0c2c6f57aac0433cac9a5532daa0db4c99c0b`
- Clean V2 table:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_v2_v3b_o2_reproduction_v1_20260813_002_fast_h10\pit_safe_ranking_v2_prepared_model_table.parquet`
- Clean V2 table SHA-256:
  `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`
- Clean V2 table population: 292,631 rows / 737 tickers
- Foreign Flow V2 representation:
  `D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001\foreign_flow_representation_v2.parquet`
- Foreign Flow V2 feature SHA-256:
  `0c2212a166115b2f5b974b93096ea06b222b7451d70fa7d58257a9bed0f7a1f0`
- Foreign Flow V2 representation manifest SHA-256:
  `4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc`
- Official calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Calendar: the accepted 1-based official exchange-session index used by the
  Clean V2 lineage.

The accepted Clean V2 HGB fold models are read-only and SHA-pinned:

`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_historical_replay_v1_20260813_001\v2`

| Fold | SHA-256 |
|---|---|
| V2F1 | `d8b8d33808d899cfebd050ae35e5cbca1f4c522241553067e7d94e9c70d3a4b3` |
| V2F2 | `bdce9e146227943fbeac21e6d8cc46bff2efd4a3ef1585c82f0264f5f0e1787f` |
| V2F3 | `e3f2a19cd58453e029272e94058710c97f7a080e0b33056dc892d179ed8fc4ad` |
| V2F4 | `3ee75ae5e9793965e6302c0e7460bbf1048421f65adb4934a19cc83dab688d3b` |
| V2F5 | `60e5194916491f98b57c461791f3c8e3900ef400613a7c4122f9ae98811809bd` |
| V2F6 | `f1893a6ce1dd3d2faa5998e48650d0fee0cb520d8d838b1b05978fb7809ba1d3` |

## Frozen comparison

BASE is the exact accepted Clean V2 `HGB_XS_MARKET` control: its pinned
25-feature fold model, binary H10 target, preprocessing, and ranking metrics.
The challenger is a fresh `HistGradientBoostingClassifier` fit from zero on
the same rows and fold split, with the exact Clean V2 25-feature prefix plus
all eight Foreign Flow V2 core features below. It is not a blend, separate
flow-only model, or score transform.

Foreign Flow V2 core block, in exact order:

1. `foreign_participation_1`
2. `foreign_flow_shock_percentile_120`
3. `xs_rank_foreign_flow_shock_mean_5`
4. `xs_rank_foreign_flow_shock_mean_20`
5. `foreign_weighted_persistence_5`
6. `foreign_flow_acceleration_5_20`
7. `foreign_flow_price_divergence_5`
8. `foreign_flow_price_divergence_20`

The Clean V2 prefix remains the exact accepted 25-feature order. Missing
Foreign Flow values retain their representation semantics and use only the
accepted parent median-imputation plus missing-indicator preprocessing. The
runner does not use `feature_status` or `missing_reasons` and never
forward-fills.

Model parameters are frozen to the Clean V2 contract:

```text
HistGradientBoostingClassifier(
    learning_rate=0.05,
    max_iter=200,
    max_leaf_nodes=31,
    l2_regularization=1.0,
    random_state=42,
)
median imputer + missing indicators; no clipping/winsorization
```

## Temporal and fold contract

The exact expanding folds are:

| Fold | Train | Purge/embargo | Validation |
|---|---|---|---|
| V2F1 | 1–504 | 505–524 | 525–624 |
| V2F2 | 1–624 | 625–644 | 645–744 |
| V2F3 | 1–744 | 745–764 | 765–864 |
| V2F4 | 1–864 | 865–884 | 885–984 |
| V2F5 | 1–984 | 985–1004 | 1005–1104 |
| V2F6 | 1–1104 | 1105–1124 | 1125–1224 |

The historical boundary is 2026-07-31. The representation's
`feature_session` is the model decision session and its
`flow_through_session` must be exactly the immediately preceding official
session. The runner verifies this against the pinned official calendar. No
same-session or future-session flow is accepted. BASE and challenger use the
same exact Clean V2 table keys; a flow join cannot add, remove, or reorder
support rows.

## Frozen target, metrics, and decision gate

The binary H10 target is consumed exactly as materialized in the accepted
Clean V2 table (`TP_FIRST` versus `SL_FIRST`). The primary comparison is
paired fold PR-AUC delta, challenger minus BASE. Secondary diagnostics are
ROC-AUC delta, Q5−Q1 delta, and top-decile lift delta, using the existing Clean
V2 ranking definitions.

The only allowed gate is:

- median paired PR-AUC delta > 0;
- Q25 paired PR-AUC delta > 0;
- at least 2 of 6 paired PR-AUC deltas > 0;
- no ranking guardrail reversal, defined as both challenger median ROC-AUC and
  challenger median Q5−Q1 being below the corresponding BASE medians.

Allowed verdicts are only:

- `FOREIGN_FLOW_V2_CORE_SURVIVOR`
- `FOREIGN_FLOW_V2_CORE_NO_SURVIVOR`

There is no subset search, alternate window, additional feature, tuning,
rescue, alternate gate, V1 rescue, or post-result selection. A failed gate is
final for this lane.

## Run identity and output

- Implementation commit frozen for the run:
  `8140825643a24b39f7f4a2eb7d5cb88d3dfe754a`
- Runner: `src/idx_trade/foreign_flow_alpha_v2.py`
- External output root:
  `D:\Documents\Project\idx-trade-foreign-flow-alpha-v2-core-20260815-001`
- Provider calls: forbidden
- Protected/fresh-forward/O2 outcomes: forbidden
- Free-float/effective-supply: excluded and remains a separate lane

The runner writes the common-support keys, paired predictions, fold metrics,
paired metrics, aggregate metrics, gate, challenger models, and a hashed
manifest outside Git. The result is executed once after this preregistration
commit; no second run is authorized after outcome access.
