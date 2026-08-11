# Path Risk V2 — Stop-Touch Probability and Discrete Competing-Risk Specification

Date: 2026-08-11 (Asia/Jakarta)
Status: **FROZEN PRE-OUTCOME SPEC — V1 REMAINS FAIL_CLOSE; F5/F6 SEALED**

## 1. Purpose

Path Risk V1 (`PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1`) is permanently closed as
`PATH_RISK_A_DISCOVERY_FAIL_CLOSE`.  V2 is a new bounded risk hypothesis family,
not a rescue or reinterpretation of PR-001.

The final alpha ranker remains immutable:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`.

Path Risk V2 asks whether the same causal setup representation can estimate a
more decision-relevant risk endpoint:

> What is the probability that the frozen 1R stop level is touched before the
> H10 setup resolves, and does modelling the discrete barrier path add useful
> information beyond a direct H10 classifier?

No Path Risk result may retune, filter, rerank, or replace the final alpha
ranker.  Any later alpha+risk decision rule requires a separate preregistered
integration study.

## 2. Development knowledge and protected boundary

Path Risk F1-F4 are now development knowledge because PR-001 was viewed there.
They may be reused to compare the two frozen V2 architectures below.

Path Risk F5/F6 remain **sealed**.  This V2 specification does not authorize
reading or scoring them.  If V2 produces exactly one F1-F4 survivor, a separate
one-shot F5/F6 confirmation spec/review is required before access.

Post-2026-07-31 fresh-forward outcomes remain protected and unrelated to this
historical Path Risk development lane.  Do not write
`FORWARD_OUTCOME_ACCESS_STARTED`.

## 3. Frozen source material for V2 discovery

V2 discovery reuses the immutable PR-001 F1-F4 joined model table rather than
recomputing H10 targets or rereading raw label/path artifacts.

Required local artifact:

`path_risk_v1_discovery_model_table.parquet`

Required SHA-256:

`b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe`

Required facts:

- rows: `252,198`;
- maximum signal session: `984`;
- exact 33-feature order SHA-256:
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- eligible statuses only: `TP_FIRST`, `SL_FIRST`, `AMBIGUOUS_SAME_BAR`,
  `NO_BARRIER_HIT`;
- no session `985+` may be materialized.

Official calendar identity remains:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.

Reusing this already-viewed immutable development artifact is deliberate: it
avoids another expensive target/path reconstruction and follows the runtime
rule to reuse deterministic immutable transformations when semantics are
unchanged.

## 4. Frozen H10 stop-touch endpoint

Signal-level binary target:

```text
stop_touch_h10 = 1  for SL_FIRST or AMBIGUOUS_SAME_BAR
stop_touch_h10 = 0  for TP_FIRST or NO_BARRIER_HIT
```

`AMBIGUOUS_SAME_BAR` is positive because the stop level was definitely touched.
This convention makes no claim about intrabar execution order.

The endpoint is **stop touch**, not realized loss, fill price, or stop-first
probability under unknown intraday ordering.

The existing `adverse_excursion_r` remains diagnostic only.  V2 does not change
or refit the V1 q75 target.

## 5. Frozen information set

Both V2 candidates use the exact frozen V3-B 33 causal market/setup features.

Feature-order SHA-256:

`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`.

Forbidden as candidate inputs:

- final V3-B score/probability;
- H10 label/status/event date;
- adverse-excursion target;
- ticker identity/dummies;
- Open;
- future data;
- V4 failed features;
- sector/fundamental/flow data.

PR-003 additionally uses only the deterministic integer `path_horizon_step`
from `1..10`.  This is a horizon coordinate, not market information.

## 6. Candidate PR-002 — direct H10 stop-touch probability

Hypothesis:

`PATH-RISK-V2-STOP-TOUCH-H10-V1`

Candidate ordinal / ID:

`PR-002` / `PATH-RISK-V2-STOP-H10-HGB-002`.

Model:

- exact 33 feature columns;
- `ColumnTransformer`, numeric columns only;
- median `SimpleImputer(add_indicator=True, keep_empty_features=True)`;
- no scaler;
- `HistGradientBoostingClassifier`;
- learning rate `0.05`;
- max iterations `200`;
- max leaf nodes `31`;
- L2 regularization `1.0`;
- random state `42`.

Output is raw model `P(stop_touch_h10=1 | X)`.  V2 does not add a post-hoc
calibrator.  Calibration is evaluated diagnostically and, if a risk model later
survives F5/F6, any calibration layer must be a separate causal study.

## 7. Candidate PR-003 — discrete competing-risk barrier model

Hypothesis:

`PATH-RISK-V2-DISCRETE-COMPETING-RISK-V1`

Candidate ordinal / ID:

`PR-003` / `PATH-RISK-V2-DISCRETE-CR-HGB-003`.

Each signal is expanded into at-risk person-period rows through at most H10.
At horizon step `h`, the multiclass target is one of:

- `CONTINUE = 0`;
- `STOP = 1`;
- `TP = 2`.

Event construction:

- `SL_FIRST` -> STOP on its first-barrier session;
- `AMBIGUOUS_SAME_BAR` -> STOP on its first-barrier session under the same
  conservative stop-touch convention used by the binary endpoint;
- `TP_FIRST` -> TP on its first-barrier session;
- `NO_BARRIER_HIT` -> CONTINUE through H10.

Rows after the first event are never created.

Model preprocessing is the same as PR-002, with model columns equal to the 33
causal features plus deterministic `path_horizon_step`.  Estimator:

- `HistGradientBoostingClassifier` multiclass;
- learning rate `0.05`;
- max iterations `200`;
- max leaf nodes `31`;
- L2 regularization `1.0`;
- random state `42`.

For a new signal, the model predicts conditional probabilities at H1..H10.  The
stop cumulative incidence is computed recursively:

```text
S(0) = 1
CIF_stop(h) = CIF_stop(h-1) + S(h-1) * p_stop(h)
CIF_tp(h)   = CIF_tp(h-1)   + S(h-1) * p_tp(h)
S(h)        = S(h-1) * p_continue(h)
```

The comparable V2 output is `CIF_stop(10)`, interpreted as the model's H10
stop-touch probability.  H3/H5 stop CIF, H10 TP CIF and H10 survival are
candidate-specific diagnostics.

## 8. Frozen comparators

Every fold reports two comparators.

### 8.1 Training base-rate comparator

Predict the outer-training prevalence of `stop_touch_h10` for every validation
row.

### 8.2 Fold-specific alpha-only comparator

This comparator tests whether a separate risk model adds information beyond
alpha itself.

Within each outer training fold only:

1. fit the exact V3-B Structure-Lite HGB architecture using only `TP_FIRST` and
   `SL_FIRST` training rows, with `TP_FIRST=1`, `SL_FIRST=0`;
2. produce raw alpha scores on all outer-training and validation Path Risk rows;
3. fit a one-dimensional logistic mapping from training alpha score to
   `stop_touch_h10` using `LogisticRegression(C=1_000_000, solver="lbfgs",
   max_iter=1000)`;
4. apply that mapping to validation alpha scores.

No final all-history V3-B refit is used in F1-F4 comparators.  This avoids
historical leakage.  The alpha-only comparator is not a Path Risk candidate.

## 9. Frozen folds

Development uses only:

- F1: train `1..504`, gap `505..524`, validation `525..624`;
- F2: train `1..624`, gap `625..644`, validation `645..744`;
- F3: train `1..744`, gap `745..764`, validation `765..864`;
- F4: train `1..864`, gap `865..884`, validation `885..984`.

F5/F6 are prohibited in the V2 discovery runner.

## 10. Frozen metrics

For each candidate and comparator on each fold report:

- binary log loss;
- Brier score;
- ROC-AUC;
- PR-AUC;
- validation stop-touch prevalence;
- mean predicted probability;
- fixed equal-width 10-bin ECE;
- within-date predicted-risk quintiles;
- Q1 and Q5 stop-touch rate;
- Q5-Q1 stop-touch-rate spread;
- Spearman correlation between predicted risk and realized
  `adverse_excursion_r`;
- finite prediction rate and unique prediction count.

For each candidate also report:

```text
relative_logloss_improvement_vs_base
relative_brier_improvement_vs_base
relative_logloss_improvement_vs_alpha
relative_brier_improvement_vs_alpha
```

where positive values mean the candidate is better.

PR-003 additionally reports stop CIF at H3/H5/H10, TP CIF H10, survival H10,
and the maximum probability-mass conservation error.

## 11. Frozen F1-F4 candidate gate

A candidate is discovery-eligible only if all are true:

1. all required predictions/metrics are finite and probability bounds pass;
2. relative log-loss improvement vs base rate is `>=0` on at least `3/4` folds;
3. median relative log-loss improvement vs base rate is `>= +0.005`;
4. relative Brier improvement vs base rate is `>=0` on at least `3/4` folds;
5. relative log-loss improvement vs alpha-only is `>=0` on at least `3/4` folds;
6. median relative log-loss improvement vs alpha-only is `>= +0.002`;
7. ROC-AUC is `>0.5` on at least `3/4` folds and median ROC-AUC is `>=0.55`;
8. Q5-Q1 stop-touch-rate spread is positive on `4/4` folds;
9. median Q5-Q1 stop-touch-rate spread is `>= +0.08`.

ECE and Spearman are diagnostics, not gates.  This avoids changing the V2
objective into a post-hoc ordering rescue of V1.

## 12. Frozen candidate selection

- If neither PR-002 nor PR-003 passes: `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE` and
  F5/F6 stay sealed.
- If exactly one passes: select that candidate.
- If both pass: choose the candidate with the higher median
  `relative_logloss_improvement_vs_alpha`.
- If the two medians differ by `<=0.002`, choose simpler PR-002.

The selected status is:

`PATH_RISK_V2_DISCOVERY_WINNER_SELECTED`.

Only one selected candidate may ever proceed to a separately authorized F5/F6
confirmation.  F5/F6 may not be used to choose between PR-002 and PR-003.

## 13. Candidate accounting

Path Risk uses its own permanent ordinal ledger:

- PR-001: viewed / V1 FAIL_CLOSE;
- PR-002: reserved for V2 direct H10 stop-touch HGB;
- PR-003: reserved for V2 discrete competing-risk HGB.

Once a PR-002/003 F1-F4 outcome is viewed, that ordinal remains permanently
viewed regardless of result.  The alpha ranking denominator remains `17`.

## 14. Runtime / implementation contract

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` is mandatory first-read.
Relevant rules for V2:

- reuse the immutable V1 joined model table rather than rebuild path targets;
- use projected Parquet reads;
- vectorize PR-003 person-period expansion;
- profile cache read, alpha comparator, candidate fit/score and serialization;
- do not introduce unrestricted parallelism before profiling;
- exact semantics/provenance take priority over speed.

Implementation/tests may use synthetic fixtures and the already-viewed V1 table
identity.  Preparing code does not itself authorize a real PR-002/003 run.

## 15. Hard boundary

Do not:

- rerun/rescue PR-001;
- change V1 q75 target or reinterpret V1 as a winner;
- add PR-004 or additional V2 candidates after seeing PR-002/003;
- change the 33 market features;
- use final V3-B score as a candidate input;
- access Path Risk F5/F6 in V2 discovery;
- access post-2026-07-31 forward outcomes;
- create risk veto, reranking, sizing, execution, or alpha+risk integration rules;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- modify the final V3-B ranker.
