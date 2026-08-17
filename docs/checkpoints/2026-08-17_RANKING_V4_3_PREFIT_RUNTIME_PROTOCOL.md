# Ranking V4-3 — pre-fit runtime capture protocol

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3-prefit-runtime-v1`
Parent support acceptance: `review/idx-ranking-v4-3-support-acceptance-v1@48dbca3799a71306a62a9ad156a106e1a978b006`
Status: `V4_3_PREFIT_RUNTIME_CAPTURE_PROTOCOL_LOCKED_NO_TARGET_OR_MODEL_RUN`

## Purpose

This lane closes the runtime-reproducibility gate required by the frozen V4-3 preregistration before the first historical V4 target/model execution.

It does not modify the V4-3 scientific configuration and does not authorize target materialization or model fitting.

## Already accepted

The primary-liquid support/fold result is independently accepted:

`V4_3_PRIMARY_LIQUID_SUPPORT_ACCEPTED_6X100_IDENTITIES_FROZEN`

Exact accepted identities include:

- support manifest SHA-256 `6cb8df059d310bb337ffe7f5026d416f0e15252c79ecc04e6c597925a0d243a4`;
- validation folds SHA-256 `91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`;
- H5 eligible list SHA-256 `e5a9d541f74c5ec1c07496aac9597510e115c230b8e5b754e91721baa0eed0bb`;
- H10 eligible list SHA-256 `c6aa516058aae6406dc58844f27c434ebd4cd12ab4b637a74b135d66b9dda373`;
- consensus eligible list SHA-256 `06f7af7d0bc34c1714ed3c19684177cd27dd911c11fd509c231b9bdfb90f970b`.

## Frozen capture protocol

Machine-readable protocol:

`config/ranking_v4_3_prefit_runtime_protocol.json`

The capture must verify the exact preregistration and support bytes before doing anything else.

It records:

- Git HEAD and branch;
- clean-worktree state;
- full Python version and executable;
- OS/platform/architecture;
- exact numpy, pandas, pyarrow, scipy, scikit-learn, joblib and threadpoolctl versions;
- BLAS/OpenMP/threadpool libraries visible to the runtime;
- relevant thread environment variables;
- exact `HistGradientBoostingRegressor` signature and effective parameters;
- exact `SimpleImputer` signature and effective control/geometry parameters;
- SHA-256 identities of the V4-3 config/support/code files used by the capture.

The script constructs estimators only to inspect their effective configuration. It never calls `.fit()` or `.predict()`.

## Runtime choice rule

The first successful capture freezes the runtime used for the initial V4 historical-development execution.

No package upgrade/downgrade, Python switch, learner-signature change, or runtime substitution may be performed after V4 target/performance access to improve the result. A material runtime change after outcome access requires a separately preregistered generation.

## Exact learner check

The capture verifies the already frozen learner:

`sklearn.ensemble.HistGradientBoostingRegressor(loss="squared_error")`

with:

- learning rate `0.05`;
- max iterations `200`;
- max leaf nodes `31`;
- max depth `None`;
- minimum samples per leaf `20`;
- L2 regularization `1.0`;
- max bins `255`;
- categorical features `None`;
- warm start `False`;
- early stopping `False`;
- random state `42`.

It also verifies the two already frozen median-imputation policies.

## Outcome-blind boundary

During capture, prohibited actions include:

- loading R5/R10;
- materializing target ranks;
- estimator fitting;
- prediction generation;
- IC/Top30/raw-return performance calculation;
- protected/fresh-forward outcome access;
- provider calls.

## Important target-materialization hardening still required

Runtime capture is not the final execution authorization.

Before first V4 target materialization, the execution implementation must explicitly preserve the V4-2 fail-closed rule for mechanical corporate-action price discontinuities across `Open_(t+1) -> Close_(t+5/t+10)`. `corporate_action_integrity_verified` must not be silently treated as proof that no split/bonus/rights discontinuity occurs inside the forward price interval unless that semantic equivalence is independently established.

This is an implementation hardening requirement, not permission to change target definitions, folds, thresholds, or feature families.

## Next local-only step

Run the focused V4-3 preregistration + prefit tests, then execute only:

`python scripts/capture_v4_3_prefit_environment.py --repo-root . --output-dir <new immutable external output dir>`

Promote only the small generated environment manifest and its SHA-256/checkpoint metadata. Stop before any V4 target/model run.

Verdict:

`V4_3_PREFIT_RUNTIME_CAPTURE_PROTOCOL_LOCKED_NO_TARGET_OR_MODEL_RUN`
