# C1/C4 Horizon Bridge V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_C1_C4_HORIZON_BRIDGE / NO ADMISSION`

## Question

Does C1/C4 overlap mainly come from a common short/medium-horizon reversal
window, or is it materially changed by C1 beta residualization and the C1/C4
normalizers?

## Method

On the frozen structural panel, reconstruct five target-free representations:

- stored C1: `-c1_residual / vol_20`;
- raw C1 reversal: `-ret_5`;
- C1 residual numerator: `-(ret_5 - beta_60_prior * market_ret_5)`;
- stored C4: `-ret_20 / abs_ret_sum_20`;
- raw C4 reversal: `-ret_20`.

For each representation, select fixed Top-30 names by descending value with an
ascending ticker tie-break. Compare same-day Top-30 overlap, Jaccard, exact
membership, and daily cross-sectional Spearman rank association.

No target, forward return, H5/H10, IC/ICIR, OOS, PnL, incumbent result,
provider, cloud, canonical, capture, telemetry, scheduler, or production state
was accessed.

## Result

| Pair | Common dates | Mean Top-30 overlap | Mean Jaccard | Mean daily Spearman |
|---|---:|---:|---:|---:|
| C1 stored vs raw `-ret_5` | 1,141 | 60.19% | 44.04% | 0.9030 |
| C1 stored vs residual numerator | 1,141 | 63.75% | 47.63% | 0.9548 |
| raw `-ret_5` vs residual numerator | 1,141 | 84.55% | 75.22% | 0.9338 |
| C1 stored vs C4 stored | 1,141 | 35.80% | 22.23% | 0.4626 |
| residual numerator vs raw `-ret_20` | 1,141 | 36.82% | 23.00% | 0.4084 |
| raw `-ret_5` vs raw `-ret_20` | 1,201 | 37.96% | 23.92% | 0.4327 |
| C4 stored vs raw `-ret_20` | 1,201 | 62.22% | 46.63% | 0.9370 |

## Interpretation

The shared C1/C4 overlap is not explained by one simple horizon-only identity.
Raw 5-session versus raw 20-session reversal overlap is 37.96%, close to the
previous residual-numerator/raw-C4 overlap of 36.82% and stored-score overlap
of 35.80%.

Within C1, beta residualization changes the raw reversal representation but it
remains strongly related to it (84.55% Top-30 overlap). The C1 volatility
normalizer changes membership further: stored C1 versus residual numerator is
63.75%, and stored C1 versus raw reversal is 60.19%. C4's path-amplitude
normalizer has a similar structural effect at 62.22% overlap with raw
20-session reversal.

This strengthens the statement that C1/C4 are related reversal surfaces while
their normalizers materially shape membership. It does not establish
predictive redundancy, orthogonality, risk-adjusted value, PIT safety,
capacity, or candidate admission.

## Reproducibility

- Script: `research/alpha_c1_c4_horizon_bridge_v1.py`
- Script SHA-256: `85c8ddce7de8c18070390f4b8647e792997c0943e41dbc92a532014bc0ed82b5`
- Focused test: `tests/test_alpha_c1_c4_horizon_bridge_v1.py` (`1/1`)
- Test SHA-256: `6e80b7bd6ba5e67b7f208c06e34f8338860734276e8b64c2c1a754e4c6ba6e68`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-c1-c4-horizon-bridge\c1_c4_horizon_bridge_v1.json`
- External result SHA-256: `f7499f1bdf9559b0af5b05625547197315b2fe3bb838a998eaa7282126ebdddd`
- Machine-readable result: `research_knowledge/c1_c4_horizon_bridge_v1.json`
- Feature SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

## Adjudication

| Gate | Result |
|---|---|
| Formula/component reconstruction | `PASS` |
| Horizon/normalizer overlap map | `SUPPORTED_SCOPED` |
| Candidate/era/policy selection | `NO` |
| Predictive/risk-adjusted interpretation | `FORBIDDEN / NOT TESTED` |
| Protected boundary | `CLOSED` |
