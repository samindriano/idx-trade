# C2 Market-Breadth Mixture V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_C2_MARKET_BREADTH_MIXTURE / NO ADMISSION`

## Question

Is the C2 positive-return/high-activity versus negative-return/low-activity
selection mixture related to same-day market-wide breadth, or is the annual
mixture shift unexplained by the available structural features?

## Scope and method

Using the frozen guarded feature artifact, structural panel, and official
session calendar, the audit reconstructs C2 components and, per session,
computes among eligible finite C2 rows:

- the share with `ret_5 >= 0`;
- the share with nonnegative log abnormal turnover;
- eligible pp and nn quadrant shares;
- fixed Top-30 C2 selected pp, nn, and cross-sign shares.

It then measures same-day Spearman associations between selected mixture and
market breadth. No forward outcome, target, H5/H10, IC/ICIR, OOS, PnL,
incumbent result, provider, cloud, canonical, capture, telemetry, scheduler,
or production state was accessed.

## Result

Across 1,201 C2 selection dates:

- selected pp mean share: `68.684%`;
- selected nn mean share: `31.316%`;
- cross-sign selected share: `0%`, mechanically due to the product sign;
- selected pp versus return-positive breadth: Spearman `0.7181`;
- selected pp versus activity-positive breadth: Spearman `0.4208`;
- selected pp versus eligible pp share: Spearman `0.8446`.

| Year | Selected pp | Selected nn | Return-positive breadth | Activity-positive breadth | Eligible pp |
|---|---:|---:|---:|---:|---:|
| 2021 | 76.82% | 23.18% | 49.33% | 54.76% | 32.00% |
| 2022 | 64.69% | 35.31% | 47.19% | 49.63% | 27.02% |
| 2023 | 65.06% | 34.94% | 49.39% | 52.24% | 28.99% |
| 2024 | 67.71% | 32.29% | 50.65% | 54.47% | 31.00% |
| 2025 | 78.80% | 21.20% | 51.87% | 56.79% | 32.90% |
| 2026 partial | 59.90% | 40.10% | 47.86% | 45.45% | 24.07% |

## Interpretation

The annual mixture shift is not an arbitrary calendar label: within this
structural artifact, C2 selection composition moves with same-day market-wide
return and activity breadth. The 2025-to-2026 change is consistent with a
reduction in both positive-return and positive-activity breadth.

This clarifies C2 as a market-state-conditioned interaction score. It does not
show that either state earns a return, that the relationship is causal, that
it is stable out of sample, or that C2 should be split into new candidates.

## Adjudication

| Gate | Result |
|---|---|
| C2 market-breadth mixture mechanics | `PASS_STRUCTURAL_ONLY` |
| Annual mixture explanation | `SUPPORTED_SCOPED` |
| Candidate split or new candidate | `NO` |
| Predictive/regime-return interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |

## Reproducibility

- Code: `research/alpha_c2_market_breadth_mixture_v1.py`
- Code SHA-256:
  `818a878049739b55e6305b62021055da79f6b2feccfb70fd23ced9249f57d451`
- Component helper SHA-256:
  `de8466ce25cce5fad2e91ada8877e8c8f8806492655355072ad45c88eb14255e`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-c2-market-breadth-mixture\alpha_c2_market_breadth_mixture_v1.json`
- External result SHA-256:
  `c1667a224b0300f6eeb8daf4db2b51c93854e0b67f16cc3e4f0ef209cca07de5`
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel input SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Focused test: `tests/test_alpha_c2_market_breadth_mixture_v1.py`, `1/1`.
