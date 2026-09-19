# H-EXC-02 Bounded Previous-Close Excursion Balance — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `I_E_HEXC02_OUTCOME_BLIND_BOUNDED_EXCURSION_DIAGNOSTIC`  
Status: `PASS_STRUCTURAL_ONLY`

## Scope and boundary

This is one fixed, preregistered structural diagnostic. It does not modify
H-EXC-01, create a candidate ID, read targets or forward outcomes, access a
provider, or change the protected C1-C4 packet. The output was written only to
the isolated external staging root.

H-EXC-01 remains permanently closed as
`STRUCTURALLY_REJECTED_AS_WRITTEN`; H-EXC-02 is a new bounded contract for the
broader excursion-balance mechanism, not a rescue of the old formula.

## Fixed representation

`bounded_daily_balance = (abs(high-prev_close) - abs(low-prev_close)) /
(abs(high-prev_close) + abs(low-prev_close))`

`H_EXC_02_bounded_excursion_balance_5_v1 = median_5(bounded_daily_balance)`

The daily term and the rolling median are bounded in `[-1, 1]`. No clipping,
denominator floor, winsorisation, sign flip, threshold, volume interaction,
horizon sweep, or target-conditioned selection was used.

## Structural result

| Metric | Result |
|---|---:|
| Finite eligible rows | `308,067` |
| Finite eligible dates | `1,201` |
| Finite eligible tickers | `711` |
| Score min / max | `-1.0000 / 1.0000` |
| Mean / median Top-30 turnover | `40.7750% / 40.0000%` |
| Q95 / maximum Top-30 turnover | `56.6667% / 86.6667%` |
| Selected value quartile shares Q1/Q2/Q3/Q4 | `18.0711% / 22.2731% / 26.0949% / 33.5609%` |
| Selected dollar-turnover quartile shares Q1/Q2/Q3/Q4 | `18.0877% / 22.2676% / 26.0783% / 33.5665%` |

The numerical bound is clean, but turnover remains high. The Q4 share is
elevated for both value and dollar-turnover, so the result does not establish
capacity or executable economics.

## Structural distinctness

Mean Top-30 overlap with existing diagnostics was:

| Comparison | Mean overlap | Minimum overlap |
|---|---:|---:|
| C1 | `1.3380%` | `0.0000%` |
| C2 | `25.8562%` | `0.0000%` |
| C4 | `4.9431%` | `0.0000%` |
| H-LIQ-01 | `14.7849%` | `0.0000%` |
| H-VOL-01 5/60 | `11.4543%` | `0.0000%` |

Mean daily Spearman dependence was `-0.4961` versus C1, `+0.1247` versus C2,
`-0.2442` versus C4, `+0.0838` versus H-LIQ-01, and `-0.0402` versus H-VOL-01.
These are structural rank diagnostics only; they are not predictive evidence
or proof of incremental alpha.

## Decision

The bounded representation passes the numerical-stability check and is
structurally distinct, but its turnover and unresolved PIT, corporate-action,
identity, and capacity risks prevent any promotion. Disposition:

`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`

No C5 ID was created. The protected candidate budget remains exactly C1-C4.
H-EXC-01 must not be retried in its raw signed-denominator form; H-EXC-02 must
not be interpreted as a predictive or OOS result.

## Reproducibility and hashes

- Code: `research/alpha_hex02_bounded_excursion_balance_diagnostic_v1.py`
- Code SHA-256: `df72b71a1d2a11ec5c2f83c463d5a078ea5da46b0cf3f6302c7610190a217a77`
- Output: `alpha_hex02_bounded_excursion_balance_diagnostic_v1.json`
- Output SHA-256: `27ed30b6a7d4c2d19260b4ffd1a7cc2772824e3e28ce0087f027f59d80b5d629`
- H-VOL-01 prerequisite output SHA-256: `7fe2f266c2ee5a8cdffe59bbb006ae491351704423e1db4458b01b41a9fa4f7b`
- Manifest SHA-256: `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`
- Repository head supplied to the run: `80773b28`

The JSON is staged at
`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hex02_bounded_excursion_balance_diagnostic_v1.json`.

