# C1/C4 Numerator-Overlap V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_C1_C4_NUMERATOR_OVERLAP / NO ADMISSION`

## Question

Does the observed C1/C4 cross-candidate overlap mainly come from their shared
reversal numerators, or from denominator/normalizer terms?

## Scope and method

Using the frozen guarded feature artifact, structural panel, and official
session calendar, the audit compares fixed Top-30 sets under:

- stored C1 score versus C1 numerator-only proxy
  `-(ret_5 - beta_60_prior * market_ret_5)`;
- stored C4 score versus C4 numerator-only proxy `-ret_20`;
- stored C1 score versus stored C4 score;
- C1 numerator-only proxy versus C4 numerator-only proxy.

Selection is descending value with ascending-ticker tie-break. The audit is
outcome-blind and does not read targets, forward returns, H5/H10, IC/ICIR,
OOS, PnL, incumbent results, provider, cloud, canonical, capture, telemetry,
scheduler, or production state.

## Result

| Comparison | Common dates | Mean Top-30 overlap | Median overlap | Mean Jaccard |
|---|---:|---:|---:|---:|
| C1 score vs C1 numerator | 1,141 | 63.75% | 63.33% | 0.4763 |
| C4 score vs C4 numerator | 1,201 | 62.22% | 63.33% | 0.4663 |
| C1 score vs C4 score | 1,141 | 35.80% | 36.67% | 0.2223 |
| C1 numerator vs C4 numerator | 1,141 | 36.82% | 36.67% | 0.2300 |

The numerator-only cross-candidate overlap is only 1.02 percentage points
higher than the stored-score overlap. Therefore denominator/normalizer terms
change membership, but they do not materially explain the shared C1/C4
overlap. The shared reversal numerator remains a real structural caution.

Within-candidate overlap is not 100%: each normalizer/score construction
contributes meaningful rank reordering. This does not tell us whether that
reordering is predictive or economically useful.

## Adjudication

| Gate | Result |
|---|---|
| Numerator/score overlap mechanics | `PASS_STRUCTURAL_ONLY` |
| Shared C1/C4 caution | `SUPPORTED_SCOPED` |
| Candidate/policy/era selection | `NO` |
| Predictive interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |

No candidate, C5, era, eligibility policy, or protected evaluation was
introduced. Candidate statuses remain unchanged.

## Reproducibility

- Code: `research/alpha_c1_c4_numerator_overlap_v1.py`
- Code SHA-256:
  `8e6975f93920a7a11404ba8be3f1cce8a2ffe18c186f3db2a0255ffa5679a830`
- Component helper SHA-256:
  `de8466ce25cce5fad2e91ada8877e8c8f8806492655355072ad45c88eb14255e`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-c1-c4-overlap\alpha_c1_c4_numerator_overlap_v1.json`
- External result SHA-256:
  `24fa534373f33af6e255432284d4c563cd27e374ed8f43183c6496ee08d58ab8`
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel input SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Focused test: `tests/test_alpha_c1_c4_numerator_overlap_v1.py`, `1/1`.
