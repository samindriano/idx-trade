# Expected Payoff V1 Metric-Only MSE Correction

Date: 2026-08-13 (Asia/Jakarta)

Branch: `research/idx-expected-payoff-v1`

Review anchor: `fb584c988cd4ac07ef077103f5a53f6ba3ef097e`

## Decision

`EXPECTED_PAYOFF_V1_NO_SURVIVOR`

The original runtime verdict at `bf6916927ea1a3ecd73708834aa38d0ad91c3c88`
was not decision-valid because its training-mean baseline MSE used training
target variance rather than validation error of the training-derived constant.
This checkpoint applies only the authorized metric correction to the existing
frozen V1 validation predictions. The model was not refit and no new
prediction was generated.

The corrected result remains NO_SURVIVOR: all six corrected MSE skills are
non-positive. The IC and D10-D1 metrics were carried forward unchanged from
the frozen validation predictions and remain positive on their respective
gates, but they cannot override the mandatory MSE-survivor gate.

## Corrected fold metrics

For each fold, `train_mean_payoff_atr` is computed from resolved training rows
only. `validation_baseline_mse` is then computed on that fold's existing
validation outcomes.

| Fold | Train mean | Validation baseline MSE | Frozen V1 validation MSE | Corrected MSE skill | Unchanged median IC | Unchanged mean D10-D1 |
|---|---:|---:|---:|---:|---:|---:|
| V2F1 | -0.113836 | 7.076126 | 7.370811 | -0.041645 | 0.070351 | 0.596744 |
| V2F2 | -0.106589 | 7.610069 | 7.874905 | -0.034801 | 0.021819 | 0.259721 |
| V2F3 | -0.117042 | 7.494278 | 8.164415 | -0.089420 | 0.010541 | 0.224503 |
| V2F4 | -0.085599 | 7.111585 | 7.557477 | -0.062699 | 0.026770 | 0.040763 |
| V2F5 | -0.101029 | 118.363196 | 118.560948 | -0.001671 | 0.030192 | -0.787390 |
| V2F6 | -0.014210 | 7.335748 | 10.456771 | -0.425454 | -0.026648 | 0.038350 |

Aggregate corrected gates:

- Data-ready: PASS.
- Median corrected MSE skill: `-0.0521721558`.
- Positive corrected-skill folds: `0/6`.
- Unchanged median session IC: `0.0242940252`; Q25: `0.0133601230`;
  positive folds: `5/6`.
- Unchanged median D10-D1 ATR spread: `0.1326330936`; positive folds:
  `5/6`.
- Corrected MSE gate: FAIL.
- Corrected IC gate: PASS.
- Corrected D10-D1 gate: PASS.
- Final corrected verdict: `EXPECTED_PAYOFF_V1_NO_SURVIVOR`.

The correction changes the decision from “undetermined” to a valid frozen
NO_SURVIVOR result. It does not authorize a rescue model, tuning, alternative
loss, horizon, feature set, or Expected Payoff V2.

## Provenance and boundaries

- Original V1 validation predictions were reused unchanged from the verified
  runtime manifest SHA `8f6a082016828bbd146b7ddfdf4d90ed0c4feedb946187dd2080aefdeeab63e2`.
- Validation key SHA remained
  `f978ec6b81ddc72259e403e78698971f655721f94fbfdcc57f682c5cea3c4602`.
- Validation rows: `140,595`.
- Training target reconstruction reused the frozen V0 payoff contract and
  cutoff `2026-07-31`; no provider/network call was made.
- Model refit: false. O2 rescore: false. Fresh-forward access: false.
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written.
- Original incorrect runtime artifacts remain unchanged and reachable.

Correction runtime output is external and was not committed:

`D:\Documents\Project\idx-trade-data-gate-20260808v\expected_payoff_v1_mse_correction_20260812_001`

Correction manifest SHA-256:
`befabebc8629f8fe6878508b37b7e698a3a0ed56f9a6f126bbb77ef584e9ba69`.

## Validation

- Focused V1 + correction tests: `10 passed`.
- Full IDX-Trade pytest before correction: `62 passed, 0 failed, 0 warnings`.
- Final full IDX-Trade pytest: `64 passed, 0 failed, 0 warnings, 5.43s`.
