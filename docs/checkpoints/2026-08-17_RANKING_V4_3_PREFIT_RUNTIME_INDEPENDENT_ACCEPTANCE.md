# Ranking V4-3 pre-fit runtime — independent acceptance

Date: 2026-08-17 (Asia/Jakarta)
Reviewed branch: `research/idx-ranking-v4-3-prefit-runtime-v1`
Reviewed final HEAD: `ffa79256c4c8f2e202047bab5a9c8a4f3ddd3218`
Captured code HEAD: `640cb257bb93775ec69e3a6f6683fd50cb22417b`
Status: `V4_3_PREFIT_RUNTIME_ACCEPTED_EXECUTION_CODE_AND_CA_CONTINUITY_STILL_BLOCK_TARGET_ACCESS`

## Verdict

**ACCEPTED for the narrow pre-fit runtime-identity gate.**

The promoted environment manifest is byte-identical to the external capture and has SHA-256:

`cf6f1b0c859dd21b1c0f377f45d62ecdc98165ff6e0975b852a85b11cfbcaac6`.

The manifest records `outcome_blind=true`, `model_fit=false`, `prediction_generated=false`, `performance_computed=false`, and `provider_calls=false`.

## Runtime identity

Captured runtime:

- CPython 3.13.5 on Windows 11 AMD64;
- numpy 2.4.2;
- pandas 2.3.3;
- pyarrow 23.0.1;
- scipy 1.18.0;
- scikit-learn 1.8.0;
- joblib 1.5.3;
- threadpoolctl 3.6.0.

The instantiated `HistGradientBoostingRegressor` effective values for every V4-3-frozen parameter match the preregistration, including `loss=squared_error`, `learning_rate=0.05`, `max_iter=200`, `max_leaf_nodes=31`, `max_depth=None`, `min_samples_leaf=20`, `l2_regularization=1.0`, `max_bins=255`, `categorical_features=None`, `warm_start=False`, `early_stopping=False`, and `random_state=42`.

The control and geometry `SimpleImputer` policies likewise match their frozen median/imputation-indicator settings. Additional estimator/library defaults are recorded rather than silently treated as scientific degrees of freedom.

## Provenance review

The stale preregistration-pin issue is closed as provenance correction only. The V4-3 scientific config did not change: the canonical tracked preregistration bytes are SHA-256 `3a54dcf0266f8a2808b8c1d73dda41a32baea368e6b48aac21e9fa073f6824ed`.

The environment capture correctly records both canonical Git-byte hashes and worktree hashes. The captured HEAD precedes the later result/promotion documentation commits by design; those later commits did not participate in the runtime capture.

## Remaining hard gates before any V4 target access

This acceptance **does not authorize** R5/R10 materialization or model fitting.

Two pre-outcome engineering gates remain:

1. implement and hash-freeze the exact V4 target / feature / fit / scoring / evaluation code path against synthetic fixtures only;
2. implement explicit forward-price continuity semantics so `corporate_action_integrity_verified` is not silently interpreted as proof that every split, reverse split, stock dividend, bonus share, rights issue, or other mechanical share/price-basis event is resolved over `Open_(t+1) -> Close_(t+5/t+10)`.

V4-2 requires an unresolved mechanical discontinuity to become `PRICE_CONTINUITY_UNRESOLVED`, not a computed return.

Existing Corporate Action evidence is not a market-wide effective-date ledger: `TanggalPencatatan` has explicitly not been promoted to generic market-effective semantics, and bounded KSEI/IDX publication-linkage work remains incomplete. Therefore the target code must consume explicit continuity evidence and fail closed; it may not infer effective dates from price jumps or provider-adjustment behavior.

Verdict:

`V4_3_PREFIT_RUNTIME_ACCEPTED_EXECUTION_CODE_AND_CA_CONTINUITY_STILL_BLOCK_TARGET_ACCESS`
