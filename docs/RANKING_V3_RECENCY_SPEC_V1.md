# Ranking V3 Recency Specification V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **FROZEN BEFORE OUTCOME RUN - PENDING INDEPENDENT REVIEW**

Hypothesis ID: `V3-A-RECENCY-V1`

This is a specification and research-governance artifact only. It does not
fit a model, score a row, inspect a V2 forward outcome, or authorize a V3
outcome run.

## 1. Single falsifiable hypothesis

Does deterministic recency weighting of training observations improve temporal
robustness versus the exact frozen V2 `HGB_XS_MARKET` control while keeping the
label, universe, features, estimator architecture, scoring semantics, and
evaluation semantics unchanged?

Only fit-row sample weights may differ. A result that requires any other change
is not a result for this hypothesis and requires a new hypothesis ID and new
specification.

## 2. Authorization and immutable development boundary

The authorized scope is specification only. A separate MAIN/ChatGPT review and
run authorization are required before implementation or V3 fitting/scoring.

The immutable prepared-data identity for a future authorized run is:

- logical artifact: `RANKING_V2_PREPARED_MODEL_TABLE`;
- prepared-table SHA-256:
  `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- prepared-cache manifest SHA-256:
  `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- rows: `292633`;
- tickers: `737`;
- eligible signal-session index: `20..1250`;
- source calendar boundary: `2021-04-29..2026-07-31`;
- row contract: resolved primary H10 rows only, with
  `label_status in {TP_FIRST, SL_FIRST}`, `binary_target in {0,1}`, and
  `universe_primary_liquid == true`.

The prepared table is read-only. It must not be regenerated, rewritten,
expanded, filtered using viewed results, or replaced with a new cache for this
hypothesis.

All information through `2026-07-31` is development/research knowledge, not
independent validation. The reserved post-`2026-07-31` V2 forward outcome set
is explicitly outside this specification and remains unreadable.

Frozen V2 lineage used for semantic inheritance:

- frozen substantive V2 implementation commit:
  `5f2ed2f53aececfd7c338d3f9f65db1efae372b6`;
- frozen V2 research specification Git blob:
  `18893d8efd870f29bf5f3a57e3fdfd68c8c0ad47`;
- frozen V2 champion/forward specification Git blob:
  `77b2d74c9d5f28460037c11cd3a134c6b6cc9d3d`;
- `src/idx_trade/research_v2_models.py` SHA-256:
  `2afe0292baa9d4fd1e35775e174481ae539ed57a285c568ccbf4b985833d1343`;
- `src/idx_trade/research_v2_validation.py` SHA-256:
  `786a54c95fba2f767097a729e31f2ec04de7b3b80d9c59ffccb9df91ea374276`;
- `src/idx_trade/research_v2_features.py` SHA-256:
  `a1730cd2dc4a75ea6550f3dd74ebebb75597f49b36a25fcbd0346e45f97c95a8`;
- `src/idx_trade/research_stage5.py` SHA-256:
  `455205a7d95d0bcd0774e86f153917a3bd82b94f98a37e16dc97752a63a34680`.

The future implementation must record its own code commit and all input
hashes. These inherited hashes do not authorize execution.

## 3. Exact V2 control

The control is the real frozen V2 champion, not a reconstructed V1 baseline:

`V2_CONTROL_HGB_XS_MARKET = HGB_XS_MARKET`

The control uses exactly these 25 features, in this order:

1. `xs_rank_close_return_5`
2. `xs_rank_close_return_20`
3. `xs_rank_atr14_over_close`
4. `xs_rank_close_position_20`
5. `xs_rank_distance_high_20_atr`
6. `xs_rank_distance_low_20_atr`
7. `xs_rank_distance_high_60_atr`
8. `xs_rank_distance_low_60_atr`
9. `xs_rank_relative_volume_20`
10. `xs_rank_log_regular_value_relative_20`
11. `market_primary_liquid_count`
12. `market_breadth_return_5_positive`
13. `market_breadth_return_20_positive`
14. `market_median_close_return_5`
15. `market_median_close_return_20`
16. `market_median_atr14_over_close`
17. `market_median_close_position_20`
18. `market_median_relative_volume_20`
19. `market_median_log_regular_value_relative_20`
20. `market_relative_close_return_5`
21. `market_relative_close_return_20`
22. `market_relative_atr14_over_close`
23. `market_relative_close_position_20`
24. `market_relative_relative_volume_20`
25. `market_relative_log_regular_value_relative_20`

