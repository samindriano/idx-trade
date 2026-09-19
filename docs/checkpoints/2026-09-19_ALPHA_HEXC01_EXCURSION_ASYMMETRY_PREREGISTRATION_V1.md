# H-EXC-01 Previous-Close Excursion Asymmetry — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `E_NEW_HYPOTHESIS / F_STRUCTURAL_DIAGNOSTIC`

## Mechanism

Intraday high/low excursions around the previous completed close may reveal
one-sided rejection or pressure that is not represented by close-to-close
return alone. A persistent positive value means the high-side excursion from
the previous close dominates the low-side excursion; a negative value means
the opposite.

This is deliberately different from the prior `effort_close_location` family:
it uses previous-close excursion geometry and no current Open, no volume, and
no failed-breakout threshold.

## Fixed representation

For each ticker/session on the official-session grid:

`daily_excursion_asym = ((high-prev_close) - (prev_close-low)) /
((high-prev_close) + (prev_close-low))`

where high, low, and previous close are positive finite values, `high>=low`,
and the denominator is positive. The fixed score is:

`H_EXC_01_excursion_asymmetry_5_v1 = median_5(daily_excursion_asym)`.

Higher score means greater upside-excursion dominance. One horizon, one
aggregation, one direction; no sign flip, threshold, volume interaction,
normalization, parameter sweep, or target-conditioned selection.

## Structural checks

Record finite support, score distribution, Top-30 turnover, selected value and
dollar-turnover quartiles, Top-30 overlap and daily rank dependence versus
C1/C2/C4, H-LIQ-01, and the fixed H-VOL-01 5/60 baseline. This is a
target-free diagnostic only; no candidate ID is created.

## Expected information gain and failure modes

The result will test whether previous-close excursion geometry is structurally
distinct from existing reversal, participation, path-efficiency, liquidity,
and range-compression representations. Main risks are corporate-action basis,
zero/suspension bars, cross-sectional concentration, and redundancy with prior
price-path/rejection experiments. Low overlap is not predictive orthogonality.

## Boundary

Use only the frozen clean panel, guarded universe/feature eligibility, official
sessions, anchors, and manifest. Write only the derived JSON to the isolated
staging root. Do not open targets, forward returns, incumbent score artifacts,
providers, cloud/capture/telemetry, or canonical data. Do not create C5.
