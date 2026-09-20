# Candidate Overlap by Market State V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_CANDIDATE_OVERLAP_MARKET_STATE / NO ADMISSION`

## Question

Does same-day Top-30 overlap among C1, C2, and C4 change with a deterministic
market-breadth state, without using any target or forward outcome?

## Method

On the guarded Stage-A surface, define four same-day states from the share of
eligible finite names with positive `ret_5` and positive C2 abnormal-turnover
log. Each share is thresholded at 0.5: `HIGH_HIGH`, `RET_HIGH_ACT_LOW`,
`RET_LOW_ACT_HIGH`, and `LOW_LOW`. For each state, compute fixed Top-30
overlap fraction and Jaccard for C1/C2, C1/C4, and C2/C4.

This is a deterministic structural decomposition, not a regime-return test.
There was no tuning, target, forward return, H5/H10, IC/ICIR, OOS, PnL,
incumbent result, or candidate promotion.

## Result

The common sample has 1,141 dates. Mean overlap fractions by state are:

| State | Dates | C1/C2 | C1/C4 | C2/C4 |
|---|---:|---:|---:|---:|
| `HIGH_HIGH` | 348 | 0.08898 | 0.34971 | 0.08285 |
| `LOW_LOW` | 230 | 0.19638 | 0.35551 | 0.16406 |
| `RET_HIGH_ACT_LOW` | 220 | 0.15045 | 0.32303 | 0.11515 |
| `RET_LOW_ACT_HIGH` | 343 | 0.15364 | 0.39057 | 0.14956 |

Overlap is state-dependent: C1/C2 and C2/C4 are lowest in `HIGH_HIGH`,
whereas C1/C4 is highest in `RET_LOW_ACT_HIGH`. This supports a structural
complementarity map only; it does not establish predictive orthogonality,
regime efficacy, or a reason to condition or combine candidates.

## Reproducibility

- Code: `research/alpha_candidate_overlap_market_state_v1.py`
- Code SHA-256: `d3c5a27bb2f089999c59b372eded1591bb96d862b19d5207259e152cd93afbfa`
- Test: `tests/test_alpha_candidate_overlap_market_state_v1.py` (`1/1`)
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-candidate-overlap-market-state\alpha_candidate_overlap_market_state_v1.json`
- External result SHA-256: `9c8be6a9c5e571f68ca5469809e09eaf3caa7a84d93b67169526d16efdf980f8`
- Machine-readable copy: `research_knowledge/candidate_overlap_market_state_v1.json`
- Component helper SHA-256: `de8466ce25cce5fad2e91ada8877e8c8f8806492655355072ad45c88eb14255e`
- Feature input SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel input SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session input SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

## Adjudication

| Gate | Result |
|---|---|
| Structural overlap calculation | `PASS` |
| Market-state decomposition | `SUPPORTED_SCOPED` |
| Candidate/era/policy selection | `NO` |
| Predictive or risk-adjusted interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |
