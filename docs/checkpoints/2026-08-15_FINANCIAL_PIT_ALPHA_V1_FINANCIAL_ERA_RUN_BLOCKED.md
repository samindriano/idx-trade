# Financial PIT Alpha V1 — Financial-era run blocked by runner defect

Status: `FINANCIAL_PIT_ALPHA_V1_FINANCIAL_ERA_RUN_BLOCKED_ENGINEERING_REAUTH_REQUIRED`

The frozen Financial-era contract was valid and the one authorized historical
run began after all outcome-blind preflight checks passed. The run then stopped
on an engineering defect before it could persist metrics, predictions, a
summary, or a result manifest.

## Frozen inputs and authorization

- Branch: `research/idx-financial-pit-alpha-v1`
- Financial-era contract status:
  `FINANCIAL_PIT_ALPHA_V1_FINANCIAL_ERA_CONTRACT_FROZEN`
- Contract SHA-256:
  `cabeb0db3db44996bda91472576855cb549965d19791f640717502cdd321993c`
- Eligible folds: exactly `V2F4`, `V2F5`, `V2F6`
- Clean V2 common-support SHA-256:
  `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`
- Historical H10 label source SHA-256:
  `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`
- Financial support key SHA-256:
  `b1257db0a2fc175aab010f1ab1a925e3c7d949b43fe1dd332874382fd09ec00d`
- Fresh-forward/O2/protected forward outcomes: untouched

## Failure

The runner completed label loading and model fitting for the nine expected
fold/candidate combinations (three candidates × F4–F6), then failed during
same-fold prediction-identity verification:

`KeyError: ('ticker', 'date', 'signal_session_index')`

Cause: pandas interprets a tuple passed to `DataFrame[...]` as one key rather
than a list of columns. The bounded engineering correction changes that access
to `DataFrame[list(KEY_COLUMNS)]`. No feature, fold, target, preprocessing,
hyperparameter, or gate semantics changed.

No performance metric, paired delta, survivor gate, or verdict is valid from
this run. The run is considered consumed because labels were accessed and
models were fit under the frozen contract.

## Preserved partial artifacts

External output root:

`D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-financial-era-run`

It contains 9 fold-model files under `fold_models/`. The runner did not write
`fold_metrics.csv`, `predictions.parquet`, `aggregate_metrics.csv`,
`summary.json`, `artifact_manifest.json`, or `artifact_manifest.sha256`.
The partial output is preserved and was not overwritten or deleted.

## Validation after correction

- Focused Financial Alpha + historical-run tests: `10 passed`.
- Full pytest: `61 passed, 1 failed`.
- The only failure remains the unrelated legacy
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflict`;
  current storage semantics report independent `raw_close` and
  `vendor_adj_close` conflicts while that old fixture expects one.
- `git diff --check`: passed.

## Decision boundary

This checkpoint does not produce `FINANCIAL_PIT_ALPHA_V1_SURVIVOR` or
`FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR`. A new explicit authorization is required
before rerunning the same frozen historical experiment with the engineering
correction. No alternate folds, candidate, support threshold, or gate may be
introduced.
