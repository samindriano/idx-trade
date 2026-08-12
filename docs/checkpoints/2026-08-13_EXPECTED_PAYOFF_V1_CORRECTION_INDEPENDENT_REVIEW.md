# Expected Payoff V1 Corrected Result — Independent Review

Date: 2026-08-13 (Asia/Jakarta)

Branch: `research/idx-expected-payoff-v1`

Reviewed correction HEAD: `bc35d1c1d7d08ae3aa84c6e16200d20c1f279981`

Prior review anchor: `fb584c988cd4ac07ef077103f5a53f6ba3ef097e`

Decision: `EXPECTED_PAYOFF_V1_NO_SURVIVOR_ACCEPTED_LANE_CLOSED`

## Independent review conclusion

The metric-only correction is accepted. The original runtime baseline bug is corrected in the decision path without refitting the model or generating new predictions.

The corrected `TRAIN_MEAN_PAYOFF` comparator now follows the frozen V1 specification:

1. derive the constant from the resolved training targets only;
2. apply that training-derived constant to the corresponding frozen validation outcomes;
3. compute validation baseline MSE on those validation outcomes;
4. compute `MSE_SKILL = 1 - MSE_V1_validation / MSE_train_mean_validation`.

The correction implementation verifies the original V1 manifest and artifact hashes, reuses the frozen validation prediction parquet, verifies the accepted V0 validation-key SHA, reconstructs training payoff targets from the frozen historical sources, and checks that each recomputed frozen V1 validation MSE equals the original stored model MSE before changing only the baseline denominator.

A regression test explicitly demonstrates that validation baseline MSE is not interchangeable with training-target variance.

## Accepted corrected evidence

| Fold | Train mean | Validation baseline MSE | Frozen V1 validation MSE | Corrected MSE skill |
|---|---:|---:|---:|---:|
| V2F1 | -0.113836 | 7.076126 | 7.370811 | -0.041645 |
| V2F2 | -0.106589 | 7.610069 | 7.874905 | -0.034801 |
| V2F3 | -0.117042 | 7.494278 | 8.164415 | -0.089420 |
| V2F4 | -0.085599 | 7.111585 | 7.557477 | -0.062699 |
| V2F5 | -0.101029 | 118.363196 | 118.560948 | -0.001671 |
| V2F6 | -0.014210 | 7.335748 | 10.456771 | -0.425454 |

Accepted aggregate gates:

- data readiness: PASS;
- median corrected MSE skill: `-0.0521721558`;
- positive corrected MSE-skill folds: `0/6`;
- median session IC: `0.0242940252`, q25 `0.0133601230`, positive `5/6`: PASS;
- median D10-D1 ATR payoff spread: `0.1326330936`, positive `5/6`: PASS;
- mandatory conditional-mean MSE gate: FAIL;
- final decision: `EXPECTED_PAYOFF_V1_NO_SURVIVOR`.

Correction manifest SHA-256:
`befabebc8629f8fe6878508b37b7e698a3a0ed56f9a6f126bbb77ef584e9ba69`.

Validation reported by the correction checkpoint:

- focused V1 + correction tests: 10 passed;
- full repository pytest: 64 passed, 0 failed, 0 warnings.

## Scientific interpretation

The evidence supports a distinction between **payoff ordering** and **conditional-mean estimation**.

The frozen 36-feature representation still contains historical-development information useful for ordering future realized payoff: the IC and D10-D1 gates remain positive. But the single preregistered HGB squared-error regressor does not produce a reliable numerical conditional mean. It underperforms the simple training-derived constant mean on validation MSE in every one of the six folds.

Therefore V1 must not be used as an expected-R estimate, sizing input, or production payoff model. The positive ordering diagnostics do not rescue the failed calibration/conditional-mean objective.

## Boundary

This exact Expected Payoff V1 lane is closed.

Do not post-hoc rescue it with another estimator, loss, clipping/winsorization, target transform, quantile model, feature subset, horizon, entry rule, subgroup/regime split, or calibration transform. A future payoff hypothesis would require a genuinely new preregistered lane with a distinct scientific question and authorization.

No final refit or forward shadow is authorized for this V1.