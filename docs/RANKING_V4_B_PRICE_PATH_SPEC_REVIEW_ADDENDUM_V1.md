# Ranking V4-B Price-Path Quality — Spec Review Addendum V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **PRE-OUTCOME REVIEW PASS — IMPLEMENTATION AUTHORIZED / OUTCOME SCORING NOT AUTHORIZED**

## Review decision

`V4_B_PRICE_PATH_SPEC_REVIEW_PASS`

The frozen V4-B specification is sufficiently compact, causal and distinct from the exact V3-B 33-feature benchmark to proceed to implementation and outcome-blind cache audit.

Controlling spec Git blob:

`a750c28831b95b1c88640c5879289da5f2c05446`

## Overlap review against V3-B

V3-B already contains:

- cross-sectional ranks of 5/20 close return;
- ATR14/close;
- current close position inside the aggregate 20-session high-low range;
- distances to 20/60-session highs/lows;
- volume/value activity;
- market context and stock-minus-market state;
- eight causal Structure-Lite geometry features.

### B1

`v4b_path_efficiency_5`, `v4b_path_efficiency_20` and `v4b_largest_move_share_20` do not re-encode return magnitude directly. They condition on the sequence of adjacent daily log returns and measure gross-path efficiency / concentration. Conceptual overlap with existing return and ATR features is **moderate but not duplicative**.

The review rejects adding skew, kurtosis, slope, R2, residual volatility, MAX/MIN return and extra lookback variants because those would turn the same path information into a feature tournament.

### B2

Daily `clv_t` measures the close inside each individual session's own high-low range. This differs mechanically from `close_position_20`, which places today's close inside the aggregate 20-session high-low range. The 5/20 acceptance means and five-session extreme-close balance therefore represent a distinct repeated-acceptance/rejection path question.

The review rejects separate wick, candlestick-pattern and structure-conditioned interaction candidates.

## Causality / missingness review

- only High/Low/Close and official-session identity are needed;
- historical Open is not required;
- no label/outcome/future column is allowed into feature construction;
- exact B1 paths fail closed if any required official-session row is missing;
- B2 exact five-session quantities fail closed on a missing/zero-range daily bar;
- B2 20-session mean requires at least 10 valid daily close-location values and never substitutes zero for missing rows;
- session `1225+` remains prohibited.

## Candidate-budget review

First pass is frozen to exactly three slots:

- ordinal `015` exact V3-B control;
- ordinal `016` B1 Path Coherence / Jump Concentration;
- ordinal `017` B2 Range Acceptance / Rejection.

No integration slot exists yet. B1 and B2 must be fully implemented before either outcome is viewed.

## Gate review

The V4-A challenger gate is reused **unchanged**. This is preferable to selecting a new threshold after observing V4-A outcomes and materially reduces adaptive research flexibility.

## Runtime implementation note

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` was read before implementation authorization. Relevant rules for V4-B are:

- profile rather than assume bottlenecks;
- preserve deterministic semantics;
- project only required columns for outcome-blind audits where useful;
- do not introduce uncontrolled candidate/fold parallelism merely to reduce runtime;
- require exact frozen-control equivalence before challenger interpretation.

The latest V4-A run shows model fitting is already small enough for a bounded deterministic first pass; no model-runtime optimization is required before V4-B implementation.

## Implementation authorization

Authorized now:

- causal B1/B2 feature builder;
- frozen candidate/model definitions;
- outcome-independent cache preparation on exact frozen V3-B rows;
- outcome-blind distribution/coverage/redundancy audit;
- atomic first-pass runner implementation and tests, **but not execution**.

Not authorized:

- V4-B outcome scoring;
- formula/lookback rescue based on later audit correlations unless there is a mechanical mismatch with the frozen mathematics;
- B1+B2 integration;
- session `1225+` or fresh-forward access;
- any later V4 family automatically.