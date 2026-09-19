# CA Unresolved-Row Exposure Attribution — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PREREGISTERED / FORENSIC / OUTCOME-BLIND`

## Question

When the 188 unresolved non-stable scale rows are substituted with their
retained `idx_close` comparison values in memory, how much candidate impact is
on the unresolved row itself versus spillover to other ticker/date rows?

This distinguishes direct rolling-window exposure from cross-sectional or
market-relative propagation. It does not decide which comparison value is
correct and does not authorize a refit.

## Fixed classification

- `direct_row`: changed score/rank row has the same `(ticker,date)` key as one
  of the 188 unresolved rows.
- `spillover_row`: changed score/rank row does not have an unresolved key.
  This is an attribution label, not proof of a specific causal path; C1's
  market-relative and prior-beta calculations can propagate one price change
  broadly.

For each C1/C2/C4 (and retained H-LIQ diagnostic), report finite comparison,
score-change, rank-change, and Top-30 set-change counts by class, plus mean/max
absolute score change and Top-30 overlap.

## Interpretation rules

- A spillover-dominant C1 result strengthens the warning that C1 is sensitive to
  cross-sectional market/beta propagation, not merely its own rolling window.
- A direct-dominant C2/C4 result is a bounded window-exposure description, not
  a price-basis correction.
- No result can establish same-basis correctness, PIT admission, or predictive
  value.

## Prohibited actions

No target/outcome/incumbent/provider/network/cloud/capture/scheduler access; no
panel mutation, clean refit, correction promotion, candidate status upgrade,
or C5 creation.

