# V4-3R CA80 historical one-shot code seal — 2026-08-19

Status: `V4_3R_HISTORICAL_ONE_SHOT_CODE_FROZEN_LOCAL_VALIDATION_PENDING`

## Authorization lineage

The V4-3R outcome-blind support gate passed before historical target access:

- prefit manifest SHA-256: `0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc`;
- support gate: `0.80`;
- frozen validation dates: `600/600` eligible;
- frozen support buckets: `<0.80 = 0`, `[0.80,0.90) = 541`, `>=0.90 = 59`;
- all 12 fold/head training sets non-empty;
- historical target/model/performance access remained false.

The local execution-freeze capture then passed:

- status: `V4_3R_EXECUTION_FREEZE_CAPTURED_HISTORICAL_EXECUTION_AUTHORIZED`;
- execution-freeze manifest SHA-256: `328713245465e0b5bb434bb4b4fd1bfdce4d8a19b419ac198446de2eb13811be`;
- historical target/model/performance remained false;
- protected-forward access remained false.

## Historical one-shot code seal

The branch now contains:

- `config/ranking_v4_3r_historical_execution_v1.json`;
- `src/idx_trade/ranking_v4_3r_model_eval.py`;
- `scripts/run_v4_3r_historical_one_shot.py`;
- `tests/test_ranking_v4_3r_model_eval.py`;
- `tests/test_v4_3r_historical_one_shot_contract.py`.

The inherited V4-3 target, feature, learner, evaluator, fold, metric, and promotion implementation blobs remain unchanged. The V4-3R evaluator overlay changes only the separately preregistered date-level target-coverage gate from `0.90` to `0.80`; the inherited `ranking_v4_3_model_eval.py` blob remains untouched.

The historical runner is pinned to:

- V4-3R preregistration blob;
- inherited V4-3 preregistration/target/features/model-eval blobs;
- V4-3R CA80 evaluator-overlay blob;
- exact accepted Python/package runtime;
- execution-freeze manifest `328713...11be`;
- prefit manifest `0c222a...cfcc`;
- final outcome-blind combined CA replay manifest `12d60b...b2f43`;
- frozen 600 validation identity SHA `91fe0e...cd915`;
- exact historical market/Open/security-master input hashes already used by the accepted V4 support lineage.

## First historical access semantics

The runner creates `HISTORICAL_ACCESS_BOUNDARY.json` immediately before calling `materialize_v4_target_ledger`. Once that marker exists, the generation is outcome-open even if a later assertion or fit fails. The output root is no-overwrite, so a failed post-access run cannot be silently retried under the same generation.

After materializing targets, but before any model fit, the runner requires exact row-level parity between actual H5/H10/consensus target availability and the already-frozen outcome-blind support booleans. Any mismatch stops the run before model fitting.

If parity passes, the one-shot execution performs exactly:

- 6 folds;
- H5 and H10 heads;
- Control and Challenger modes;
- 24 total fits;
- full frozen validation scoring population;
- consensus alpha = `0.5 * H5 alpha + 0.5 * H10 alpha`;
- unchanged Top30/no-refill semantics;
- unchanged absolute viability gates;
- unchanged paired incremental promotion gates;
- unchanged 2,000-replication fold-stratified block bootstrap.

## Decision rule

No post-result interpretation is allowed to change the preregistered decision rule:

1. Challenger passes absolute viability and all incremental gates -> `V4_3R_CHALLENGER_PROMOTED_FOR_FRESH_PROSPECTIVE_CONFIRMATION`;
2. otherwise, if Control passes absolute viability -> `V4_3R_CONTROL_RETAINED`;
3. otherwise -> `V4_3R_GENERATION_NO_SURVIVOR`.

A historical promotion is not deployment and still requires fresh prospective confirmation. Protected-forward outcomes remain locked.

## Required local validation before first target access

Run syntax and focused synthetic/contract tests on a clean checkout. Do not run the historical one-shot if any test fails. No threshold, feature, learner, fold, metric, or promotion-rule fix may be made after historical access begins; any material scientific change after that boundary requires a separately preregistered generation.

The original V4-3 >=90% generation remains failed and closed. V4-3R must always be reported as the separately preregistered CA80 generation because 541/600 frozen validation dates lie below the original 90% support threshold.
