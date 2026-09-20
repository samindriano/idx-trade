# C1/C4 Normalizer Direction V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_C1_C4_NORMALIZER_DIRECTION / NO ADMISSION`

## Question

The prior numerator-overlap audit showed that C1/C4 normalizers materially
change Top-30 membership. Do those changes have a consistent structural
direction, or are they effectively random rank perturbations?

## Scope and method

The frozen formula components are:

- C1: `-(ret_5 - beta_60_prior * market_ret_5) / vol_20`;
- C4: `-ret_20 / abs_ret_sum_20`.

For each date, the audit compares fixed Top-30 membership under the stored
score against a numerator-only proxy. Names are classified as `both`,
`score_only`, or `numerator_only`. The denominator percentile is measured
within that date's eligible finite cross-section. The result reports the
per-date median denominator percentile by membership group.

No target, forward return, H5/H10, IC/ICIR, OOS, PnL, incumbent result,
provider, cloud, canonical, capture, telemetry, scheduler, or production state
was accessed.

## Result

| Candidate | Denominator | Score-only median percentile | Numerator-only median percentile | Median daily gap |
|---|---|---:|---:|---:|
| C1 | `vol_20` | 18.74% | 87.95% | -0.6983 |
| C4 | `abs_ret_sum_20` | 17.86% | 83.38% | -0.6570 |

The comparison covers 1,141 C1 dates and 1,201 C4 dates. The group counts are
balanced by construction: the number of score-only additions equals the number
of numerator-only removals on each date.

## Interpretation

The normalizers are not merely perturbing ranks. They consistently favor names
with lower denominator values: lower recent volatility for C1 and lower recent
absolute path amplitude for C4. This gives a structural explanation for the
roughly 62–64% within-candidate score/numerator overlap found earlier.

This does not establish that the tilt improves risk-adjusted returns, reduces
capacity costs, survives corporate-action/PIT correction, or is causally useful.
It is a representation-level structural finding only.

## Adjudication

| Gate | Result |
|---|---|
| Normalizer-direction mechanics | `PASS_STRUCTURAL_ONLY` |
| Directional denominator effect | `SUPPORTED_SCOPED` |
| Candidate/policy/era selection | `NO` |
| Predictive/risk-adjusted interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |

## Reproducibility

- Code: `research/alpha_c1_c4_normalizer_direction_v1.py`
- Code SHA-256:
  `e8ed247a90f55c65365bfd278b12e0b4d2c61d3e8ca5c709c03a10e3bff025c0`
- Component helper SHA-256:
  `de8466ce25cce5fad2e91ada8877e8c8f8806492655355072ad45c88eb14255e`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-c1-c4-normalizer-direction\alpha_c1_c4_normalizer_direction_v1.json`
- External result SHA-256:
  `ce269fee9faf34ebe7e90242ca57a285441620e89ead23b7ced30356db023a6d`
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel input SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Focused test: `tests/test_alpha_c1_c4_normalizer_direction_v1.py`, `1/1`.
