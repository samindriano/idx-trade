# H-EXC-02 Corporate-Action Sensitivity — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PASS_STRUCTURAL_ONLY / PARTIAL FORENSIC EVIDENCE`  
Candidate: none; no C5 created.

## Question and boundary

This audit tested whether the fixed H-EXC-02 bounded excursion-balance state
changes when the retained `idx_close` comparison values are substituted for the
188 unresolved non-stable-scale rows. The substitution was in-memory only.
The comparison values are not admitted corrections and do not certify PIT,
corporate-action completeness, issuer continuity, or predictive value.

No target, forward return, incumbent score, provider, network, cloud, capture,
telemetry, canonical dataset, refit, model artifact, H-EXC-01 artifact, or
protected packet was accessed or changed.

## Fixed construction

The score remained exactly:

`median_5((abs(high-prev_close)-abs(low-prev_close)) /
(abs(high-prev_close)+abs(low-prev_close)))`

Only `close` was replaced for the 188 retained comparison keys; high, low,
volume, universe, windows, direction, aggregation, and eligibility were
unchanged. Since `close` supplies the previous-close chain, downstream changes
are expected and are reported as spillover, not causal labels.

## Result

| Metric | Result |
|---|---:|
| Unresolved rows / tickers | `188 / 19` |
| Baseline / counterfactual finite support | `308,067 / 308,067` |
| Score-changed rows | `155` (`33` direct / `122` spillover) |
| Rank-changed rows | `3,977` (`36` direct / `3,941` spillover) |
| Top-30 common / changed dates | `1,201 / 8` |
| Mean / minimum Top-30 overlap | `99.9722% / 93.3333%` |
| Changed Top-30 slots, direct / spillover | `1 / 19` |
| Maximum absolute score change | `0.99147` |

The direct classification means the changed `(ticker,date)` key is present in
the unresolved artifact. Spillover means the changed key is absent from it; it
does not label causality. Among `66` finite direct rows, `33` changed score and
`36` changed rank. Among `308,001` finite spillover rows, `122` changed score
and `3,941` changed rank.

## Interpretation

At the Top-30 portfolio level, this specific 188-row counterfactual leaves
H-EXC-02 highly stable (`99.9722%` mean and `93.3333%` minimum overlap), and
support is unchanged. That narrows—but does not clear—the price-basis risk:
the counterfactual still changes direct rows, produces rank spillover, and has
a material maximum score delta. Global PIT/CA/identity authority remains
`UNKNOWN`.

The earlier H-EXC-02 structural result still governs the economics: mean
Top-30 turnover is `40.7750%` and maximum is `86.6667%`. Therefore the overall
disposition remains:

`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`

No C5 ID was created, no protected evaluation packet changed, and no clean
refit is authorized.

## Provenance and hashes

- Preregistration: `2026-09-19_ALPHA_HEXC02_CA_SENSITIVITY_PREREGISTRATION_V1.md`
- Code: `research/alpha_hex02_ca_sensitivity_v1.py`
- Code SHA-256: `eb5845e708b832a7ba84337af2ab88fda184f412feb03ffab8df8708a8e93daf`
- Output: external staged `alpha_hex02_ca_sensitivity_v1.json`
- Output SHA-256: `74dd84ab756545c1647c94901491f7b8a471df07c97f8eb1045702557daeba74`
- H-EXC-02 structural output SHA-256: `27ed30b6a7d4c2d19260b4ffd1a7cc2772824e3e28ce0087f027f59d80b5d629`
- Repository head used: `ab6ff567`
- Unresolved-scale source SHA-256: `eaedba187a3645a83c06c3885dac2c819e818fb68636cfedf2d32e7792432743`
- Manifest SHA-256: `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`

The JSON is staged at
`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hex02_ca_sensitivity_v1.json`.