The control preserves the existing causal universe, H10 first-touch target,
ATR14 geometry, TP/SL ambiguity handling, same-date percentile ranks, market
context, stock-minus-market features, and training-only preprocessing.

The estimator is unchanged:

- `ColumnTransformer` selecting the exact 25 columns;
- median `SimpleImputer(add_indicator=True, keep_empty_features=True)`;
- no scaler;
- `HistGradientBoostingClassifier`;
- `learning_rate=0.05`;
- `max_iter=200`;
- `max_leaf_nodes=31`;
- `l2_regularization=1.0`;
- `random_state=42`.

The ranking score is the logit of `predict_proba()[:, 1]` after clipping to
`[1e-9, 1 - 1e-9]`. It is a ranking score, not a calibrated probability.

The control is fit with uniform effective weight `1.0` and is otherwise an
exact V2 run. No V2 candidate, feature, parameter, label, universe, or
champion rule may be reopened.

## 4. Exact discovery and confirmation folds

Fold boundaries are one-based official-session indices. The V2 split and
20-session purge/maturity semantics are inherited exactly.

### Tier 1 discovery: fixed V2F1-V2F4

| discovery fold | train | purge gap | validation |
|---|---:|---:|---:|
| `V3D1 = V2F1` | `1..504` | `505..524` | `525..624` |
| `V3D2 = V2F2` | `1..624` | `625..644` | `645..744` |
| `V3D3 = V2F3` | `1..744` | `745..764` | `765..864` |
| `V3D4 = V2F4` | `1..864` | `865..884` | `885..984` |

Each validation block has exactly 100 official sessions. Training uses only
resolved primary H10 rows in the stated training prefix. Purge rows are used
for neither fitting nor validation. No random split, date shuffle, validation
threshold, early stopping, or fold-specific candidate change is allowed.

### Tier 2 late-development confirmation: fixed V2F5-V2F6

The latest two folds are reserved while recency candidates are discovered:

| confirmation fold | train | purge gap | validation |
|---|---:|---:|---:|
| `V3C1 = V2F5` | `1..984` | `985..1004` | `1005..1104` |
| `V3C2 = V2F6` | `1..1104` | `1105..1124` | `1125..1224` |

F5/F6 are run at most once, only after the candidate definitions and the
discovery winner are frozen. They are late-development evidence, not
independent validation. Sessions `1225..1250` present in the cache are not
used to select or rescue a candidate. No historical period through
`2026-07-31` may later be relabeled as independent validation.

## 5. Pre-registered candidate set

Exactly three candidate slots exist for this hypothesis: one control and two
recency variants. The candidate set is closed before any result is viewed.

| candidate ID | definition | training weight |
|---|---|---|
| `V3-A-RECENCY-V1-CONTROL-001` | exact V2 control | uniform `1.0` |
| `V3-A-RECENCY-V1-HL252-002` | recency variant A | half-life `252` official sessions |
| `V3-A-RECENCY-V1-HL504-003` | recency variant B | half-life `504` official sessions |

There are no other half-lives, windows, caps, decay bases, class weights,
resampling schemes, feature toggles, model families, parameter values,
thresholds, ensembles, or pairwise candidates in this experiment. The two
half-lives are fixed before outcome access as approximately one and two years
of official-session history; they are not a post-result search grid.

## 6. Exact official-session age and weight formula

For a training row with signal-session index `s` in a fold whose inclusive
training end is `T`, define:

`age_sessions(s, T) = T - s`.

Age is measured only in official IDX exchange sessions. It is not calendar-day
age, ticker-observation age, row count, current-active age, or label maturity.
The newest training signal session has age zero. Every row on the same signal
session receives the same age. The purge gap is not part of the age origin:
`T` is the last training signal index, not the first validation index.

For half-life `H` in `{252, 504}`, calculate in float64:

`raw_weight_i(H) = 2 ** (-age_sessions_i / H)`

