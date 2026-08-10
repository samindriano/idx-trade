# Ranking V3 Final Structure-Lite Late-Development Confirmation Spec V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **FROZEN PRE-OUTCOME ONE-SHOT V2F5/V2F6 CONFIRMATION SPECIFICATION**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

## Purpose

Tier-1 V3 discovery is complete except for V3-D, which is parked at an external
PIT sector-history data dependency and has no viewed outcomes.

Viewed Tier-1 results:

- V3-A Recency: killed;
- V3-B Structure-Lite: promoted on V2F1-V2F4;
- V3-C Regime-Specialization: killed;
- V3-E True Ranking: killed;
- V3-D Sector-Relative: blocked before outcomes.

Therefore the only independently surviving Tier-1 component is the exact frozen
V3-B Structure-Lite candidate. There is no second surviving component to justify
an integration experiment.

This specification consumes V2F5/V2F6 exactly once as **late-development
confirmation** of the unchanged V3-B Structure-Lite architecture.

This is development evidence, not independent validation.

## Architecture frozen unchanged

Comparator:

- exact V2 `HGB_XS_MARKET` control;
- exact frozen V2 25 features;
- exact H10 binary target;
- exact V2 model/preprocessing semantics.

Candidate:

- exact V3-B `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- exact frozen V2 25-feature prefix plus the exact eight frozen causal
  Structure-Lite features;
- exact same HistGradientBoostingClassifier architecture, hyperparameters,
  seed, preprocessing, score semantics and causal feature definitions used in
  V3-B discovery.

No feature, threshold, clustering rule, structure definition, model
hyperparameter, target, universe rule or score transform may change.

The viewed V3-B definition is closed.

## Exact late-development folds

Consume exactly:

- V2F5: train `1..984`, purge `985..1004`, validation `1005..1104`;
- V2F6: train `1..1104`, purge `1105..1124`, validation `1125..1224`.

No other fold may be scored by this confirmation runner.

The prepared/feature cache may physically materialize only rows needed through
signal session `1224`. Sessions `1225+` must not be materialized by this task.

## Data and provenance identities

Use the same immutable sources as V3-B:

- signal panel SHA-256
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA-256
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master SHA-256
  `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`;
- V2 prepared table SHA-256
  `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- V2 prepared manifest SHA-256
  `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- frozen V2 HGB reference summary SHA-256
  `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`;
- frozen V2 HGB reference predictions SHA-256
  `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`.

The V3-B controlling identities remain:

- Structure-Lite spec SHA-256
  `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- Structure-Lite spec Git blob
  `0392ab506aa451355697327d416f8f2b2ea21d4f`;
- Structure-Lite review-addendum Git blob
  `717871707e833ab9818c249d52aae5b234334fc4`.

## Outcome-independent cache prepare

Before any F5/F6 score is computed, build a new immutable Structure-Lite cache
through session 1224 using the exact frozen V3-B feature builder.

Mandatory checks:

- exact source hashes above;
- exact V2 row identity/order and all existing V2 columns preserved;
- exact frozen 25-feature prefix;
- exact frozen eight Structure-Lite columns and ordering;
- no duplicate `(ticker,date)` rows;
- no orphan join rows;
- no infinite structure-feature values;
- max materialized signal session exactly `<=1224`;
- sessions `1225+` absent;
- `outcome_metrics_computed=false`.

The prepare stage may calculate feature coverage/missingness only. It must not
calculate F5/F6 target-performance metrics.

Freeze cache and manifest hashes before scoring.

## Exact V2 control equivalence

The late-development runner must execute the exact V2 control on F5/F6 first.

It must compare against the immutable V2 reference predictions using only
V2F5/V2F6 rows.

Required equivalence:

- exact row count;
- exact row identity/order;
- score `atol=1e-12`, `rtol=0`;
- prevalence, PR-AUC, PR delta, ROC-AUC, Q1/Q5 rates, Q5-Q1,
  top-decile TP rate and top-decile lift within `1e-12`.

If control equivalence fails, stop before interpreting Structure-Lite.

## One-shot confirmation gates

Because only two late-development folds exist, the gate is intentionally simple
and strict. No post-result threshold change is allowed.

### Absolute sanity

The Structure-Lite candidate must satisfy all of:

1. all required metrics finite on F5 and F6;
2. PR-AUC minus prevalence > 0 on **both** F5 and F6;
3. ROC-AUC > 0.50 on **both** F5 and F6;
4. Q5-Q1 > 0 on **both** F5 and F6.

### Paired confirmation versus exact V2 control

The candidate must satisfy all of:

1. paired PR-delta improvement >= 0 on **both** F5 and F6;
2. median paired PR-delta improvement >= `+0.001`;
3. median paired ROC-AUC change >= `-0.005`;
4. paired Q5-Q1 change >= 0 on **both** F5 and F6.

Top-decile lift remains diagnostic only, consistent with V3-B discovery.
Report it per fold and as paired change, but do not tune or rescue the candidate
from it.

### Deterministic final decision

If both absolute sanity and paired confirmation pass:

`V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS`

Otherwise:

`V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`

There is no MIXED category, feature pruning, structure ablation, threshold
change, blend, rescue variant or second late-development attempt.

## Required diagnostics

Report at minimum per F5/F6:

- prevalence;
- PR-AUC and PR delta;
- ROC-AUC;
- Q5-Q1;
- top-decile lift;
- paired PR/ROC/Q5-Q1/top-decile changes;
- validation rows, dates and tickers;
- feature finite/missingness coverage;
- top-decile Jaccard/entrants/exits versus V2 control.

Also report the two-fold aggregate:

- median/worst paired PR improvement;
- median ROC change;
- median/worst Q5-Q1 change;
- median top-decile lift change.

## Candidate accounting

This confirmation evaluates the **same already-counted V3-B architecture**,
not a new architecture candidate. Do not create a new candidate ordinal.

The cumulative V3 architecture-candidate denominator therefore remains `9`.
The ledger must instead record that ordinals 004/005 received one-shot
late-development confirmation on V2F5/V2F6.

V3-D ordinals 008/009 remain blocked/unviewed.

## After PASS

A PASS freezes exact Structure-Lite as the final V3 historical-development
architecture. It does **not** authorize:

- fresh-forward outcome access;
- calibration;
- Stage 6 / `IDX-VAL-002`;
- execution/PnL;
- Kelly sizing;
- paper/live trading;
- merge to main.

A separate forward-validation protocol is still required.

## After FAIL

A FAIL closes Structure-Lite as not late-development confirmed. Do not rescue
or re-open V2F5/V2F6. Keep exact V2 `HGB_XS_MARKET` as the active ranking
architecture pending a separately authorized future research generation.

## Hard prohibitions

Do not:

- modify the viewed V3-B feature bundle or model;
- integrate killed V3-A/C/E components;
- bypass the V3-D PIT sector data block;
- access V2F5/V2F6 before this spec and implementation are frozen;
- run V2F5/V2F6 more than once for V3;
- materialize or score sessions `1225+` in this task;
- inspect reserved post-2026-07-31 V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start calibration, Stage 6, execution, paper/live or merge main.
