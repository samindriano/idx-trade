# Ranking V3-D Sector-Relative — Post-V3-C Pre-Outcome Amendment V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **FROZEN PRE-OUTCOME AMENDMENT — V3-D OUTCOMES STILL NOT AUTHORIZED**

Parent hypothesis: `V3-D-SECTOR-RELATIVE-V1`

This is the one allowed V3-C-informed amendment described by the provisional V3-D specification and review addendum. It is frozen after the V3-C F1-F4 result was independently reviewed and before any V3-D F1-F4 outcome was viewed.

## 1. V3-C evidence consumed

V3-C tested one global V2 control against one NORMAL/STRESS two-expert architecture using the exact V2 25-feature representation.

Authoritative result:

`V3_C_REGIME_KILL_KEEP_V2_CONTROL`

Key historical-development observations:

- exact V2 control equivalence passed on 84,732 rows with maximum score/metric difference `0.0`;
- two-expert absolute sanity passed but overall paired promotion failed;
- median overall PR-delta improvement was approximately `-0.012317`;
- median NORMAL PR improvement was approximately `-0.001471`;
- median STRESS PR improvement was approximately `-0.028965`;
- STRESS degradation was materially worse and unstable across folds;
- V3-C is closed to rescue, threshold changes, blending, rescaling, or another expert architecture.

This result does **not** imply that regime information is useless. It rejects the tested explicit sample-fragmenting two-expert architecture. The frozen V3-C regime state remains useful as an audit partition for later hypotheses.

## 2. V3-D candidate remains unchanged

No V3-D feature/model hypothesis is changed by this amendment.

Ordinal `008` remains the exact V2 `HGB_XS_MARKET` control.

Ordinal `009` remains one global HGB with exact V2 25 features plus exactly these six PIT sector-relative features:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

No regime state is added as a model feature. No NORMAL/STRESS expert is used. No Structure-Lite feature is added. No score rescaling, blending, calibration, or fallback is allowed.

## 3. Frozen V3-C regime partition used only for evaluation

The V3-D outcome runner must additionally evaluate candidate-minus-control behavior inside the already-frozen V3-C `NORMAL` and `STRESS` partitions.

The authoritative V3-C discovery cache identity is pinned:

- cache SHA-256: `1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8`;
- rows: `216,472`;
- tickers: `674`;
- sessions: `20..984`;
- F5/F6 are absent;
- the regime definition remains prior-252-session, min-126-history, 2-of-3 votes over breadth-20, market median return-20, and market median ATR/close.

The V3-D runner may read from that cache only the outcome-independent routing metadata required to map V3-D validation dates to `NORMAL`/`STRESS`. It must not retrain V3-C, change thresholds, use V3-C model scores, or use V3-C predictions as V3-D features.

## 4. Added regime-stratified diagnostics

For each V2F1-V2F4 validation fold and for each of `NORMAL` and `STRESS`, report candidate-minus-control changes in:

- PR-AUC minus prevalence;
- ROC-AUC;
- Q5-Q1;
- top-decile lift.

Also report:

- rows and dates per fold/state;
- median change by state;
- worst fold/state PR change;
- nonnegative PR fold count by state.

These metrics are computed on the same V3-D prediction rows, merely partitioned by the frozen market-wide regime state.

## 5. Added regime non-degradation guard

V3-D promotion now requires all original V3-D absolute and paired gates **plus** this regime non-degradation guard:

1. NORMAL median paired PR-delta improvement >= `-0.005`;
2. STRESS median paired PR-delta improvement >= `-0.005`;
3. NORMAL median ROC change >= `-0.005`;
4. STRESS median ROC change >= `-0.005`;
5. NORMAL median Q5-Q1 change >= `-0.005`;
6. STRESS median Q5-Q1 change >= `-0.005`;
7. worst paired PR-delta improvement across all fold/state cells >= `-0.015`.

Top-decile lift remains diagnostic only and cannot rescue or kill by itself.

Rationale: V3-D is not hypothesized to improve one specific regime, so positive regime-specific uplift is not required. However a candidate that passes aggregate gates by hiding material damage inside either market state is not considered robust enough to survive.

The thresholds above are frozen before V3-D outcome access. They may not be changed after V3-D metrics are viewed.

## 6. Deterministic V3-D decision after amendment

A V3-D candidate is promoted only if:

- PIT sector/provenance/coverage data gate PASS;
- exact V2 control equivalence PASS;
- original absolute sanity gate PASS;
- original paired promotion gate PASS;
- post-V3-C regime non-degradation guard PASS.

Otherwise the candidate is `KEEP_DIAGNOSTIC` and the deterministic decision remains `V3_D_SECTOR_KILL_KEEP_V2_CONTROL`.

No rescue candidate is permitted.

## 7. Outcome authorization remains locked

This amendment does not authorize V3-D scoring.

Before any V3-D F1-F4 outcome run:

1. full repository pytest must pass on the final amended tree;
2. a real historical PIT sector-history artifact must pass provenance validation;
3. every referenced source hash must be independently evidenced;
4. the outcome-independent V3-D cache must pass the frozen coverage gate;
5. the amended evaluation implementation must be tested;
6. a separate authorization JSON must pin final spec/amendment/code/cache identities.

V2F5/V2F6 and reserved post-2026-07-31 forward outcomes remain prohibited.