For `n` eligible training rows in that fold, normalize only within that fold:

`weight_i(H) = n * raw_weight_i(H) / sum_j(raw_weight_j(H))`.

Therefore every recency variant has finite positive weights with arithmetic
mean exactly one and total effective training weight equal to `n`. The control
uses `weight_i = 1.0`.

This normalization is frozen to keep the total sample-weight scale, and hence
the interaction with HGB regularization and stopping criteria, comparable to
the unweighted V2 control. It does not make recency neutral: recent rows still
receive greater influence. No class rebalancing is applied.

Weights are passed only to model fitting. Validation rows are never weighted
for metric calculation. Weight sums, min/max/mean, formula, half-life, fold
boundary, and implementation code hash must be recorded in the run manifest.

## 7. Invariants during a future authorized run

For every candidate and fold:

- the eligible rows, labels, universe, dates, and 25 feature values are the
  same as the control;
- preprocessing is fitted on that fold's training rows only;
- only the two recency candidates receive the frozen normalized sample weight;
- the estimator, score transform, ranking buckets, and metric code are exact
  V2 semantics;
- no H5/H20 label, Open field, future date, forward outcome, or outcome-derived
  feature is read;
- output directories are isolated and newly created;
- the immutable prepared cache is never modified.

The future implementation must fail closed on missing/changed cache hashes,
changed fold boundaries, non-finite weights, non-positive weights, duplicate
rows, changed feature order, or any provenance mismatch.

## 8. Metrics and robustness gates

Each fold reports the exact V2 metrics: row count, positive prevalence, PR-AUC,
`PR-AUC - prevalence`, ROC-AUC, Q1 TP rate, Q5 TP rate, Q5-Q1 TP-rate spread,
top-decile TP rate, and top-decile lift. Q5-Q1 is **Q5 TP rate minus Q1 TP
rate**; it is not a realized-return spread. Top-decile lift is top-decile TP
rate minus prevalence. Probability metrics are out of scope.

For each recency candidate, also report paired per-fold differences versus the
uniform V2 control for PR-AUC delta, ROC-AUC, Q5-Q1 spread, and top-decile
lift. Discovery aggregates include median, q25, and worst-fold PR-AUC delta;
positive-fold count; median ROC-AUC and ROC>0.5 count; median and worst-fold
Q5-Q1; positive Q5-Q1 fold count; top-decile lift; and the V4 discovery fold
behavior explicitly.

### Discovery absolute sanity gate

A candidate must satisfy all of the following on V3D1-V3D4:

1. every required metric is finite;
2. median `PR-AUC - prevalence` is strictly positive;
3. `PR-AUC - prevalence` is positive in at least 3 of 4 folds;
4. median ROC-AUC is greater than `0.50`;
5. ROC-AUC is greater than `0.50` in at least 3 of 4 folds;
6. median Q5-Q1 TP-rate spread is strictly positive;
7. Q5-Q1 TP-rate spread is positive in at least 3 of 4 folds.

### Discovery paired promotion gate

A recency variant passes discovery only if it passes the absolute sanity gate
and all of these predeclared paired rules versus the control:

1. median PR-AUC-delta improvement is at least `+0.001`;
2. q25 PR-AUC-delta improvement is non-negative;
3. worst-fold PR-AUC-delta improvement is non-negative;
4. the variant is not below the control on PR-AUC delta in at least 3 of 4
   folds;
5. median ROC-AUC change is no worse than `-0.005`;
6. median Q5-Q1 change is no worse than `-0.005`;
7. the variant is not below the control on Q5-Q1 in at least 3 of 4 folds.

The `+0.001` PR-AUC threshold and `-0.005` non-inferiority tolerances are
fixed practical gates, not tunable parameters. Top-decile lift and late-fold
behavior are mandatory diagnostics; they cannot rescue a failed primary gate.

### Late-confirmation promotion gate

Only a recency variant that passes discovery receives the one-time F5/F6
confirmation. It is promoted for the next separately authorized research step
only if, across F5/F6:

1. all metrics are finite;
2. median PR-AUC delta, median ROC-AUC, and median Q5-Q1 are positive;
3. on each confirmation fold, candidate PR-AUC delta is no worse than control
   by `0.005`;
