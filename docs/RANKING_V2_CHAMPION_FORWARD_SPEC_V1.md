# Ranking V2 Champion and Fresh-Forward Specification V1

Status: frozen after independent review clarification, 2026-08-10 (Asia/Jakarta)

This document freezes the historical champion, final refit contract, and the
first independent fresh-forward evaluation contract. It does not run a final
refit, read fresh-forward labels, or inspect any outcome after 2026-07-31.

## 1. Frozen champion

The only selected Ranking-V2 historical-development champion is
`HGB_XS_MARKET`. Candidate selection is closed. No candidate, feature family,
hyperparameter, label, universe, threshold, or calibrator may be reopened to
improve a future result.

The frozen feature order is:

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

The estimator is the existing scikit-learn pipeline: a
`ColumnTransformer` selecting the exact 25 columns, a median
`SimpleImputer(add_indicator=True, keep_empty_features=True)`, and
`HistGradientBoostingClassifier` with:

- `learning_rate=0.05`;
- `max_iter=200`;
- `max_leaf_nodes=31`;
- `l2_regularization=1.0`;
- `random_state=42`.

There is no scaler. The ranking score is the logit of clipped
`predict_proba()[:, 1]`, clipped to `[1e-9, 1 - 1e-9]`. It is a ranking score
only; it is not a calibrated probability and must not be used for probability
claims, sizing, execution, or trading.

## 2. Final-development refit boundary

