# Ranking V3-C Regime-Specialization Specification V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **FROZEN BEFORE V3-C OUTCOME RUN**

Hypothesis ID: `V3-C-REGIME-V1`

This document freezes one bounded regime-specialization experiment. It does not contain V3-C model outcomes, does not inspect V2F5/V2F6, and does not access the reserved post-2026-07-31 V2 forward outcomes.

## 1. Single falsifiable question

> After the frozen V2 `HGB_XS_MARKET` already receives continuous causal market-context features, does one explicit two-state market-regime specialization improve robust ranking performance, especially in stressed market states, beyond the exact V2 control?

This experiment tests **architecture / conditional specialization only**. It does not add Structure-Lite, recency weighting, sector information, new labels, macro data, technical-indicator libraries, or a new model family.

V3-B Structure-Lite remains an independently surviving component and is intentionally **not inherited** here. If V3-C survives, any later Structure-Lite + Regime combination requires the separately preregistered one-shot V3 integration experiment.

## 2. Candidate budget

Exactly two candidate slots are frozen:

1. `V3-C-REGIME-V1-CONTROL-006` — exact V2 `HGB_XS_MARKET` global control;
2. `V3-C-REGIME-V1-TWO-EXPERT-007` — two-state gated HGB experts defined below.

There is no second regime definition, no threshold grid, no three-state variant, no blending coefficient, no expert hyperparameter search, and no rescue candidate.

## 3. Exact V2 control and invariant model semantics

The control is the exact frozen V2 champion:

- exact H10 first-touch label and ambiguity semantics;
- exact causal primary-liquid universe;
- exact 25 V2 feature columns and order;
- exact median `SimpleImputer(add_indicator=True, keep_empty_features=True)` preprocessing;
- exact `HistGradientBoostingClassifier` parameters: `learning_rate=0.05`, `max_iter=200`, `max_leaf_nodes=31`, `l2_regularization=1.0`, `random_state=42`;
- no scaler;
- uniform training weights;
- exact logit of clipped `predict_proba()[:,1]` ranking-score semantics;
- exact V2 metrics and within-date bucket semantics.

The V3-C specialist experts use **the same 25 feature columns and exact same pipeline/hyperparameters**. Regime state is a routing variable, not an additional model feature.

## 4. Outcome-blind two-state regime definition

### 4.1 Source market-context series

The regime definition uses only three market-wide variables already present in frozen V2 market context:

1. `market_breadth_return_20_positive`;
2. `market_median_close_return_20`;
3. `market_median_atr14_over_close`.

They must be recomputed outcome-independently from the frozen signal-research panel through the existing baseline + V2 feature pipeline over the full causal primary-liquid universe. The resolved-label prepared table must **not** be used to define rolling regime thresholds because its row/date availability is outcome-bearing.

For each official signal session there must be exactly one market-context row. Same-date repeated values across primary-liquid securities must agree exactly within `1e-12`.

### 4.2 Causal threshold history

For signal session `t`, each regime threshold uses prior official sessions only:

`H_t = [t-252, ..., t-1]` clipped at the beginning of the certified calendar.

Current-session context never enters its own threshold distribution.

For each of the three source series separately:

- retain finite prior observations inside `H_t`;
- require at least `126` finite prior official-session observations;
- calculate quantiles in float64 with linear interpolation;
- otherwise regime state for `t` is `MISSING_WARMUP`.

Frozen thresholds:

- breadth threshold = prior-history 25th percentile;
- return threshold = prior-history 25th percentile;
- volatility threshold = prior-history 75th percentile.

No expanding/full-sample quantile and no validation-period information is allowed.

### 4.3 Stress votes and state

For a session with valid thresholds and finite current context:

- `breadth_stress = market_breadth_return_20_positive_t <= breadth_q25_t`;
- `return_stress = market_median_close_return_20_t <= return_q25_t`;
- `volatility_stress = market_median_atr14_over_close_t >= atr_q75_t`.

Define:

`stress_votes = breadth_stress + return_stress + volatility_stress`.

Regime state is:

- `STRESS` when `stress_votes >= 2`;
- `NORMAL` when `stress_votes <= 1`;
- `MISSING_WARMUP` only when the causal threshold/current-context contract is unavailable.

The 2-of-3 rule is frozen before V3-C outcomes. It represents joint relative weakness/elevated volatility rather than optimizing a single market threshold.

