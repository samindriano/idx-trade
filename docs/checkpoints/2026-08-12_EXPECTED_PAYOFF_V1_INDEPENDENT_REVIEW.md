# Expected Payoff V1 — Independent Review

Date: 2026-08-12 (Asia/Jakarta)

Branch: `research/idx-expected-payoff-v1`

Reviewed runtime anchor: `bf6916927ea1a3ecd73708834aa38d0ad91c3c88`

Original runtime verdict: `EXPECTED_PAYOFF_V1_NO_SURVIVOR`

Independent review decision: `EXPECTED_PAYOFF_V1_RUNTIME_VERDICT_NOT_ACCEPTED_BASELINE_METRIC_BUG`

## Finding

The frozen V1 specification defines `TRAIN_MEAN_PAYOFF` as follows:

1. compute the mean `payoff_atr_gross` on resolved training rows only;
2. predict that constant for every validation row;
3. compute `MSE_TRAIN_MEAN` on the exact validation outcomes;
4. compute `MSE_SKILL = 1 - MSE_V1 / MSE_TRAIN_MEAN`.

The implementation does not evaluate the baseline this way.

`train_mean_baseline(train_y)` returns both the training mean and the MSE of the training targets around that mean, i.e. training-set target variance. `fit_fold_model(...)` returns that training-set MSE as `baseline_mse`. The fold evaluation then computes `MSE_V1` on validation rows but calculates:

`mse_skill = 1 - validation_mse_v1 / training_set_baseline_mse`.

Therefore the numerator and denominator are evaluated on different populations. The denominator is not the frozen `MSE_TRAIN_MEAN` comparator required by the specification.

This is decision-changing because MSE skill is a mandatory survivor gate. The reported negative median MSE skill and `1/6` positive-skill folds cannot be used to accept `EXPECTED_PAYOFF_V1_NO_SURVIVOR` until the baseline metric is corrected.

The large V2F5 reported skill (`-15.213322`) may be amplified by this denominator mismatch, but no corrected scientific conclusion is inferred before the exact remediation is run.

## What remains valid

The following evidence is not invalidated by this specific bug, subject to the existing provenance checks:

- exact accepted V0 validation key alignment;
- the fitted frozen one-candidate V1 predictions already produced at the runtime anchor;
- session IC diagnostics;
- D10-D1 payoff-spread diagnostics;
- data-readiness/protected-runtime findings unrelated to the baseline metric.

No new model candidate, tuning, loss, feature, horizon, target transform, or rescue is authorized.

## Authorized remediation boundary

A **metric-only correction** is scientifically appropriate and is not a rescue experiment.

Do not refit or rerun the V1 payoff model if avoidable. Reuse the already-produced frozen `validation_predictions.parquet` and model artifacts from the original V1 runtime.

For each frozen fold:

1. reconstruct/verify the exact original resolved training target rows under the already-frozen V1/V0 contract;
2. compute `train_mean_payoff` from those training rows only;
3. apply that constant prediction to every accepted validation row;
4. compute validation-set baseline MSE as `mean((y_validation - train_mean_payoff)^2)`;
5. compute corrected `MSE_SKILL = 1 - MSE_V1_validation / MSE_TRAIN_MEAN_validation`;
6. rerun the **unchanged frozen survivor gate** using the corrected six MSE-skill values plus the already-produced IC/spread metrics.

Persist a separate post-review correction artifact and manifest. Preserve the original V1 runtime artifacts and original incorrect verdict for auditability; label them superseded for the MSE-gate decision, not deleted or rewritten.

No provider call, fresh-forward outcome access, O2 rescore/retrain, target repair, alternative baseline, or model refit/tuning is authorized.

## Review conclusion

The V1 scientific outcome is currently **undetermined**, not `NO_SURVIVOR` and not `SURVIVOR`, pending the exact frozen metric correction above.