The final refit, when separately authorized, uses the immutable prepared model
cache only:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet`

The accepted cache SHA-256 is
`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` and its
manifest SHA-256 is
`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`.

Eligible rows are exactly:

- `signal_session_index` in `20..1250`;
- `label_status` in `{TP_FIRST, SL_FIRST}`;
- `binary_target` in `{0, 1}`;
- `universe_primary_liquid == true`;
- all existing common-stock, PIT, official ACTIVE regular-market, and H10
  evidence requirements already enforced by the prepared-cache contract.

This is the 292,633-row, 737-ticker resolved primary H10 table. No row with a
signal index above 1250 is eligible. The final refit is one fit over this
fixed table, with no folds, candidate comparison, tuning, search, or outcome-
based filtering. It must not be run until MAIN authorizes the next phase.

## 3. Causal forward feature and universe contract

The forward signal date must be an official IDX exchange session strictly
after 2026-07-31. The forward calendar, security master, tradability evidence,
corporate-action evidence, and price snapshots must be immutable inputs for a
run.

For each signal session `t`, construct the same V2 features using only data
available at or before `t`:

- stock rolling features are right-aligned and use the trailing official
  session history only;
- the primary universe uses the existing common-stock/PIT/official ACTIVE
  regular-market contract, at least 20 active observations in the trailing 60
  official sessions, and median Regular-Market Value at least IDR
  1,000,000,000;
- same-date percentile ranks and market context use every eligible
  primary-liquid row on `t`, not label-resolved rows;
- relative features are stock raw values minus the same-date market median;
- Open is not a V2 feature and is never synthesized;
- no future label, future price, Yahoo-only state, or current-active listing
  shortcut may affect eligibility or feature construction.

Rows with incomplete required causal history or failed official data gates are
excluded from the scored forward universe and reported explicitly. No
forward-fill, synthetic OHLC, or silent provider substitution is allowed.

## 4. H10 maturity and first sample

An H10 signal at session `t` is an observed outcome only after official
sessions `t+1` through `t+10` exist and the complete existing H10 path/label
contract is available for that signal. A signal with a missing endpoint,
unknown tradability, unresolved price evidence, revision conflict, or any
other failed evidence condition remains immature/unresolved and is not scored
as an observed outcome.

Partial horizons, endpoint estimates, forward-fills, and synthetic outcomes are
forbidden. The first independent verdict is one fixed block of exactly 100
consecutive mature official forward signal sessions. The verdict is not
available before the 100th session in that block is mature. The exact calendar
dates and row counts are determined by the frozen post-2026-07-31 calendar and
reported after the authorized run; they are not inspected or inferred here.

## 5. Metrics and decision rule

The one-shot report must include resolved row count, expected row count,
coverage, unknown/immature counts, positive prevalence, PR-AUC, PR-AUC minus
prevalence, ROC-AUC, within-signal-date Q1 TP rate, within-signal-date Q5 TP
rate, `Q5 TP rate - Q1 TP rate`, within-signal-date top-decile TP rate, and
top-decile lift versus fold/block prevalence.

These bucket metrics intentionally preserve the historical Ranking-V2 semantics
implemented by `evaluate_v2_scores`: Q5-Q1 is a **TP-rate spread**, and
top-decile lift is **top-decile TP rate minus prevalence**. No realized-return
Q5-Q1 spread is part of this verdict.

All metrics must be finite and computed on the same frozen resolved sample.
Probability calibration metrics are out of scope and remain deferred.

Split the 100-session block into its first 50 and last 50 mature signal
sessions for a predeclared stability check. The verdict is:

- `PASS` only when all data/provenance/maturity gates pass, all metrics are
  finite, aggregate PR-AUC minus prevalence is positive, aggregate ROC-AUC is
  greater than 0.50, aggregate Q5-Q1 TP-rate spread is positive, and both
  50-session halves have positive PR-AUC minus prevalence and positive Q5-Q1
  TP-rate spread;
- `MIXED` only when all data/provenance/maturity gates pass and the aggregate
  PR-AUC minus prevalence and Q5-Q1 TP-rate spread are positive, but at least
  one PASS stability condition is not met;
- `FAIL` for any data/provenance/maturity failure, non-finite metric,
  non-positive aggregate PR-AUC delta, or non-positive aggregate Q5-Q1 TP-rate
  spread.

This rule is fixed before outcome access. No metric selection, threshold
search, half selection, calibration, post-outcome refit, or adaptive rescue is
permitted.

## 6. One-shot access and artifact controls

The evaluation is one-shot at the first eligible 100-mature-session block.
Sequential monitoring, repeated verdicts on overlapping windows, and reruns in
new output directories are prohibited. A later forward extension requires a
new authorization and is not an independent verdict from this block.

Before any fresh-forward outcome is read, the runtime must:

1. write and hash a pre-outcome manifest containing the contract/spec SHA,
   code commit, frozen champion identity, exact feature order and parameters,
   prepared-cache and source snapshot hashes, calendar/security/tradability/
   corporate-action revisions, environment, and intended 100-session block;
2. atomically write `FORWARD_OUTCOME_ACCESS_STARTED` in the parent frozen
   snapshot directory, not only in the output directory;
3. refuse to start if that global marker already exists.

The marker is written before loading the complete fresh-forward label/outcome
set. If the process crashes after the marker is written, the block is consumed
and must not be rerun. The outcome manifest, summary, metrics, and all
resolved/unresolved diagnostics are written only after the one-shot run. Every
artifact is SHA-256 hashed and the manifest verifies all hashes.

The final model, when authorized, is serialized as a joblib artifact with a
JSON model manifest. The manifest records the exact preprocessing, feature
order, hyperparameters, training row count, maximum training signal index,
cache/manifest hashes, source snapshot hashes, runtime code commit, Python
and dependency versions, and score semantics. The actual final model hash is
not generated in this freeze task.

## 7. Revisions and immutable evidence

Raw provider files and derived snapshots are content-addressed or copied into
an immutable run directory. Existing artifacts are reused only when their
recorded hash and provenance match the frozen contract. Download errors,
revision conflicts, changed official calendars, changed corporate actions,
changed security identity, and changed tradability evidence fail closed. No
in-place rewrite may silently change a previously frozen input.

## 8. Runtime and performance plan

The mandatory `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` was read before
freezing this contract. Its applicable recommendations are:

- use one deterministic Python orchestrator with a bounded process pool, not
  many unconstrained Codex chats;
- profile the post-cache stages before optimizing: cache read,
  normalization/validation, split construction, preprocessing, final fit,
  scoring, maturity/metrics, serialization, total wall time, CPU, and RAM;
- use column-projected Parquet reads and bounded concurrency; do not
  oversubscribe candidate and fold work;
- use immutable fold-index caches only where they serve an authorized future
  workload; no historical candidate rerun is needed for this freeze;
- prove reference-versus-optimized equivalence on fixtures, adversarial cases,
  deterministic samples, and the full authorized workload before any optimized
  runtime may access fresh outcomes. Require exact categorical/index/date
  equality, strict numeric tolerances, score/metric equality, and hashed
  environment/artifacts.

No profiling, optimization implementation, final refit, or fresh-forward
runtime was run in this task.

## 9. Boundary and next action

This specification is the frozen architecture and decision contract. The
current blockers are authorization to implement/run the final refit and the
availability of a complete post-2026-07-31 immutable forward evidence window;
neither is to be bypassed by inspecting outcomes early.

The exact next action is: MAIN / ChatGPT reviews this document and the
checkpoint, then separately authorizes implementation of the final-refit and
one-shot fresh-forward runtime. Until that authorization, do not read or
summarize fresh-forward outcomes, do not run Stage 6 or IDX-VAL-002, and do
not merge to `main`.
