# Handoff — IDX Ranking V3-B Structure-Lite Specification

Date: 2026-08-10 (Asia/Jakarta)
Status: **AUTHORIZED FOR SPECIFICATION / DEFINITION AUDIT ONLY — NO V3-B OUTCOME RUN**

## Required reads

Before changing anything, read and explicitly acknowledge:

1. `docs/CURRENT_STATUS.md`
2. `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_REVIEW_PASS.md`
3. `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_F1_F4_RESULT.md`
4. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
5. `docs/RANKING_V3_RESEARCH_BACKLOG.md`
6. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
7. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
8. frozen V2 feature/model/validation specifications and code
9. relevant legacy support/resistance code in `samindriano/past-models-indo-stock`, especially the causal geometry layer; do not import its outcome-conditioned decision/scoring layer.

## Objective

Draft and freeze `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md` only.

The single hypothesis is:

> Does a compact, causal representation of support/resistance and price-structure geometry add robust same-date ranking information beyond the exact frozen V2 `HGB_XS_MARKET` 25-feature representation?

This task is definition/specification work only. Do not fit or score a V3-B model.

## Design principles

### Exact control

The comparator remains exact uniform V2 `HGB_XS_MARKET`:

- exact H10 target;
- exact causal universe;
- exact existing 25 V2 features;
- exact preprocessing/HGB parameters;
- exact score/metric semantics;
- uniform training weights; V3-A recency is closed and must not be inherited.

### Structure candidate budget

Prefer:

- one exact V2 control; and
- **one fixed Structure-Lite candidate bundle**.

A second structure variant is allowed only if the specification can justify it before outcomes as a single distinct sub-hypothesis rather than a feature-search mechanism. Never exceed two structure variants.

### Compact feature budget

The final structure bundle should normally contain no more than roughly 6-8 new numeric/boolean features. The exact count and definitions must be frozen by the spec.

The feature family may draw from:

- prior support/resistance touch density or touch count;
- level age/recency;
- role-reversal evidence;
- breakout/retest state;
- volume confirmation associated with a causal breakout/retest;
- compression / range-contraction geometry.

Do not add RSI/MACD/Bollinger/stochastic/CCI/MFI/large indicator libraries. V2 already contains momentum, ATR, recent-high/low distance, range position, relative volume, liquidity and market-context information.

### Avoid duplicate information

Before freezing each new feature, map it against the existing 25 V2 features and explain what incremental geometry it represents. Features that are effectively deterministic restatements of V2 20/60 high-low distance or range position should be excluded unless the spec documents a materially different causal concept.

## Point-in-time / causal requirements

Every signal feature for session `t` must use information available at or before the close of `t` only.

The spec must define precisely:

- pivot/extrema detection rule, if used;
- lookback windows;
- whether the current signal bar may contribute to level formation and, if so, how breakout semantics avoid self-reference;
- level clustering/tolerance formula in price/ATR terms;
- support versus resistance classification;
- touch definition and minimum separation between touches;
- level age definition;
- role-reversal definition;
- breakout/retest definition;
- volume-confirmation definition;
- missing/no-level behavior;
- tie handling and deterministic sorting;
- numerical edge cases and fail-closed behavior.

Do not use future confirmation bars to define a structure feature at `t`.

## Legacy-code boundary

The legacy support/resistance project is inspiration only.

Safe to inspect/reformulate:

- pivot/window extrema;
- level clustering;
- historical touch counts;
- level recency;
- role reversal;
- causal distance/geometry;
- breakout/retest state using only information through `t`.

Prohibited to port:

- historical routed-test outcome lookups;
- `actual_up`, realized-return or backtest buckets;
- ticker/setup-specific empirical overlays;
- adaptive horizon weights based on realized historical subsets;
- hand-tuned current investment-score bonuses derived from viewed outcomes;
- any rule chosen because the legacy backtest showed it worked.

## Data architecture requirement

The current immutable V2 prepared cache contains derived V2 model features but may not contain enough raw trailing geometry to construct Structure-Lite correctly.

The spec must explicitly decide the source architecture before outcomes:

1. derive Structure-Lite from the frozen underlying signal-research panel / baseline feature pipeline with exact source hashes; or
2. build a new immutable V3-B prepared cache that joins exact V2 eligible rows to causal Structure-Lite features by ticker/date.

Do not silently overwrite or expand the frozen V2 prepared cache.

Any new V3-B cache must:

- preserve exact V2 row identity/label/universe eligibility for the experiment;
- pin source panel/calendar/security/provenance hashes;
- prove exact V2 25-feature equivalence on joined rows;
- record coverage/missingness for each new structure feature;
- fail closed on duplicate/misaligned ticker-date rows.

## Development folds and sealed evidence

The eventual Structure-Lite discovery run must use **V2F1-V2F4 only** for comparability with V3-A.

V2F5/V2F6 remain sealed for the future final-V3 architecture and must not be loaded/scored/summarized during Structure-Lite discovery.

Reserved post-2026-07-31 V2 forward outcomes remain off-limits.

## Evaluation/gate design

The spec must freeze before any V3-B score:

- exact candidate set;
- feature bundle/order;
- feature definitions and source/cache identity;
- F1-F4 fold boundaries;
- exact V2 control-equivalence gate;
- same ranking metrics used by V3-A/V2;
- absolute sanity gate;
- paired promotion gate versus exact V2 control;
- q25/worst-fold/late-discovery diagnostics;
- top-decile and Q5-Q1 diagnostics;
- coverage/missing-feature diagnostics;
- deterministic tie/simplicity rule;
- hypothesis-ledger ordinals and cumulative candidate denominator.

The paired promotion rule should require a material robustness improvement, not just a tiny positive median metric. Do not choose thresholds after viewing V3-B scores.

## Testing requirements to specify

The future implementation must include adversarial tests for at least:

- no future-bar dependence;
- no accidental look-ahead in pivot confirmation;
- current-bar breakout semantics;
- split/adjustment/raw-price semantics compatible with existing research contracts;
- deterministic level clustering/ties;
- no-level and single-level cases;
- repeated touches on adjacent sessions not artificially inflating touch count;
- role reversal only after causally observable crossing/retest sequence;
- V2 row/feature equivalence after any V3-B join/cache build;
- F5/F6 hard block;
- provenance/hash mismatch fail closed.

## Deliverables

1. `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`
2. dated spec checkpoint
3. result handoff summarizing exact frozen definitions/feature bundle/cache plan/gates
4. update the hypothesis ledger with preregistered V3-B slots but no fabricated results
5. update continuity docs so the new spec is discoverable

Stop after specification work and return for ChatGPT review.

## Hard prohibitions

Do not:

- fit or score Structure-Lite in this task;
- reopen or rescue V3-A recency;
- score/load V2F5/V2F6;
- inspect reserved V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- add broad technical-indicator/model/threshold searches;
- start V3-C regime, V3-D sector, V3-E ranking, integration, calibration, Stage 6, IDX-VAL-002, execution-PnL, paper/live, or main merge.