## 5. Outcome-independent V3-C discovery cache

Build a new immutable V3-C cache. Do not modify the frozen V2 prepared cache.

The prepare step must:

1. SHA-verify the frozen signal panel, official calendar, security master, V2 prepared table, and V2 manifest;
2. physically materialize only exact V2 prepared rows with `signal_session_index <= 984` using a Parquet predicate;
3. bound raw feature/context construction at official session `984`;
4. recompute causal baseline/V2 market context from the outcome-independent panel;
5. prove the three recomputed context values equal the existing V2 prepared values on every joined discovery row within `1e-12`;
6. derive one causal regime row per official session;
7. join `regime_state`, `stress_votes`, and audit thresholds/votes to exact V2 discovery rows by signal session/date;
8. preserve exact V2 row order, labels, and all 25 V2 feature values;
9. fail closed on duplicate, orphan, date/session mismatch, non-finite context inconsistency, or provenance mismatch.

The cache may contain regime-audit columns, but the specialist model sees only the exact 25 V2 features. `MISSING_WARMUP` rows may exist in early training history but must never occur in F1-F4 validation.

V2F5/V2F6 rows must not be materialized, loaded, scored, or summarized.

## 6. Coverage / sample-fragmentation gate before model outcomes

Because the hypothesis explicitly fragments the sample, coverage is a hard pre-score requirement.

For every discovery fold:

### Training

Each of `NORMAL` and `STRESS` must contain at least:

- `40` distinct official training signal sessions; and
- `5,000` resolved training rows.

`MISSING_WARMUP` training rows are excluded from specialist fitting and their counts must be reported. They are not relabeled as NORMAL.

### Validation

Every validation row must have a non-missing regime.

Within each 100-session validation block, each of `NORMAL` and `STRESS` must contain at least:

- `8` distinct official signal sessions; and
- `500` validation rows.

If any fold fails this gate, V3-C is `BLOCKED_REGIME_NOT_EVALUABLE` before specialist outcome scoring. Do not modify quantiles, history length, or vote rule to rescue it under this hypothesis.

## 7. Frozen specialist architecture

For each F1-F4 fold:

1. fit the exact V2 global control on all exact fold training rows;
2. prove control equivalence before interpreting any specialist result;
3. for the specialist candidate, remove only `MISSING_WARMUP` rows from expert training;
4. fit one exact V2 HGB pipeline on `NORMAL` training rows;
5. fit one exact V2 HGB pipeline on `STRESS` training rows;
6. every validation session routes **all securities on that date** to the expert matching the market-wide state;
7. concatenate the routed raw logit scores in original validation row order;
8. evaluate using exact V2 metrics without score rescaling, calibration, blending, date normalization, thresholds, or post-hoc alignment.

Because market regime is date-wide, all securities within a signal date use the same expert. Separate-expert score-scale differences are part of the hypothesis and are not corrected after seeing results.

No global-model fallback is allowed in F1-F4 validation because validation regime coverage is required to be complete. No expert may see another state's rows.

## 8. Folds and evidence boundary

Discovery uses exactly V2F1-V2F4:

- F1: train `1..504`, gap `505..524`, validate `525..624`;
- F2: train `1..624`, gap `625..644`, validate `645..744`;
- F3: train `1..744`, gap `745..764`, validate `765..864`;
- F4: train `1..864`, gap `865..884`, validate `885..984`.

V2F5/V2F6 remain sealed for one final-V3 late-development confirmation only. All history through 2026-07-31 remains development knowledge, never independent validation.

## 9. Overall metrics and gates

Report exact V2 per-fold metrics for control and specialist:

- prevalence;
- PR-AUC;
- `PR-AUC - prevalence`;
- ROC-AUC;
- Q1/Q5 TP rates and Q5-Q1;
- top-decile TP rate/lift.

The specialist must pass the same frozen discovery absolute sanity gate used by V3-A/B:

1. all required metrics finite;
2. median PR delta > 0;
3. positive PR delta in at least 3/4 folds;
4. median ROC > 0.50;
5. ROC > 0.50 in at least 3/4 folds;
6. median Q5-Q1 > 0;
7. positive Q5-Q1 in at least 3/4 folds.

It must also pass the same paired overall promotion gate versus exact V2 control:

