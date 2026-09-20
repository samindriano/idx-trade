# C2 Interaction Quadrants V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_C2_INTERACTION_QUADRANTS / NO ADMISSION`

## Question

Does C2's product `ret_5 * log(abnormal turnover)` represent one dominant
mechanism, or a mixture of sign-consistent market states?

## Scope and method

Using the guarded C1/C2/C4 feature artifact and the structural panel, the
fixed C2 Top-30 selection was classified into four sign quadrants:

- positive `ret_5` and nonnegative log abnormal turnover;
- positive `ret_5` and negative log abnormal turnover;
- negative `ret_5` and nonnegative log abnormal turnover;
- negative `ret_5` and negative log abnormal turnover.

The audit compares pooled eligible-universe shares with pooled Top-30 slot
shares and reports enrichment. It uses existing descending C2 rank and
ascending ticker tie-break. It does not read targets, forward returns,
incumbent predictive results, H5/H10, IC/ICIR, OOS, PnL, provider, cloud,
canonical, capture, telemetry, scheduler, or production state.

## Result

| Quadrant | Eligible share | Top-30 share | Pooled enrichment | Interpretation |
|---|---:|---:|---:|---|
| `ret_5 >= 0`, activity `>= 0` | 29.13% | 68.68% | 2.36x | Positive-return/high-activity confirmation dominates |
| `ret_5 < 0`, activity `< 0` | 27.79% | 31.32% | 1.13x | Negative-return/low-activity confirmation is secondary |
| `ret_5 >= 0`, activity `< 0` | 20.15% | 0.00% | 0.00x | Negative product; zero selection is mechanically expected |
| `ret_5 < 0`, activity `>= 0` | 22.93% | 0.00% | 0.00x | Negative product; zero selection is mechanically expected |

All selected Top-30 slots have positive C2 scores in this artifact. The zero
cross-sign selection is therefore a consequence of the product and the
availability of enough positive-score names, not evidence that cross-sign
states have no predictive or economic value.

The positive/positive versus negative/negative mixture shifts by year:

| Year | Positive-return/high-activity | Negative-return/low-activity |
|---|---:|---:|
| 2021 | 76.82% | 23.18% |
| 2022 | 64.69% | 35.31% |
| 2023 | 65.06% | 34.94% |
| 2024 | 67.71% | 32.29% |
| 2025 | 78.80% | 21.20% |
| 2026 partial | 59.90% | 40.10% |

This is a descriptive change in the composition of a mechanically selected
interaction score. It is not evidence of a regime return, predictive
stability, or a reason to split C2 into new candidates.

## Adjudication

| Gate | Result |
|---|---|
| C2 quadrant mechanics | `PASS_STRUCTURAL_ONLY` |
| Candidate/policy/era selection | `NO` |
| Predictive interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |

The result clarifies C2 as a two-mode sign-consistent interaction and adds a
bounded regime-mixture observation. It does not change C2's `FUTURE_RESEARCH`
status or create C5.

## Reproducibility

- Code: `research/alpha_c2_interaction_quadrants_v1.py`
- Code SHA-256:
  `e8fd8223bf73ffc14e61741fbf4d31f9966f01aadfabe96d34a531a2d04fcdfc`
- Component helper SHA-256:
  `de8466ce25cce5fad2e91ada8877e8c8f8806492655355072ad45c88eb14255e`
- Result: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-c2-quadrants\alpha_c2_interaction_quadrants_v1.json`
- Result SHA-256:
  `cb6ca355519ae6f4b3359e30e7aa2d10e5f783ce8213bffd3049af004647d57e`
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel input SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Focused tests: `1/1` passing.
