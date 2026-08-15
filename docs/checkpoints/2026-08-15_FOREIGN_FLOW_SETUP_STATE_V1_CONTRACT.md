# Foreign Flow Setup State V1 — Contract

Status: `DRAFT_OUTCOME_BLIND_PROSPECTIVE_ONLY`

This lane defines a causal, descriptive Foreign Flow setup/state layer. It does not authorize historical alpha rescue, model fitting, protected outcome access, or a new forward counter.

## Scientific boundary

- Foreign Flow V1 and Foreign Flow V2 Core direct-H10 alpha experiments remain final `NO_SURVIVOR` results.
- This contract must not use V2 fold-specific performance, feature importance, alternate windows, or threshold search.
- The state layer is intended for prospective capture and discretionary-style decision context.
- The previously established PIT supply extension remains a separate lane and is not implemented here.

## Core design principle

Do not collapse foreign activity into a single `foreign_net / current_volume` number.

The setup state keeps distinct axes because they answer different questions:

1. **Current participation** — how dominant foreign net activity is relative to current regular-market volume.
2. **Historical abnormality** — how unusual the economic foreign flow is relative to the ticker's own prior activity baseline.
3. **Own-history percentile** — where the current abnormality sits versus the ticker's prior distribution.
4. **Cross-sectional pressure** — how strong the ticker's foreign pressure is versus other primary-liquid names on the same source session.
5. **Persistence / acceleration** — whether the pressure is sustained and strengthening or fading.
6. **Flow-price divergence** — whether foreign pressure is strong while price response remains comparatively weak.

A high current participation ratio is not automatically a strong accumulation signal. A low participation ratio is not automatically weak if the absolute/economic flow is extreme relative to the ticker's own historical baseline.

## Reuse of accepted V2 representation

This contract reuses the accepted causal Foreign Flow V2 representation semantics rather than inventing new retrospective formulas.

Primary inputs:

- `foreign_participation_1`
- `foreign_flow_shock_percentile_120`
- `xs_rank_foreign_flow_shock_1`
- `xs_rank_foreign_flow_shock_mean_5`
- `xs_rank_foreign_flow_shock_mean_20`
- `foreign_weighted_persistence_5`
- `foreign_weighted_persistence_20`
- `foreign_flow_acceleration_5_20`
- `foreign_flow_price_divergence_5`
- `foreign_flow_price_divergence_20`

The accepted t -> t+1 causality, listing-aware history, current-excluded own-history percentile, and source-session cross-sectional scope remain unchanged.

## State axes

### Participation state

Outcome-blind descriptive categorization only. V1 does not optimize thresholds against historical outcomes.

- `LOW`
- `NORMAL`
- `HIGH`

Thresholds must be fixed from economically interpretable distribution bands or percentile bands before any prospective outcome evaluation.

### Historical abnormality state

Based primarily on `foreign_flow_shock_percentile_120` and supported by the shock/rank context.

- `NORMAL`
- `ELEVATED`
- `EXTREME`

This axis is intentionally independent of current participation.

### Persistence state

- `DISTRIBUTION`
- `MIXED`
- `ACCUMULATION`

Derived from accepted persistence/acceleration fields only after outcome-blind threshold freeze.

### Price-response relationship

Foreign flow state should not itself decide entry. The flow layer only describes whether price is responding proportionally to foreign pressure.

Candidate descriptive labels:

- `CONFIRMED_RESPONSE`
- `ABSORBED_OR_SIDEWAYS`
- `NEGATIVE_DIVERGENCE`

Exact state semantics must be based on causal price-state inputs and frozen prospectively.

## Composite descriptive labels

These are human-readable setup labels, not alpha predictions:

- `HIGH_PARTICIPATION_LOW_ABNORMALITY`
- `ABNORMAL_ACCUMULATION`
- `PERSISTENT_ACCUMULATION`
- `STEALTH_ACCUMULATION_CANDIDATE`
- `DISTRIBUTION_PRESSURE`
- `INDETERMINATE`

`STEALTH_ACCUMULATION_CANDIDATE` is conceptually reserved for abnormal/persistent positive foreign pressure with relatively muted price response. It must not imply a BUY signal.

## Intended downstream architecture

`Structural Context -> Foreign Accumulation State -> Price State -> Confirmation -> Ranking -> Risk/Execution`

Examples:

- `ACCUMULATION + DOWNTREND -> WATCH`
- `ACCUMULATION + BASING -> READY`
- `ACCUMULATION + CONFIRMED_REVERSAL -> ENTRY_ELIGIBLE`

The price/confirmation layer is not defined in this contract and must not be tuned from the already-observed Foreign Flow V1/V2 historical folds.

## Missingness and fail-closed behavior

- Preserve missing/applicability semantics from the accepted V2 representation.
- Never forward-fill missing foreign-flow state.
- Do not turn unavailable cross-sectional ranks into neutral values.
- If required axes are unavailable, emit `INDETERMINATE` plus explicit missing reasons.
- No inferred free-float denominator is allowed until PIT supply source remediation succeeds.

## Prospective-only evaluation boundary

The first evaluation of the state-machine/confirmation architecture must use genuinely new prospective observations or a separately protected unseen period. The already-used six historical folds may be used only for non-outcome data-quality checks, not for threshold optimization or performance selection.

## Immediate implementation scope

Allowed:

- schema/enums for the state axes;
- deterministic outcome-blind state classifier driven by frozen/configured thresholds;
- explicit provenance and missingness fields;
- unit tests for semantic separation between participation and historical abnormality;
- tests showing that a 50% participation observation can rank lower in abnormality than a 5% participation observation when own-history context differs;
- prospective sidecar wiring design.

Forbidden:

- historical alpha rerun;
- feature subset search;
- threshold optimization against TP/SL labels;
- protected/fresh-forward outcome access;
- free-float/effective-supply inference;
- model fitting;
- second forward counter.

## Status

`FOREIGN_FLOW_SETUP_STATE_V1_CONTRACT_DRAFTED`
