# Ranking V3-C Regime Specification — Independent Review Addendum V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **INDEPENDENT REVIEW PASS — IMPLEMENTATION AUTHORIZED, OUTCOME RUN NOT YET AUTHORIZED IN THIS DOCUMENT**

Reviewed specification:

`docs/RANKING_V3_REGIME_SPEC_V1.md`

Frozen spec Git blob at review:

`2a2f48d68f5d3df839c61191d4a11fa870470b00`

No V3-C outcome, V2F5/V2F6 outcome, or reserved post-2026-07-31 V2 forward outcome was inspected during this review.

## Review conclusion

PASS. The experiment is sufficiently bounded to isolate one architecture hypothesis:

- exact V2 global control;
- one two-state market-wide regime definition;
- one two-expert HGB specialist candidate;
- exact 25 V2 model features for every expert;
- no Structure-Lite inheritance;
- no regime threshold/model/grid search;
- no score calibration/blending/rescaling.

## Clarification A — recompute context outcome-independently

The implementation must build regime thresholds from market context recomputed from the full causal primary-liquid feature frame, not from resolved-label date availability. Use the existing `build_baseline_features` and `build_v2_feature_table` semantics over the hash-pinned signal panel/calendar.

The security-master artifact remains hash-pinned for provenance. Listing-age fields are not regime inputs and V2 time proxies remain excluded.

## Clarification B — official-session history

The 252-session threshold window is indexed in the certified official calendar. Missing ticker observations do not compress time. Regime context is market-wide and must have at most one deterministic row per official date.

Quantile thresholds for session `t` use only sessions before `t`; current market context can vote against those frozen prior thresholds because the signal is produced after close.

## Clarification C — specialist score semantics

Do not align, z-score, percentile-normalize, calibrate, or blend NORMAL and STRESS expert scores. Route the exact raw V2 logit score from the applicable expert. Any scale incompatibility between experts is part of the tested architecture and must be reflected in the result.

## Clarification D — coverage gate precedes specialist outcome access

The prepare stage may calculate regime counts/dates/threshold diagnostics because those are outcome-independent. It must not compute target-performance metrics.

If the frozen training/validation fragmentation gate fails for any F1-F4 fold, the specialist outcome run is blocked and the regime definition is not adjusted under this hypothesis.

## Clarification E — discovery evidence only

V2F1-F4 remain the only V3-C outcome-bearing discovery folds. V2F5/F6 remain physically excluded from the V3-C discovery model cache and reserved for the final frozen V3 architecture. Reserved fresh-forward V2 outcomes remain off-limits.

## Unchanged frozen gates

Promotion requires:

1. absolute sanity PASS;
2. overall paired promotion PASS;
3. regime-specific robustness PASS, including meaningful STRESS benefit and bounded NORMAL degradation.

Top-decile behavior remains diagnostic and cannot rescue a failed primary gate.

## Implementation authorization

Implementation of the outcome-independent regime builder, F1-F4-only cache preparation, exact control-equivalence runner, specialist routing, regime-specific metrics, guardrail tests, artifact hashing, and run handoff is authorized.

Implementation must stop before locally viewing V3-C outcome metrics. A separate local run handoff may authorize Codex to execute the frozen runner after full pytest and artifact verification.