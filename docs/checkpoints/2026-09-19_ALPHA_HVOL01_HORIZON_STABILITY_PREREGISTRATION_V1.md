# H-VOL-01 Horizon Stability — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `F_STRUCTURAL_ROBUSTNESS / J_MULTI_HORIZON`

## Question

Is the H-VOL-01 compression mechanism structurally stable across a small set
of economically distinct short/long state horizons, or is the observed
5-session versus 60-session result a narrow representation artifact?

## Fixed representations

Evaluate exactly these three forms on the same guarded official-session grid:

1. `5/20`: `-log(median_5(range_pct) / median_20(range_pct))`;
2. `5/60`: `-log(median_5(range_pct) / median_60(range_pct))`, the existing
   preregistered H-VOL-01 baseline;
3. `20/120`: `-log(median_20(range_pct) / median_120(range_pct))`.

Here `range_pct=(high-low)/close`, with positive finite high/low/close and
`high>=low`. No other windows, signs, thresholds, normalization, or weights
are allowed in this audit.

## Structural checks

For each fixed form record support, score distribution, Top-30 turnover,
selected value/turnover quartiles, overlap and daily rank dependence versus
C1/C2/C4/H-LIQ-01, and pairwise overlap between the three H-VOL forms.

The result is descriptive. No horizon is selected as “best”; no outcome,
target, forward return, IC/ICIR, incumbent score, or candidate ID is allowed.
The existing 5/60 result must reproduce its recorded structural support and
Top-30 turnover within deterministic equality.

## Decision rule

Stable support and broadly similar portfolio geometry strengthen the mechanism
as a representation family. Large support, turnover, composition, or overlap
changes make horizon dependence an explicit risk. Either result leaves H-VOL
outside the protected four-ID packet and does not create C5.

## Inputs and boundary

Use only the already admitted frozen panel, guarded feature eligibility,
official sessions, anchors, manifest, and prior H-VOL output. Write only the
derived JSON to the isolated staging root. Stop on hash, key, eligibility, or
baseline-reproduction mismatch.
