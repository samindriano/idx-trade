# H-EXC-02 Bounded Previous-Close Excursion Balance — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `I_REPRESENTATION_SEARCH / E_NEW_HYPOTHESIS`

## Relationship to H-EXC-01

H-EXC-01's exact raw form is permanently preserved as
`STRUCTURALLY_REJECTED_AS_WRITTEN` because its signed denominator can create
unbounded score tails. This document does not alter or rescue that result. It
defines a new bounded hypothesis contract for the broader previous-close
excursion-balance mechanism.

## Fixed representation

For each ticker/session:

`bounded_daily_balance = (abs(high-prev_close) - abs(low-prev_close)) /
(abs(high-prev_close) + abs(low-prev_close))`

when high, low, and previous close are positive finite and the denominator is
positive. The score is exactly:

`H_EXC_02_bounded_excursion_balance_5_v1 = median_5(bounded_daily_balance)`.

The absolute distances make the daily term bounded in `[-1, 1]` even when a
session gaps outside the previous close. No clipping, denominator floor,
winsorisation, sign flip, threshold, volume interaction, horizon sweep, or
target-conditioned selection is allowed.

## Structural checks

Record finite support, bounded score distribution, Top-30 turnover, selected
value and dollar-turnover quartiles, Top-30 overlap, and daily rank dependence
versus C1/C2/C4, H-LIQ-01, and H-VOL-01 5/60. This is target-free evidence;
no candidate ID or protected-packet entry is created.

## Decision rule

The test can establish whether the broader excursion-balance mechanism has a
numerically stable structural representation. It cannot establish predictive
value, PIT/CA admission, or superiority. A result that is bounded but highly
churned/concentrated remains future research only.

## Boundary

Use only the frozen panel, guarded eligibility, official sessions, anchors,
manifest, and existing H-VOL structural output. Write only the derived JSON
to isolated staging. Do not modify H-EXC-01 artifacts or access targets,
forward returns, providers, cloud, capture, telemetry, or canonical data.
