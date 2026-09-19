# H-EXC-02 Horizon Stability — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PASS_STRUCTURAL_ONLY / HORIZON_DEPENDENT`  
Candidate: none; no C5 created.

## Question and boundary

This audit evaluated exactly the preregistered rolling-median windows `5`,
`20`, and `60` sessions for the same bounded previous-close excursion term. It
was a structural representation-stability audit, not outcome-based parameter
selection. No target, forward outcome, incumbent prediction, provider, cloud,
capture, telemetry, canonical data, or protected packet was accessed or
changed.

## Fixed term

`daily_balance = (abs(high-prev_close)-abs(low-prev_close)) /
(abs(high-prev_close)+abs(low-prev_close))`

Each variant is `median_window(daily_balance)` with the window fixed to `5`,
`20`, or `60` sessions. No other horizon, clipping, threshold, direction flip,
or post-result rescue was used.

## Variant results

| Window | Finite rows | Finite dates / tickers | Mean / median turnover | Q95 / max turnover | Value Q1 / Q4 |
|---:|---:|---:|---:|---:|---:|
| 5 | `308,067` | `1,201 / 711` | `40.7750% / 40.0000%` | `56.6667% / 86.6667%` | `18.0711% / 33.5609%` |
| 20 | `306,655` | `1,201 / 710` | `20.4944% / 20.0000%` | `30.1667% / 43.3333%` | `17.5049% / 33.2973%` |
| 60 | `303,047` | `1,200 / 705` | `11.7570% / 10.0000%` | `20.0000% / 33.3333%` | `20.1222% / 29.8806%` |

The 5-session variant reproduces the stored H-EXC-02 support and turnover.
Longer aggregation reduces churn and slightly reduces support, but that alone
does not make the 20- or 60-session form the same mechanism.

## Horizon membership stability

Mean/minimum Top-30 overlap:

| Pair | Mean overlap | Minimum overlap |
|---|---:|---:|
| 5 vs 20 | `34.7905%` | `10.0000%` |
| 5 vs 60 | `24.3750%` | `0.0000%` |
| 20 vs 60 | `42.3333%` | `20.0000%` |

The horizon variants are materially distinct. The reduction in turnover at 20
and 60 sessions is therefore a representation trade-off, not evidence that
the 5-session high-churn signal has been economically repaired.

## Existing-candidate overlap

Mean Top-30 overlap with C1/C2/C4 was:

| Window | C1 | C2 | C4 |
|---:|---:|---:|---:|
| 5 | `1.3380%` | `25.8562%` | `4.9431%` |
| 20 | `5.6500%` | `21.2240%` | `1.9623%` |
| 60 | `7.7564%` | `17.3028%` | `5.5417%` |

These are structural overlaps only and do not establish predictive
orthogonality.

## Decision

No horizon is selected. The fixed 5-session H-EXC-02 result remains the
registered baseline; 20 and 60 are recorded as distinct future representations
with lower turnover but materially different membership. The family remains:

`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`

The unresolved PIT/CA/identity boundary, high 5-session churn, and lack of
target evidence remain. No C5 ID or protected-packet entry was created.

## Provenance and hashes

- Preregistration: `2026-09-19_ALPHA_HEXC02_HORIZON_PREREGISTRATION_V1.md`
- Code: `research/alpha_hex02_horizon_stability_v1.py`
- Code SHA-256: `db6540c78e424d174ba9e60d50b5a261c7db6718bf5accc5ec0d0d6c644b080a`
- Output: external staged `alpha_hex02_horizon_stability_v1.json`
- Output SHA-256: `1b79e8280a2ae1e7446b39c130b73951ded9b0d5cfc0083424460234081eb2e2`
- H-EXC-02 structural output SHA-256: `27ed30b6a7d4c2d19260b4ffd1a7cc2772824e3e28ce0087f027f59d80b5d629`
- Repository head used: `988e0c44`
- Manifest SHA-256: `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`

The JSON is staged at
`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hex02_horizon_stability_v1.json`.

