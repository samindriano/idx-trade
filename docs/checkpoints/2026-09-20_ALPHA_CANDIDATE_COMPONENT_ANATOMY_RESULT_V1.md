# Candidate Component Anatomy V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_COMPONENT_ANATOMY / NO ADMISSION`

## Question

Which fixed formula components actually dominate the C1/C2/C4 cross-sectional
rank, and does the observed C1/C4 overlap reflect a shared dominant component?

## Scope and method

This is an outcome-blind reconstruction over the guarded Stage-A feature
artifact, the structural market panel, and the official session calendar. It
rebuilds the market-side rolling components using the same official-session
surface and current eligibility mask, then checks recomputed scores against the
stored C1/C2/C4 scores.

The formulas are:

- C1: `-(ret_5 - beta_60_prior * market_ret_5) / vol_20`
- C2: `ret_5 * log(turnover_mean_5 / turnover_median_60)`
- C4: `-ret_20 / abs_ret_sum_20`

The audit records daily Spearman association between each component and the
candidate score, plus the component percentile of fixed Top-30 selections. It
does not read C3 financial outcomes, targets, forward returns, incumbent
predictive results, H5/H10, IC/ICIR, OOS, PnL, cloud, provider, canonical,
capture, telemetry, scheduler, or production state.

## Formula consistency gate

The recomputed scores match the stored feature artifact exactly on every finite
value checked:

| Candidate | Finite values checked | Maximum absolute difference |
|---|---:|---:|
| C1 | 295,243 | 0.0 |
| C2 | 310,761 | 0.0 |
| C4 | 310,323 | 0.0 |

This is a consistency result for the frozen implementation and inputs. It is
not proof of PIT safety, population completeness, or predictive validity.

## Main structural findings

### C1

C1 rank is dominated by the residual-reversal numerator: median daily
Spearman association between score and residual is `-0.9599`, because lower
residual is preferred. The beta-market component (`0.0646`) and volatility
denominator (`-0.0399`) are secondary on this rank diagnostic. Top-30 names
are low-percentile on residual (`0.1053`) but near-neutral on beta-market
component (`0.5412`) and volatility (`0.4717`).

### C4

C4 rank is dominated by negative 20-session return: median daily Spearman
association between score and `ret_20` is `-0.9519`. The path-length
normalizer has materially weaker rank association (`-0.1136`). Top-30 names
are low-percentile on `ret_20` (`0.1121`) and near-neutral on path length
(`0.4730`).

This supports the existing structural caution that C1/C4 share a reversal
family, but it does not establish predictive redundancy or prove that one
should be removed.

### C2

C2 is more clearly an interaction. Its median daily score association is
`0.2681` with `ret_5` and approximately zero (`-0.0045`) with log abnormal
turnover. Yet its Top-30 names are elevated on both component percentiles:
`0.6944` for `ret_5` and `0.6772` for log abnormal turnover. A one-component
interpretation would therefore be misleading.

## Adjudication

| Gate | Result |
|---|---|
| Formula consistency | `PASS_SCOPED` |
| Component anatomy | `SUPPORTED_STRUCTURAL_ONLY` |
| Candidate/policy/era selection | `NO` |
| Predictive interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |

The result adds formula-component understanding and supports the C1/C4
shared-reversal caution. It does not change C1/C2/C4 `FUTURE_RESEARCH` or
C3 `BLOCKED` status, and it does not create C5.

## Reproducibility

- Code: `research/alpha_candidate_component_anatomy_v1.py`
- Code SHA-256:
  `de8466ce25cce5fad2e91ada8877e8c8f8806492655355072ad45c88eb14255e`
- Result: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-component-anatomy\alpha_candidate_component_anatomy_v1.json`
- Result SHA-256:
  `c024d20e01008e2ba13d234843f195dbf859dfd9dbe66cc3404344bb57230295`
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel input SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Focused tests: `1/1` passing.
