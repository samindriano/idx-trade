# Ranking V3-B Final Refit and Fresh-Forward Specification V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **FROZEN PRE-OUTCOME SPEC — IMPLEMENTATION/FINAL REFIT MAY FOLLOW REVIEW; FRESH OUTCOME ACCESS NOT AUTHORIZED**

## 1. Purpose

The historical ranking architecture search is closed. The final historical-development ranker is:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

This specification freezes:

1. one final historical-development refit of that exact architecture;
2. an outcome-blind forward feature/scoring runtime;
3. the first independent fresh-forward ranking verdict.

It does not authorize reading post-2026-07-31 outcomes, writing `FORWARD_OUTCOME_ACCESS_STARTED`, calibration, execution/PnL, paper/live trading, or main merge.

## 2. Frozen architecture

The ranker is exact V3-B Structure-Lite: the frozen V2 `HGB_XS_MARKET` 25-feature information set plus the exact eight Structure-Lite features.

Exact appended Structure-Lite feature order:

1. `structure_support_distance_atr`
2. `structure_resistance_distance_atr`
3. `structure_support_touch_count_60`
4. `structure_resistance_touch_count_60`
5. `structure_nearest_level_age_sessions`
6. `structure_role_reversal_count_120`
7. `structure_breakout_retest_state`
8. `structure_breakout_volume_confirmed`

The complete model feature order is the existing `V3_B_FEATURE_COLUMNS`: exact V2 25-feature prefix followed by the exact eight columns above. Its canonical feature-order SHA-256 is:

`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`

The model is unchanged:

- training-only median `SimpleImputer`;
- `add_indicator=True`;
- `keep_empty_features=True`;
- no scaler;
- `HistGradientBoostingClassifier`;
- `learning_rate=0.05`;
- `max_iter=200`;
- `max_leaf_nodes=31`;
- `l2_regularization=1.0`;
- `random_state=42`;
- ranking score = logit of clipped positive-class `predict_proba` under the existing V2/V3 semantics.

The score is **not a calibrated probability**.

No Structure-Lite formula, threshold, pivot rule, clustering rule, touch rule, role-reversal rule, breakout/retest rule, volume-confirmation rule, feature, preprocessing step, model parameter, label, or universe rule may change.

## 3. Historical final-refit contract

The final refit is a training operation only. It is not another validation experiment.

Use the immutable V2 resolved-primary-H10 prepared table:

- cache SHA-256 `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- manifest SHA-256 `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- exact rows/tickers/signal sessions `292,633 / 737 / 20..1250`.

Use the immutable signal-research sources:

- panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Structure-Lite is recomputed causally on the immutable signal panel through signal session `1250`, then joined one-to-one onto the exact V2 prepared rows by `(ticker,date)`.

Mandatory invariants:

- exact `292,633` V2 training rows retained;
- exact `737` tickers retained;
- exact signal-session range `20..1250`;
- no duplicate `(ticker,date)`;
- no orphan V2 row;
- every original V2 identity/target/25-feature value is unchanged;
- exact 25+8 feature order/hash above;
- no infinity in Structure-Lite columns;
- missing Structure-Lite values remain missing for the frozen training-only imputer; they do not cause row deletion;
- no performance metric, fold, candidate comparison, feature selection, pruning, or threshold decision is computed from sessions `1225..1250`.

Sessions `1225..1250` were not part of V3/V4 architecture selection. They may enter the final fit only because all historical architecture choices are now closed. Their labels may not be inspected as a new validation slice.

Run exactly one model fit. Serialize the model and JSON manifest, hash both, and record environment/source/code identities. A mechanical failure before fit may be fixed only to restore this exact frozen contract; there is no alternative model or feature candidate.

## 4. Causal forward input contract

Fresh-forward signal dates are official IDX sessions strictly after `2026-07-31`.

The forward input must be an immutable, hash-pinned **signal-safe ACTIVE-only regular-market snapshot** with the historical prefix required by all rolling V2 and Structure-Lite features. It must preserve the project's existing PIT common-stock identity, listing, official-session, tradability, corporate-action, and raw execution-price semantics.

At minimum, feature construction needs:

- `ticker`, `date`;
- regular-market `high`, `low`, `close`, `volume`, `regular_market_value`;
- official exchange sessions;
- listing-origin information required by the existing causal universe logic.

Open is not a ranker feature and is never synthesized.

Outcome-blind feature construction must reject target/outcome columns. Provider presence must not define official tradability. Current-survivor shortcuts, future listing information, future bars, future labels, forward-filled prices, synthetic OHLC, and silent provider substitution are prohibited.

## 5. Forward feature construction

For every fresh signal session `t`:

1. build the exact existing causal baseline/V2 feature table from the full signal-safe historical prefix through `t`;
2. compute same-date V2 cross-sectional ranks and market context using the full causal primary-liquid universe on `t`, not only future label-resolved rows;
3. independently compute exact Structure-Lite geometry using only observations at or before `t` and official-session identity;
4. join the eight Structure-Lite columns one-to-one onto the V2 rows by `(ticker,date)`;
5. retain only `universe_primary_liquid == true` rows for model scoring;
6. preserve missing Structure-Lite values for the frozen imputer;
7. score with the exact serialized final V3-B model.

