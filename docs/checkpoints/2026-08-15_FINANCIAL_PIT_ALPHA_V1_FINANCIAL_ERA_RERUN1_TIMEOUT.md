# Financial PIT Alpha V1 — exact rerun stopped by execution timeout

Status: `FINANCIAL_PIT_ALPHA_V1_RERUN_TOOL_TIMEOUT_RESULT_UNDETERMINED_REVIEW_REQUIRED`

This checkpoint records the single reauthorized exact-contract rerun. The
scientific result is undetermined because the execution wrapper timed out
before the frozen three-fold run completed.

## Preflight

- Branch HEAD: `507aaf8bca3286996eb30f3f8e7ea161d8892cc1`
- Contract SHA-256:
  `cabeb0db3db44996bda91472576855cb549965d19791f640717502cdd321993c`
- Exact eligible folds: `V2F4`, `V2F5`, `V2F6`
- Support: 70,520 rows / 321 tickers
- Clean V2 support SHA-256:
  `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`
- Selected Financial matrix SHA-256:
  `464c2a18bd7b238f98c786365026466bfd52c514022b3ced09798b2654665471`
- Historical H10 label SHA-256:
  `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`

All preflight checks passed before the rerun began.

## Rerun status

Output root:

`D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-financial-era-rerun1`

The command ended with tool timeout `exit 124` after approximately 124
seconds. Read-only inspection found six model artifacts: all three frozen
candidates for `V2F4` and `V2F5`. `V2F6` had not completed.

No `fold_metrics.csv`, `predictions.parquet`, `aggregate_metrics.csv`,
`summary.json`, `artifact_manifest.json`, or `artifact_manifest.sha256` exists
in the rerun directory. Therefore no metrics, paired deltas, survivor gate, or
verdict are valid or reported.

The prior failed-run directory remains untouched and read-only:
`D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-financial-era-run`.

## Boundaries

The rerun used the exact frozen folds, support, features, HGB parameters,
preprocessing, and gate. No third run is started automatically. No canonical
refit/promotion, O2, fresh-forward, or protected-forward outcome was accessed.

## Validation and decision

The latest executable validation before this rerun was:

- focused Financial Alpha tests: `10 passed`;
- full pytest: `61 passed, 1 failed`, the unrelated legacy storage conflict
  expectation;
- `git diff --check`: passed.

The outcome is `UNDETERMINED_EXECUTION_TIMEOUT`, not survivor or no-survivor.
A further rerun requires explicit authorization and a runtime allowance that
can complete the unchanged F4–F6 contract.