4. on each confirmation fold, candidate Q5-Q1 is no worse than control by
   `0.005`.

No candidate is selected by inspecting one confirmation fold before the other.
If both variants pass, use the deterministic tie rule below. If neither passes
late confirmation, the recency hypothesis is closed without promotion.

## 9. Kill, diagnostic, promotion, and tie rules

- `KILL`: a candidate violates a data/contract/provenance gate, produces a
  non-finite required metric/weight, or fails the discovery absolute sanity
  gate. It remains permanently recorded in the ledger and is not rerun under
  this spec.
- `KEEP_DIAGNOSTIC`: a candidate is clean and finite but fails the paired
  discovery promotion gate or the one-time late-confirmation gate. It is not
  promoted and cannot be rescued by changing thresholds or weights.
- `PROMOTE_FOR_NEXT_RESEARCH_STEP`: a recency candidate passes both discovery
  and late-confirmation gates. This is a research-governance result only; it
  does not authorize implementation, forward access, probability, execution,
  paper, or live trading.

If both recency variants pass, choose in this order:

1. larger discovery median paired PR-AUC-delta improvement;
2. larger discovery q25 paired PR-AUC-delta improvement;
3. larger discovery worst-fold paired PR-AUC-delta improvement;
4. larger discovery median paired Q5-Q1 improvement;
5. simpler perturbation: `HL504` before `HL252`;
6. lower candidate ordinal.

If no recency candidate is promoted, the deterministic decision is
`V3_A_RECENCY_KILL_KEEP_V2_CONTROL`. The exact V2 control remains the reference
and no alternative V3 architecture is substituted.

## 10. Hypothesis ledger and cumulative counter

The permanent ledger is `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`. At this spec
freeze, the V3 generation has evaluated zero candidates and the cumulative
evaluated counter is `0`. The three candidate ordinals below are reserved, not
results:

- `001`: uniform V2 control;
- `002`: half-life 252;
- `003`: half-life 504.

An authorized runner must increment the cumulative counter deterministically
when a candidate is actually run, never reuse an ordinal, and never delete a
viewed or failed candidate. Each ledger row must contain at least:

`hypothesis_id`, `parent_hypothesis`, `candidate_id`, `candidate_ordinal`,
`spec_sha256`, `spec_commit`, `cache_sha256`, `cache_manifest_sha256`,
`fold_set`, `feature_order_hash`, `model_identity`, `weight_formula`,
`weight_normalization`, `result_status`, `result_viewed`, `metrics_artifact`,
`artifact_sha256`, `verdict`, `cumulative_candidate_count`, `code_commit`,
`environment`, and `notes`.

Before any outcome run, the ledger rows must remain `SPECIFIED_NOT_RUN`,
`result_viewed=false`, and without fabricated metrics.

## 11. Provenance and runtime contract

The future run must use one deterministic Python orchestrator with a bounded
process pool if parallelism is needed. Codex sessions are not the compute
scheduler. The post-cache stages must be profiled before adding concurrency;
candidate-level and fold-level parallelism must not be independently
unbounded.

The run manifest must pin the spec SHA-256, source commit, V2 code hashes,
prepared-cache and manifest hashes, official-session/fold manifest, feature
order, estimator parameters, candidate ordinal, half-life, random seed,
weight statistics, Python/dependency environment, output paths, and hashes of
all metrics/model/diagnostic artifacts. Reference-vs-optimized equivalence is
required before any optimized implementation can be used for outcomes.

All artifacts are written to a new immutable run directory. Changed inputs,
revision conflicts, missing provenance, changed folds, or artifact hash
mismatches fail closed. No runtime implementation or profiling is part of this
specification task.

## 12. Explicit stop boundary

This task must stop after the spec, checkpoint, ledger, continuity update, and
result handoff are committed and pushed for review.

Do not fit, score, evaluate, or serialize a V3 model. Do not inspect or
summarize reserved V2 forward labels/outcomes after `2026-07-31`. Do not write
`FORWARD_OUTCOME_ACCESS_STARTED`. Do not rerun or retune V2, start Stage 6,
start `IDX-VAL-002`, start probability calibration, make execution-PnL claims,
paper/live trade, or merge to `main`.