Appending future rows to the input must not change features or scores for an earlier signal date.

Rows failing PIT/data/causal-history requirements are excluded from the scored forward universe and reported explicitly. They are never silently repaired.

## 6. H10 maturity and first independent block

Use the existing H10 TP-before-SL label contract unchanged.

A signal session is mature only when official sessions `t+1..t+10` exist and the complete required H10 evidence is defensible. Missing endpoints, unresolved tradability, unresolved price evidence, revision conflicts, or other failed evidence conditions make the signal session immature/unresolved for the verdict.

The first independent verdict uses **exactly the first 100 consecutive mature official forward signal sessions strictly after 2026-07-31**.

No outcome for that block may be inspected before all 100 signal sessions are mature and the exact block is frozen outcome-blind. No shorter interim score, rolling monitor, overlapping-window verdict, or early peek is permitted.

Split the block, before outcome access, into:

- first 50 signal sessions;
- last 50 signal sessions.

## 7. Frozen forward metrics

Use the exact existing `evaluate_v2_scores` ranking semantics on the resolved forward sample:

- resolved row count and expected/eligible coverage diagnostics;
- positive prevalence;
- PR-AUC;
- PR-AUC minus prevalence;
- ROC-AUC;
- within-date Q1 TP rate;
- within-date Q5 TP rate;
- Q5-Q1 TP-rate spread;
- within-date top-decile TP rate;
- top-decile lift versus block prevalence.

Compute aggregate metrics and the same required metrics for the first-50 and last-50 halves.

No realized-return spread, calibration metric, PnL metric, threshold search, portfolio construction, or execution metric is part of this verdict.

## 8. Frozen PASS / MIXED / FAIL rule

To avoid inventing a more convenient threshold after V4, reuse the already-frozen Ranking-V2 fresh-forward decision semantics unchanged for the final V3-B ranker.

`PASS` only when:

- all data/provenance/maturity gates pass;
- all required metrics are finite;
- aggregate PR-AUC minus prevalence > 0;
- aggregate ROC-AUC > 0.50;
- aggregate Q5-Q1 TP-rate spread > 0;
- first-50 PR-AUC minus prevalence > 0;
- first-50 Q5-Q1 > 0;
- last-50 PR-AUC minus prevalence > 0;
- last-50 Q5-Q1 > 0.

`MIXED` only when all data/provenance/maturity gates pass and aggregate PR-AUC minus prevalence and aggregate Q5-Q1 are positive, but at least one PASS stability/ROC condition is not met.

`FAIL` for any data/provenance/maturity failure, non-finite required metric, non-positive aggregate PR-AUC delta, or non-positive aggregate Q5-Q1 spread.

No post-result rescue, threshold relaxation, alternate block, reweighting, feature change, V2 fallback selection, or second one-shot verdict is allowed.

The historical V2 model may remain archived as a research reference, but the first fresh block is reserved for the final V3-B architecture and must not be used to adaptively choose between V2 and V3-B afterward.

## 9. One-shot provenance and access marker

Before any fresh-forward outcome is read:

1. final V3-B model and manifest must already be frozen and hash-verified;
2. all forward source snapshots must be immutable and hash-pinned;
3. the exact 100-session mature block must be selected outcome-blind;
4. a pre-outcome manifest must record the spec identity, code commit, model/manifest hashes, exact 33-feature order/hash, source hashes, environment, and intended 100-session block;
5. that pre-outcome manifest must be written and SHA-256 hashed;
6. `FORWARD_OUTCOME_ACCESS_STARTED` must then be atomically written in the parent immutable snapshot directory **before** the outcome set is loaded;
7. the run must refuse to start if the global marker already exists.

If a process crashes after the marker is written, the block is consumed and cannot be rerun as an independent verdict.

Every resulting artifact must be content-hashed. The final report must state that this is independent ranking validation only, not calibration, PnL, or live readiness.

## 10. Runtime implementation rule

Reuse existing tested V2 forward primitives where semantics are identical:

- immutable final-refit artifact verification;
- H10 maturity diagnostics;
- first exact 100-session block selection;
- `evaluate_v2_scores` metric semantics;
- fixed PASS/MIXED/FAIL logic;
- pre-outcome manifest structure;
- global marker refusal/atomic write;
- deterministic hashing/environment capture.

Add only the exact V3-B Structure-Lite training-table join, final model fit, forward Structure-Lite join, exact feature-order verification, and final-model scoring layer.

Follow `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`. Engineering optimization is permitted only with semantic equivalence; it cannot change model/research behavior.

## 11. Authorization boundary

After independent review of this specification, the following may be separately authorized now:

- implementation and tests for the final V3-B refit/runtime;
- one final historical fit on exact rows `20..1250`;
- model/manifest serialization and hashing;
- outcome-blind forward feature/maturity/provenance tooling.

Still prohibited until a later explicit authorization:

- reading/summarizing post-2026-07-31 outcomes;
- writing `FORWARD_OUTCOME_ACCESS_STARTED` outside synthetic/temp tests;
- producing the 100-session forward verdict;
- rerunning historical feature/model selection;
- calibration or probability claims;
- Stage 6 / `IDX-VAL-002`;
- execution/PnL, Kelly, portfolio sizing;
- paper/live trading;
- merge to main.
