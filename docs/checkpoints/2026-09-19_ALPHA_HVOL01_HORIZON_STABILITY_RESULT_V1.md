# H-VOL-01 Horizon Stability — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PASS_STRUCTURAL_ONLY / HORIZON_SENSITIVE / NO C5`

## Boundary and baseline reproduction

This was a fixed, target-free structural audit of exactly three preregistered
compression horizons. The existing `5/60` output reproduced exactly:

- finite eligible support: `308,514` rows;
- mean Top-30 turnover: `29.2777778%`.

No target, forward return, incumbent score, IC/ICIR, provider, network, cloud,
capture, telemetry, canonical dataset, refit, or candidate ID was accessed or
changed.

## Fixed horizon results

| Horizon | Finite rows / dates / tickers | Mean / q95 / max Top-30 turnover | Selected value Q1 | Mean overlap C1/C2/C4 |
|---|---:|---:|---:|---:|
| `5/20` | `308,486 / 1,201 / 711` | `36.2583% / 50.0000% / 66.6667%` | `36.3086%` | `6.9880% / 7.1607% / 12.6533%` |
| `5/60` | `308,514 / 1,201 / 711` | `29.2778% / 43.3333% / 53.3333%` | `42.7200%` | `9.5209% / 8.0155% / 15.5676%` |
| `20/120` | `271,045 / 1,141 / 643` | `12.5789% / 20.0000% / 30.0000%` | `38.0018%` | `14.8262% / 8.4166% / 16.6667%` |

The slow `20/120` form loses roughly `12.8%` of eligible rows and 60 dates
relative to the baseline, while the fast `5/20` form increases mean turnover by
about 7 percentage points and has a higher tail.

## Horizon distinctness

Mean Top-30 overlap between the fixed H-VOL forms was:

| Pair | Mean overlap |
|---|---:|
| `5/20` vs `5/60` | `58.9675%` |
| `5/20` vs `20/120` | `9.9182%` |
| `5/60` vs `20/120` | `29.3193%` |

The forms are therefore not monotone duplicates. That is a structural
representation finding, not evidence that one horizon is predictive or better.
The low overlap also means a future evaluation cannot carry all variants
without expanding the candidate budget; a separate freeze decision would be
required after data admission.

H-LIQ-01 overlap also changes materially: `16.0255%` for `5/20`, `13.5803%`
for `5/60`, and `10.9173%` for `20/120`. Mean daily Spearman with H-LIQ-01 is
`-0.0136 / -0.0780 / -0.1255` respectively.

## Interpretation and disposition

H-VOL is horizon-sensitive in support, turnover, and selected-name geometry:

- `5/20` is broadly available but has the highest churn and friction tail;
- `5/60` is the preregistered baseline and reproduces its prior result;
- `20/120` has lower churn but materially lower coverage and a different
  portfolio set.

This is useful evidence against treating the compression family as a single
robust representation. It does not reject the economic mechanism entirely, but
it keeps horizon choice unresolved and prevents any C5 admission. The status
remains `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`.

## Provenance

- Preregistration: `2026-09-19_ALPHA_HVOL01_HORIZON_STABILITY_PREREGISTRATION_V1.md`
- Code: `research/alpha_hvol01_horizon_stability_v1.py`
- Code SHA-256: `dcf043dbfbd650f7cf70647e1bf1ee950cf2495525f7805bd5c0aab5884f9ffd`
- Output: external staged `alpha_hvol01_horizon_stability_v1.json`
- Output SHA-256: `d7eeb1e9c738e3d01572ea085f9c13373ddd085b1bd566d42afbf3b3b4192203`
- Repository head used: `ac117806b7c82684d797f52b04a035f9968330a`
- Prior H-VOL output SHA-256: `7fe2f266c2ee5a8cdffe59bbb006ae491351704423e1db4458b01b41a9fa4f7b`
- Manifest SHA-256: `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`
- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Guarded features SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Official sessions SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability anchors SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`

## Decision

`PASS_STRUCTURAL_ONLY`: H-VOL horizon dependence is now quantified. No
horizon is selected, no candidate budget is expanded, and protected-target
evaluation remains blocked by independent Data QA admission.
