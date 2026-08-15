# Foreign Flow Setup State V1 — Contract

Date: 2026-08-15 (Asia/Jakarta)
Status: `FOREIGN_FLOW_SETUP_STATE_V1_OUTCOME_BLIND_CONTRACT`

## Scientific boundary

Foreign Flow V1 and Foreign Flow V2 Core direct-H10 alpha experiments remain final `NO_SURVIVOR` results. This lane does **not** rescue them. It defines a deterministic descriptive/setup state for prospective use only.

Forbidden in this lane:

- historical alpha reruns or subset search;
- threshold optimization against TP/SL outcomes;
- model fitting;
- protected/fresh-forward outcome access;
- free-float/effective-supply inference;
- a second forward counter.

The previously established PIT supply extension remains a separate lane.

## Core design principle

Do not collapse foreign activity into one `foreign_net / current_volume` number.

The state layer preserves distinct economic axes:

1. **Current participation** — dominance of net foreign activity relative to current regular-market volume.
2. **Own-history abnormality** — how unusual current economic foreign pressure is relative to the ticker's prior behavior.
3. **Cross-sectional pressure** — how strong the ticker is versus the same-session primary-liquid universe.
4. **Persistence / acceleration** — whether pressure is sustained and strengthening or fading.
5. **Flow-price divergence** — whether foreign pressure is strong while price response is comparatively weak.

This intentionally permits a 5% current-participation observation to be more informative than a 50% observation when the former is historically extreme and persistent while the latter is routine for its ticker.

## Accepted V2 inputs reused

The implementation reuses accepted causal Foreign Flow V2 fields without changing their formulas:

- `foreign_participation_1`
- `foreign_flow_shock_percentile_120`
- `xs_rank_foreign_flow_shock_mean_5`
- `xs_rank_foreign_flow_shock_mean_20`
- `foreign_weighted_persistence_5`
- `foreign_weighted_persistence_20`
- `foreign_flow_acceleration_5_20`
- `foreign_flow_price_divergence_5`
- `foreign_flow_price_divergence_20`

The accepted t -> t+1 causality, listing-aware history, current-excluded own-history percentile, and source-session rank scope remain unchanged.

## Coarse outcome-blind bands

These bands are engineering defaults for descriptive state capture, **not optimized alpha thresholds**.

### Current participation intensity

Uses `abs(foreign_participation_1)`:

- `LOW`: `< 5%`
- `NORMAL`: `5% .. <20%`
- `HIGH`: `>= 20%`

Direction is retained separately from magnitude.

### Historical abnormality

Uses signed own-history percentile:

- `EXTREME_DISTRIBUTION`: `<= 5th percentile`
- `DISTRIBUTION`: `>5th .. <=20th`
- `NORMAL`: `>20th .. <80th`
- `ACCUMULATION`: `>=80th .. <95th`
- `EXTREME_ACCUMULATION`: `>=95th`

### Persistence

Uses accepted weighted persistence fields:

- `ACCUMULATION`: 20-session persistence `>= +0.50` and 5-session persistence non-negative;
- `DISTRIBUTION`: 20-session persistence `<= -0.50` and 5-session persistence non-positive;
- otherwise `MIXED`.

### Cross-sectional pressure

Uses the stronger of accepted 5d/20d source-session ranks:

- `LOW`: `<0.50`
- `ELEVATED`: `0.50 .. <0.80`
- `HIGH`: `>=0.80`

### Divergence

A positive flow-price rank gap means foreign pressure is stronger than price response.

- `POSITIVE`: max(5d,20d divergence) `>= +0.20`
- `NEGATIVE`: min(5d,20d divergence) `<= -0.20`
- otherwise `NEUTRAL`

## Composite descriptive setup labels

The classifier may emit:

- `HIGH_PARTICIPATION_ROUTINE_FLOW`
- `ABNORMAL_ACCUMULATION`
- `PERSISTENT_ACCUMULATION`
- `STEALTH_ACCUMULATION_CANDIDATE`
- `DISTRIBUTION_PRESSURE`
- `NEUTRAL_OR_MIXED`
- `INDETERMINATE`

`STEALTH_ACCUMULATION_CANDIDATE` requires abnormal positive own-history flow, persistent accumulation, high cross-sectional pressure, and positive flow-price divergence. It is a **WATCH/SETUP context**, not a BUY signal.

Current participation magnitude is deliberately **not** required for `STEALTH_ACCUMULATION_CANDIDATE`.

## Intended downstream architecture

`Structural Context -> Foreign Accumulation State -> Price State -> Confirmation -> Ranking -> Risk/Execution`

Examples:

- `ACCUMULATION + DOWNTREND -> WATCH`
- `ACCUMULATION + BASING -> READY`
- `ACCUMULATION + CONFIRMED_REVERSAL -> ENTRY_ELIGIBLE`

Price-state and confirmation semantics are out of scope here and must not be tuned from already-observed V1/V2 historical outcomes.

## Missingness / fail-closed

- Do not forward-fill unavailable foreign-flow state.
- Do not convert unavailable rank/divergence fields to neutral.
- Non-finite required inputs emit `INDETERMINATE` with explicit missing fields.
- No inferred effective-float denominator is allowed until PIT supply remediation succeeds.

## Validation rule

Historical data may be used only for semantic/unit/distribution checks. Performance evaluation of this post-V2 state architecture must use genuinely new prospective observations or a separately protected unseen period.

Final contract status:

`FOREIGN_FLOW_DIRECT_H10_ALPHA_CLOSED`

`FOREIGN_FLOW_SETUP_STATE_V1_PROSPECTIVE_ONLY`
