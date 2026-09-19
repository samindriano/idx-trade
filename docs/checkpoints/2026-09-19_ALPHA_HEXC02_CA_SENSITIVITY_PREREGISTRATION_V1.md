# H-EXC-02 Corporate-Action Sensitivity — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `B_J_HEXC02_CORPORATE_ACTION_UNRESOLVED_SENSITIVITY`

## Question

Does the fixed H-EXC-02 bounded excursion-balance representation change when
the retained `idx_close` comparison values are substituted for the same 188
unresolved non-stable-scale rows used by the existing forensic lane?

This is a sensitivity audit, not a price-basis correction or admission.

## Fixed construction

The score remains exactly:

`median_5((abs(high-prev_close)-abs(low-prev_close)) /
(abs(high-prev_close)+abs(low-prev_close)))`

Only `close` is replaced in memory at the 188 retained comparison keys. The
high, low, volume, universe, official sessions, anchors, eligibility, window,
aggregation, and direction remain unchanged. Because `close` supplies the
previous-close chain, downstream rows may change through the ordinary causal
shift; these are reported as spillover, not causal labels.

## Required evidence

Record baseline/counterfactual support, changed score rows, changed ranks,
direct-versus-spillover attribution, changed Top-30 dates, mean/minimum Top-30
overlap, and changed Top-30 slots. Do not tune, clip, refit, or select a
variant after observing the result.

## Decision boundary

The result may narrow H-EXC-02 price-basis risk but cannot establish PIT,
corporate-action completeness, issuer continuity, predictive value, or
candidate readiness. No C5 ID or protected-packet entry may be created.

## Safety

Use the frozen panel, guarded eligibility, official sessions, anchors, manifest,
the retained unresolved-scale artifact, and the existing H-EXC-02 structural
output only. The substitution is in-memory only. Do not access targets,
forward outcomes, incumbent predictions, providers, cloud, capture, telemetry,
or canonical data, and do not modify H-EXC-01 or the protected packet.

