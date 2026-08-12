# Reliability / Uncertainty V0 — Implementation Ready

Date: 2026-08-13 (Asia/Jakarta)
Branch: `research/idx-reliability-uncertainty-v0`

## Status

`RELIABILITY_V0_IMPLEMENTATION_READY_NOT_EXECUTED`

The frozen V0 specification is committed at `37259c68e22d5703f6fae6738785dee87886e63c`.

Implementation and contract tests are now present:

- `src/idx_trade/reliability_v0.py`;
- `tests/test_reliability_v0.py`.

No historical diagnostic runtime has been executed by ChatGPT because the pinned external O2/V3-B/Open artifacts live in the local Windows external artifact store rather than the Git repository.

## Frozen implementation boundary

The runner:

- consumes only the accepted historical O2 OOF candidate predictions;
- reconstructs exact 36 O2 raw features from the pinned V3-B table plus pinned Open coverage artifact;
- computes fold-training-only empirical support statistics;
- evaluates only the two frozen primary proxies:
  - `score_margin_reliability`;
  - `joint_marginal_support_reliability`;
- persists `observed_feature_fraction` and `mean_marginal_support` as non-gating secondary diagnostics;
- computes realized local pairwise ranking quality only after proxy construction;
- evaluates frozen session/fold/selective/conditional gates;
- contains no reliability estimator fitting, composite score, trade filter, provider call, O2 refit/rescore, or fresh-forward access path.

## Required next step

Run focused/full tests locally, locate the already-pinned Open coverage artifact by SHA, and execute the frozen diagnostic **once** into a new external output directory. Do not alter the spec, proxies, thresholds, or runtime after seeing results. Then checkpoint/push the factual verdict and stop for independent review.
