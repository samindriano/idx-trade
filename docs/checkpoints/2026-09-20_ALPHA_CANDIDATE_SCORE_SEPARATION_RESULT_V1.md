# Candidate Score-Separation Mechanics V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_SCORE_SEPARATION / NO ADMISSION`

## Question

Does fixed Top-30 turnover arise from a thin score edge at the selection
boundary, or from broader score-distribution behavior? This is a structural
diagnostic only; it does not ask whether any score predicts an outcome.

## Scope and boundary

The audit reads only the guarded Stage-A feature artifact and the official
session calendar. For each candidate and usable date it orders the eligible
finite rows by the existing descending rank with ascending-ticker tie-break,
then records:

- score at rank position 30 and score at position 31;
- raw boundary gap and boundary gap normalized by same-day finite-score IQR;
- top-1 to top-30 score gap, also IQR-normalized;
- exact score ties at the 30/31 boundary;
- fraction of unique scores in Top-30;
- next-session Top-30 turnover and its correlation with the current boundary
  gap.

The next-session comparison uses only consecutive official sessions within the
same calendar year for the year-stratified summaries. It does not read target,
forward-return, incumbent, H5/H10, IC/ICIR, OOS, PnL, cloud, provider,
canonical, capture, telemetry, scheduler, or production state.

## Result

| Candidate | Usable dates | Median normalized boundary gap | Exact 30/31 tie fraction | Mean next turnover | Spearman gap vs next turnover |
|---|---:|---:|---:|---:|---:|
| C1 | 1,141 | 0.01089 | 0.0000 | 41.74% | -0.071 |
| C2 | 1,201 | 0.05912 | 0.0000 | 32.62% | -0.174 |
| C3 | 275 | 0.01810 | 10.18% | 10.96% | -0.060 |
| C4 | 1,201 | 0.00936 | 0.0000 | 23.26% | -0.115 |

The score edge is widest for C2 on this normalized metric. C1 and C4 have
thin boundary gaps and higher/moderate turnover, but the relationship is not
strong enough to treat thin boundary separation as a complete explanation for
turnover. The negative correlations are modest structural associations, not
causal or predictive evidence.

C3's 10.18% exact boundary-tie fraction is consistent with its rank-aggregated,
sparse financial surface. Its low turnover and apparently stable boundary are
support-driven and cannot be treated as signal quality.

Calendar-year medians show no universal monotone drift:

| Candidate | 2022 | 2025 | 2026 partial |
|---|---:|---:|---:|
| C1 | 0.01261 | 0.00938 | 0.01080 |
| C2 | 0.05605 | 0.05960 | 0.04330 |
| C3 | — | 0.02449 | 0.01523 |
| C4 | 0.00777 | 0.00934 | 0.00890 |

The 2026 turnover increase documented in the era-mechanics experiment is
therefore not reducible to a simple across-the-board collapse in normalized
Top-30 score separation.

## Adjudication

| Gate | Result |
|---|---|
| Score-separation mechanics | `PASS_STRUCTURAL_ONLY` |
| Candidate/policy/era selection | `NO` |
| Predictive interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |

This adds a score-geometry view that was not present in the existing Top-K,
calendar-year, concentration, or rank-displacement summaries. It does not
change C1/C2/C4 `FUTURE_RESEARCH` or C3 `BLOCKED` status.

## Reproducibility

- Code: `research/alpha_candidate_score_separation_v1.py`
- Code SHA-256:
  `38777f7c530552ad88eb2e6779b64e2c64a1e4500c538692970eff935cfc80e9`
- Result: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-score-separation\alpha_candidate_score_separation_v1.json`
- Result SHA-256:
  `43866dc33d2ab6041f346666d6c6df674a68d72a20b805276c0ec115959ff9db`
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Focused tests: `2/2` passing.

The first execution was discarded after correcting the year-boundary pairing
rule. The recorded result is the corrected execution above.
