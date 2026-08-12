# IDX Trade — 100-Session Forward Evaluation Protocol V1

Date: 2026-08-13 (Asia/Jakarta)
Branch: `research/idx-forward-evaluation-protocol-v1`
Decision: `FORWARD_100_SESSION_EVALUATION_PROTOCOL_V1_FROZEN_OUTCOME_BLIND`

## Purpose

Freeze the evaluation order and decision rules for the first O2 100-session fresh-forward vault **before any protected forward outcome is accessed**.

This protocol does not read outcomes, change a model, change a score, change O2 eligibility, alter the O2 counter, create a trading rule, or authorize O2.1 promotion. It coordinates the already-frozen O2 primary evaluation with the already-accepted Reliability V1 shadow so both are evaluated from one immutable outcome access rather than through repeated or adaptive peeking.

## Controlling parents

### O2 fresh-forward parent

- active model: `O2-GEOMETRY-FULL3-V1-CANDIDATE-001`;
- O2 model SHA-256: `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb`;
- O2 feature-order SHA-256: `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- O2 counter schema: `idx-trade/o2-forward-counter-v1`;
- O2 frozen gate length: exactly `100` consecutive official post-freeze sessions;
- first accepted session: `2026-08-12`, official session index `1268`;
- first-session score SHA-256: `b7fc6f22230500d65c1a24c4333b5601c0102da5bb99c3cae77a85bdb112c42d`;
- first-session manifest SHA-256: `4f3d7814333b867316092758b8530270a14d2e741bc8cca2c12c1dffbc99b5e2`;
- accepted first-session review: `O2_FORWARD_SESSION_1268_ACCEPTED_COUNTER_1_OF_100`.

The forward counter is the sole official vault trigger. Reliability and O2.1 do not create another counter.

### Existing fresh-forward decision semantics

This protocol preserves the existing Ranking fresh-forward H10 semantics rather than inventing a new post-hoc metric family:

- exactly one first block of 100 consecutive mature official signal sessions;
- frozen H10 binary outcome contract;
- aggregate PR-AUC minus prevalence;
- aggregate ROC-AUC;
- within-session Q5-minus-Q1 TP-rate spread;
- top-decile TP-rate lift as descriptive evidence;
- fixed first-50 versus last-50 stability split;
- no calibration/probability claim;
- one-shot outcome access with a global access marker written before outcomes are loaded.

The active O2 verdict below applies these same semantics to the frozen O2 score and its frozen row-level eligibility contract.

### Reliability V1 parent

- frozen V1 spec commit: `3239a319fbd4ff492b16a74d899a20edc9affa7f`;
- accepted V1 implementation review: `a21c2665f1afa73f4e377286b6ca9096bae48ab1`;
- only scientific variable: raw `score_margin_reliability`;
- display percentile is not a scientific variable and is not evaluated;
- no independent counter, filtering, model fit, tiering, sizing, or ranking change.

Reliability V0 historical evidence is used only to define the already-frozen metric family, not to tune a new forward effect-size cutoff. The accepted V0 P1 evidence was positive across all six historical folds for Spearman, Q4-Q1 lift, top-40% selective lift, and conditional lift.

### O2.1 sealed-shadow parent

Historical O2.1 remains `O2_1_NO_SURVIVOR_ACCEPTED_LANE_CLOSED` at acceptance `32ee9ee1e5696b2262b4defc936846dff5af557e`.

A later score-only sealed shadow was separately authorized for prospective diagnostics, but it has no promotion eligibility and no independent counter. Its implementation is currently under bounded engineering review. **O2.1 outcomes are not part of the first O2/Reliability one-shot verdict defined here.**

## 1. Vault eligibility

The first outcome access is permitted only when all of the following are true:

1. the canonical O2 counter equals exactly `100/100`;
2. the 100 O2 sessions are consecutive under the frozen official-session counter contract;
3. all 100 signal sessions are H10-mature under the existing outcome evidence contract;
4. all 100 accepted O2 score artifacts/manifests pass hash, model, feature-order, source-snapshot, eligibility, session-index, and outcome-clean verification;
5. the Reliability V1 sidecar for every O2 session either exists and validates against its exact O2 source bundle, or the Reliability lane is explicitly declared `INCONCLUSIVE_DATA` before outcomes are loaded; missing sidecars must not be silently rebuilt from outcomes;
6. this protocol file and the evaluator implementation have been committed and hash-pinned before outcome access;
7. no global `FORWARD_OUTCOME_ACCESS_STARTED` marker already exists;
8. no protected forward outcome has previously been inspected manually, through UI, through an exploratory script, or through another evaluation lane.

If O2 itself fails a provenance/maturity gate, do not open the vault.

## 2. One-shot access order

Before loading any forward labels/outcomes, the evaluation runtime must write an immutable pre-outcome manifest containing at minimum:

- this protocol file SHA-256 and commit;
- evaluator code commit;
- exact 100 official session dates and indices;
- exact O2 model/model-manifest/feature-order pins;
- all 100 O2 score-artifact and session-manifest hashes;
- all available Reliability V1 sidecar and manifest hashes;
- exact calendar/security/tradability/corporate-action/source-snapshot revisions required by the existing O2 outcome contract;
- environment/dependency identity;
- runtime flags confirming no pre-access outcome read.

Then, and only then:

1. atomically write the global `FORWARD_OUTCOME_ACCESS_STARTED` marker in the controlling frozen forward snapshot/runtime location;
2. load the complete protected outcome set once;
3. materialize one immutable resolved/unresolved outcome frame for the 100-session block;
4. compute the O2 primary verdict first;
5. compute Reliability V1 from the same immutable O2/outcome frame second;
6. do **not** evaluate O2.1 in this run;
7. persist report artifacts and a hash inventory.

If the process crashes after the marker is written, the block is consumed. Do not erase the marker or rerun the same first-block verdict in a fresh directory.

## 3. O2 primary verdict

### Sample

Use only rows that were frozen as `o2_eligible=true` and received a finite accepted O2 score on their signal session. Never synthesize scores for true flat-range zero-denominator exclusions or any other O2-ineligible row.

H10 outcomes use the existing frozen TP-first / SL-first binary-target semantics and evidence rules. Unresolved rows remain unresolved; they are not coerced to either class.

### Required report metrics

Report at minimum:

- expected O2-scored rows;
- resolved outcome rows;
- unresolved/unknown rows and reasons;
- outcome coverage;
- positive prevalence;
- PR-AUC;
- `PR-AUC - prevalence`;
- ROC-AUC;
- within-session Q1 TP rate;
- within-session Q5 TP rate;
- `Q5 TP rate - Q1 TP rate`;
- within-session top-decile TP rate;
- top-decile lift versus prevalence.

All gating metrics must be finite on one frozen resolved sample.

### Stability split

Split the 100 signal sessions by the frozen session order:

- early half: sessions `1..50`;
- late half: sessions `51..100`.

Do not optimize or move the split.

### O2 decision rule

`O2_FORWARD_PASS` only if:

- all provenance/maturity gates pass;
- all required gating metrics are finite;
- aggregate `PR-AUC - prevalence > 0`;
- aggregate `ROC-AUC > 0.50`;
- aggregate `Q5-Q1 TP-rate spread > 0`;
- early-half `PR-AUC - prevalence > 0`;
- late-half `PR-AUC - prevalence > 0`;
- early-half `Q5-Q1 TP-rate spread > 0`;
- late-half `Q5-Q1 TP-rate spread > 0`.

`O2_FORWARD_MIXED` only if all provenance/maturity gates pass and both aggregate core ranking gates are positive (`PR-AUC - prevalence > 0` and `Q5-Q1 > 0`), but at least one PASS stability/ROC condition above fails.

`O2_FORWARD_FAIL` for any provenance/maturity failure after vault eligibility, any non-finite gating metric, aggregate `PR-AUC - prevalence <= 0`, or aggregate `Q5-Q1 <= 0`.

Top-decile lift is reported but is not an independent rescue gate.

No later metric may rescue or reinterpret the O2 verdict.

## 4. Reliability V1 forward evaluation

### Evaluation sample and target

Reliability is evaluated only on the exact O2-scored rows in the same 100-session block for which:

- the accepted Reliability V1 raw `score_margin_reliability` is finite;
- the frozen H10 `binary_target` is resolved;
- the signal session contains at least 30 eligible evaluated O2 rows and both H10 classes.

For each metric-eligible session, compute row-level `local_pairwise_quality` exactly as Reliability V0:

- positive row: fraction of negative-class peers with lower O2 score, plus half credit for score ties;
- negative row: fraction of positive-class peers with higher O2 score, plus half credit for score ties.

Do not use `reliability_percentile` for the scientific verdict.

### Frozen per-session metric family

For every metric-eligible session compute exactly:

1. Spearman correlation between raw `score_margin_reliability` and `local_pairwise_quality`;
2. `Q4-Q1` local-pairwise-quality lift using deterministic equal-count Reliability quartiles;
3. top-40% selective-quality lift versus full-session mean local quality;
4. conditional reliability lift after splitting O2 score into deterministic quintiles and comparing upper versus lower Reliability halves within score quintiles with at least 8 rows.

No new subgroup, threshold, proxy, transform, regime, or alternative coverage level may be added after outcome access.

### Reliability readiness gate

The Reliability verdict is evaluable only if:

- every included sidecar passes its frozen source/hash/protection validation;
- at least `80/100` signal sessions are metric-eligible;
- at least `40/50` sessions are metric-eligible in each fixed half;
- all four aggregate metrics below are finite in the full block and both halves.

Failure of this readiness gate yields `RELIABILITY_FORWARD_INCONCLUSIVE_DATA`, not a no-signal result, and does not change the O2 verdict.

### Aggregate metrics

For the full block and separately for each fixed half compute:

- median session Spearman;
- mean session Q4-Q1 quality lift;
- mean session top-40% selective-quality lift;
- mean session conditional quality lift.

These aggregation semantics deliberately mirror the historical V0 metric definitions and use the already-declared 50/50 forward stability split. No historical effect-size number is used as a new minimum cutoff.

### Reliability decision rule

`RELIABILITY_FORWARD_PASS` only if:

- the readiness gate passes;
- **all four** full-block aggregate metrics are strictly positive;
- **all four** early-half aggregate metrics are strictly positive;
- **all four** late-half aggregate metrics are strictly positive.

This is intentionally strict because V0's accepted P1 signal was directionally positive across all four metrics in all six historical folds.

`RELIABILITY_FORWARD_INCONCLUSIVE` if:

- the readiness gate passes;
- all four full-block aggregate metrics are strictly positive;
- but at least one corresponding half-block metric is non-positive.

This means the historical direction appears in aggregate but lacks the preregistered temporal stability needed for a production confidence layer.

`RELIABILITY_FORWARD_FAIL` if the readiness gate passes and **any** full-block aggregate metric is non-positive.

No `PASS`/`INCONCLUSIVE`/`FAIL` boundary may be changed after the outcome marker is written.

### Interpretation boundary

A Reliability PASS means only that the deterministic ex-ante margin diagnostic survived its first genuinely fresh forward validation as a **ranking-reliability signal**.

It still does not mean:

- Reliability percentile is a probability;
- a 90th percentile row has a 90% chance of success;
- Reliability should automatically filter trades;
- a LOW/MEDIUM/HIGH tier threshold has been validated;
- position sizing is authorized.

Any production tier/filter/sizing use requires a later separately frozen decision-layer contract and cannot use this same 100-session block to optimize thresholds.

## 5. Joint interpretation matrix

The two verdicts answer different questions and must not rescue each other.

- O2 `PASS` + Reliability `PASS`: O2 ranking survives and the margin diagnostic also survives. A **new** confidence-layer design may be considered, but no filter/tier is automatically authorized.
- O2 `PASS` + Reliability `INCONCLUSIVE`/`FAIL`: keep O2 verdict unchanged; Reliability remains exploratory or is closed according to its verdict.
- O2 `MIXED` + any Reliability result: Reliability may be reported scientifically, but it cannot turn O2 into PASS or authorize production confidence use.
- O2 `FAIL` + any Reliability result: O2 FAIL remains controlling. Reliability cannot rescue failed alpha.
- Reliability `INCONCLUSIVE_DATA`: no Reliability scientific verdict; O2 can still receive its own independent verdict if O2 gates pass.

There is no composite score and no combined p-value or weighted verdict.

## 6. O2.1 diagnostic boundary

O2.1 is explicitly excluded from the first one-shot O2/Reliability outcome computation.

Reasons:

1. historical O2.1 is already a frozen `NO_SURVIVOR`;
2. the sealed shadow has no promotion eligibility by contract;
3. its archive implementation is currently undergoing bounded provenance remediation;
4. adding O2.1 performance metrics to the first verdict would expand the confirmatory family without necessity.

After the first vault is consumed, a later O2.1 outcome analysis may be authorized only as an explicitly labeled **exploratory consumed-vault diagnostic** under a separate checkpoint. It can never retroactively become an independent fresh-forward promotion test on this same block.

No O2.1 result may change O2 ranking, O2 eligibility, the O2 counter, the historical `O2_1_NO_SURVIVOR`, or the O2/Reliability verdicts above.

## 7. Multiple-comparison and anti-rescue rules

The confirmatory family is fixed to:

- one O2 primary verdict;
- one Reliability V1 secondary verdict using one predefined proxy and four predefined reliability metrics.

Forbidden after outcome access:

- choosing a different horizon;
- dropping bad sessions or rows outside the frozen evidence rules;
- changing 50/50 halves;
- changing Reliability top-40% to another coverage;
- changing Reliability quartiles/quintiles;
- replacing mean with median or vice versa where this protocol specifies the aggregation;
- adding regimes, sectors, volatility buckets, score bands, ticker subsets, or market-state filters as gating evidence;
- reviving Reliability P2;
- fitting a Reliability model;
- optimizing LOW/MEDIUM/HIGH thresholds;
- using O2.1 to rescue O2;
- rerunning the consumed 100-session block under a revised rule.

Post-hoc diagnostics, if scientifically useful, must be clearly labeled exploratory and cannot modify the frozen verdicts.

## 8. Required output artifacts

The one-shot run must persist at minimum:

- `pre_outcome_contract.json`;
- immutable 100-session identity/hash inventory;
- resolved/unresolved H10 outcome frame with provenance;
- O2 aggregate metrics;
- O2 early/late-half metrics;
- O2 decision artifact;
- Reliability row-level local-pairwise-quality evaluation frame;
- Reliability per-session metrics;
- Reliability full/early/late aggregate metrics;
- Reliability readiness/decision artifact;
- joint interpretation artifact;
- final artifact manifest with SHA-256 for every output;
- runtime flags proving no second counter, model refit, threshold optimization, provider call, or pre-marker outcome access.

## 9. Implementation-before-access requirement

The evaluator may be implemented and tested before the vault is eligible, but only with synthetic fixtures or already-consumed historical-development fixtures that cannot reveal the protected fresh-forward block.

Minimum tests must cover:

- exact 100-session and 50/50 boundaries;
- O2 PASS/MIXED/FAIL boundary behavior;
- Reliability local-pairwise-quality class/tie semantics;
- deterministic Reliability quartile/top-40/quintile calculations;
- Reliability readiness `80/100` and `40/50` boundaries;
- Reliability PASS/INCONCLUSIVE/FAIL boundaries;
- no Reliability rescue of O2;
- no O2.1 inclusion;
- pre-outcome manifest written before global marker;
- marker written before outcome loader is callable;
- existing marker refuses a rerun;
- crash-after-marker behavior leaves block consumed;
- all input/source/model/sidecar hashes fail closed.

Implementation and tests do not authorize outcome access. A separate final `READY_TO_OPEN_VAULT` independent review is required after the evaluator exists and the O2 counter reaches 100/100.

## Hard stop

After this protocol is frozen, do not inspect any protected forward outcome and do not tune it based on accumulating score-only telemetry.

The next valid steps are only:

1. finish independent engineering acceptance of O2.1 sealed shadow without outcome access;
2. optionally implement/test this evaluator on synthetic/non-protected fixtures;
3. let O2 + Reliability score-only accumulation proceed unchanged;
4. when O2 reaches 100/100 and H10 maturity is complete, perform a final pre-vault audit against this exact protocol before writing the outcome-access marker.