1. median PR-delta improvement >= `+0.001`;
2. q25 PR-delta improvement >= `0`;
3. worst-fold PR-delta improvement >= `0`;
4. PR not below control in at least 3/4 folds;
5. median ROC change >= `-0.005`;
6. median Q5-Q1 change >= `-0.005`;
7. Q5-Q1 not below control in at least 3/4 folds.

Top-decile lift remains mandatory diagnostic and cannot rescue a failed gate.

## 10. Regime-specific robustness gate

In addition to overall metrics, evaluate control and specialist separately inside NORMAL and STRESS validation rows for each fold using the exact same score/metric functions. Because every date has one regime, within-date bucket semantics remain valid inside each regime subset.

For each regime calculate paired candidate-minus-control changes across F1-F4.

Promotion additionally requires all of:

1. `STRESS` median paired PR-delta improvement >= `+0.001`;
2. `STRESS` PR-delta improvement >= `0` in at least `3/4` folds;
3. `NORMAL` median paired PR-delta improvement >= `-0.001`;
4. worst PR-delta improvement across all eight fold-regime cells >= `-0.005`;
5. median ROC change in each regime >= `-0.005`;
6. median Q5-Q1 change in each regime >= `-0.005`.

Mandatory diagnostics, not rescue rules:

- per-regime prevalence and number of dates/rows;
- per-regime q25/worst PR improvement;
- per-regime top-decile lift change;
- F4 regime behavior;
- expert training rows/dates and discarded warmup rows.

This gate is intentionally asymmetric: the hypothesis must demonstrate meaningful benefit in STRESS while not materially damaging NORMAL.

## 11. Deterministic verdict

- Contract/provenance/coverage failure before specialist scores: `V3_C_REGIME_BLOCKED_KEEP_V2_CONTROL`.
- Clean specialist failing absolute, overall paired, or regime-specific gate: candidate `KEEP_DIAGNOSTIC`, decision `V3_C_REGIME_KILL_KEEP_V2_CONTROL`.
- Clean specialist passing all three gates: `PROMOTE_FOR_NEXT_RESEARCH_STEP`, decision `V3_C_REGIME_PROMOTE_TWO_STATE_EXPERTS`.

There is no rescue regime, alternate threshold, expert blend, or rerun under this spec.

## 12. Control-equivalence gate

Before specialist metrics may be interpreted, the exact V2 control must reproduce immutable V2 F1-F4 artifacts with:

- exact row identity/order;
- row-level scores under `rtol=0`, `atol=1e-12`;
- prevalence, PR-AUC, PR delta, ROC, Q1/Q5, Q5-Q1, top-decile TP/lift under `1e-12`.

Failure is a hard stop. Do not weaken tolerance or replace the frozen V2 reference.

## 13. Testing requirements

Before an outcome run, focused tests must cover at least:

- thresholds use prior sessions only;
- current session cannot alter its own q25/q75 thresholds;
- exact 252-session history cap and 126-observation warmup;
- official-session gaps do not compress history into row counts;
- deterministic linear quantiles and equality boundary votes;
- exact 2-of-3 state rule;
- one unique market regime per date;
- no label/outcome dependency in regime construction;
- V2 market-context equivalence after recomputation;
- exact V2 25-feature prefix preserved;
- specialist training state isolation;
- validation routing preserves original row order;
- missing validation regime fails closed;
- sample-fragmentation coverage gate;
- F5/F6 hard block;
- provenance/hash mismatch fail closed;
- control equivalence pass/fail behavior.

## 14. Ledger and provenance

Preregister ledger ordinals:

- `006` control;
- `007` two-state specialist.

The cumulative evaluated candidate count remains `5` until actual V3-C outcomes are run. The cache/manifest, regime coverage, thresholds, metrics, regime metrics, predictions, model artifacts, runtime, verdict, and SHA-256 inventory must be immutable and documented after execution.

## 15. Hard prohibitions

Do not:

- include V3-B Structure-Lite in this V3-C candidate;
- reopen V3-A or V3-B definitions;
- search regime thresholds/windows/vote rules;
- add macro/sector/event/broker-flow data;
- score or summarize V2F5/V2F6;
- inspect reserved V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-D/V3-E or V3 integration automatically;
- calibrate probability, run Stage 6/IDX-VAL-002, execution-PnL, Kelly, paper/live, or merge main.

Stop after the frozen V3-C result and independent review.