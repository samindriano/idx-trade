# Stage 5 Post-Mortem — Implementation Ready

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage5-postmortem-v1`
Parent: `research/idx-stage5-ranking-holdout-v1`
Substantive post-mortem code commit: `f51f9778a6657b52752d2423dbde8499c693bf70`
Draft PR: #8

## Status

**`STAGE5_POSTMORTEM_IMPLEMENTATION_READY`**

Ranking V1 remains a failed benchmark. The consumed Stage-5 holdout is now allowed only for bounded diagnosis/V2 hypothesis generation; it cannot regain independent validation status.

## Frozen diagnostic scope

Read `docs/STAGE5_POSTMORTEM_PLAN_V1.md`.

Exactly five diagnostic hypotheses are frozen before additional runtime inspection:

1. A/B frozen-feature distribution drift;
2. A/B feature-to-outcome relationship drift;
3. localization across six fixed non-overlapping temporal blocks A1/A2/A3/B1/B2/B3;
4. causal market/regime environment drift using the full primary-liquid universe;
5. HGB decile/top-tail behavior separately in A and B.

No training, selection, calibration, target search, threshold search, Stage-5 rerun, or V1 rescue is implemented.

## Input guards

The runner fails closed unless all of these exact consumed Stage-5 facts match:

- signal panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- Stage-5 H10 predictions SHA-256: `9d850776c98c07e069b32d606ad510d94a26435659da86997f5302d765d8ee8c`;
- Stage-5 summary SHA-256: `1a38171eead5a9c72de62da4f6ef486f35e3fba2e962c3b0bccac9fea033acd0`;
- Stage-5 security master SHA-256: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`;
- Stage-5 summary decision is `STAGE5_RANKING_HOLDOUT_FAIL`;
- `holdout_consumed=true`;
- `holdout_consumed_for=RANKING_V1_ONLY`;
- `holdout_outcome_accessed=true`;
- durable global holdout-consumption marker exists and agrees.

The frozen calendar guard is inherited from the Stage-5 runner. Numerical runtime must match the Stage-3/4/5 exact environment.

## Implementation validation

GitHub Actions on substantive code commit `f51f9778a6657b52752d2423dbde8499c693bf70`:

- **211 passed, 0 failed**;
- 15 existing warning instances/classes from older data-foundation tests;
- the initial post-mortem test-fixture warning flood was removed before readiness;
- no new post-mortem warning appears in the final CI warning summary.

## External outputs

One descriptive runtime should emit outside Git:

- `postmortem_fixed_block_metrics.csv`;
- `postmortem_feature_drift_a_vs_b.csv`;
- `postmortem_feature_target_relation_by_half.csv`;
- `postmortem_market_regime_daily.csv`;
- `postmortem_market_regime_a_vs_b.csv`;
- `postmortem_hgb_deciles_by_half.csv`;
- `postmortem_summary.json`.

All outputs are hashed by the runner.

## Next action

Run exactly the bounded descriptive post-mortem against the already-consumed Stage-5 artifacts, then stop for independent ChatGPT interpretation. No Ranking V2 implementation is authorized by this readiness checkpoint.