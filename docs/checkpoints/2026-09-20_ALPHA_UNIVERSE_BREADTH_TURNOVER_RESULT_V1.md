# Universe Breadth versus Turnover V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_UNIVERSE_BREADTH_TURNOVER / NO ADMISSION`

## Question

Are observed Top-30 turnover differences mainly explained by the breadth of
the finite eligible universe, or is universe breadth a weak confounder for the
candidate score mechanics?

## Scope and method

For each fixed C1/C2/C3/C4 rank column, the audit counts per official session:

- all rows in `eligible_decision_universe`;
- rows with finite candidate rank;
- finite support as a share of the eligible universe.

It then measures one-way Top-30 turnover between adjacent official sessions,
using only pairs within the same calendar year. It reports Spearman association
between turnover and current/previous finite-support count, absolute count
change, and relative count change. Selection is descending rank with
ascending-ticker tie-break.

No target, forward return, H5/H10, IC/ICIR, OOS, PnL, incumbent result,
provider, cloud, canonical, capture, telemetry, scheduler, or production state
was accessed.

## Result

| Candidate | Pairs | Mean turnover | Mean finite count | Finite/eligible share | Count-vs-turnover rho | 2026 rho |
|---|---:|---:|---:|---:|---:|---:|
| C1 | 1,135 | 41.74% | 258.73 | 99.54% | 0.133 | -0.045 |
| C2 | 1,195 | 32.62% | 258.74 | 100.00% | 0.061 | 0.107 |
| C3 | 274 | 10.97% | 111.27 | 35.96% | -0.372 | -0.711 |
| C4 | 1,195 | 23.26% | 258.38 | 99.85% | 0.175 | -0.060 |

Absolute finite-count-change versus turnover is also weak for C1/C2/C4:
`0.079`, `-0.007`, and `0.049`. C3 is materially different: its 2026
absolute-count-change association is `0.439`, while its current finite-count
association is `-0.711`.

## Interpretation

For C1/C2/C4, finite rank support is nearly the complete eligible universe and
its breadth is only weakly associated with turnover. The earlier conclusion
that turnover is not explained by one universal score-edge mechanism is
therefore not replaced by a simpler “universe size” explanation.

C3 has low finite support relative to its eligible universe and strong
support/turnover associations in 2026. This strengthens the existing warning
that C3's lower turnover, longer persistence, and concentration are support-
driven diagnostics, not evidence of superior stability or predictive quality.

The result is descriptive and correlational. It does not establish causality,
population completeness, PIT safety, capacity, predictive stability, or a
candidate/era decision.

## Adjudication

| Gate | Result |
|---|---|
| Breadth/turnover mechanics | `PASS_STRUCTURAL_ONLY` |
| C1/C2/C4 universal breadth explanation | `NOT_SUPPORTED_SCOPED` |
| C3 support-sensitivity caution | `SUPPORTED_SCOPED` |
| Candidate/policy/era selection | `NO` |
| Predictive interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |

## Reproducibility

- Code: `research/alpha_universe_breadth_turnover_v1.py`
- Code SHA-256:
  `e3ae3010b707232fcfcfdb966b9618e8e230bb1c11e4477f1d9e593af827fe6a`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-universe-breadth-turnover\alpha_universe_breadth_turnover_v1.json`
- External result SHA-256:
  `4c9d752c926f5d206bb2e7842e89188d470adefbe30ff12815cbccea50236468`
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Focused test: `tests/test_alpha_universe_breadth_turnover_v1.py`, `1/1`.
