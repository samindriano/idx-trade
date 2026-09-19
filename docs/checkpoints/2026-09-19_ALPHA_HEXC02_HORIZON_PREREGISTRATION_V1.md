# H-EXC-02 Horizon Stability — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `J_HEXC02_FIXED_HORIZON_STABILITY`

## Question

Is the bounded H-EXC-02 excursion-balance mechanism structurally stable beyond
the current five-session representation, or is its high turnover specific to a
short horizon?

## Fixed horizon set

Evaluate exactly the three rolling-median windows `{5, 20, 60}` sessions on the
same daily bounded term:

`(abs(high-prev_close)-abs(low-prev_close)) /
(abs(high-prev_close)+abs(low-prev_close))`

No additional horizons, combinations, threshold search, direction flip,
clipping, winsorisation, or outcome-conditioned selection is permitted. The
existing 5-session form is the baseline and must reproduce its stored support
and Top-30 turnover exactly.

## Structural checks

For each horizon record finite support, score distribution, Top-30 turnover,
selected value and dollar-turnover quartiles, overlap with C1/C2/C4, and
pairwise Top-30 overlap among the three H-EXC-02 horizons. This is a
representation-stability audit, not hyperparameter optimization.

## Decision boundary

The result can identify a stable or fragile representation and inform future
freezing. It cannot establish predictive value, PIT/CA admission, capacity,
or superiority. No C5 ID or protected-packet entry may be created.

## Safety

Use only the frozen panel, guarded feature eligibility, official sessions,
anchors, manifest, and existing H-EXC-02 structural output. Keep output in the
isolated staging root. Do not access targets, outcomes, incumbent predictions,
providers, cloud, capture, telemetry, or canonical data.

