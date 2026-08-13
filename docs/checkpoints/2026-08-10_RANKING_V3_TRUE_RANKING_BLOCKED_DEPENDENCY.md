# Ranking V3-E True-Ranking - Dependency Block

Date: 2026-08-10 (Asia/Jakarta)

Status: **BLOCKED_DEPENDENCY**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

Pre-run HEAD: `8f58b4884c6f4c7d45766737935c8fd1a9568e58`

## Scope

This checkpoint records the pre-outcome environment gate for the frozen V3-E
True-Ranking run. The exact XGBoost dependency could not be installed in the
local environment, so the run stopped before frozen-artifact materialization
and before any outcome-bearing control or LambdaMART execution.

## Dependency result

- required: `xgboost==3.2.1`;
- installed/imported: `xgboost==3.1.3`;
- attempted command: `python -m pip install --upgrade --force-reinstall xgboost==3.2.1`;
- result: both the configured package index and public PyPI reported no
  matching `3.2.1` distribution (they expose `3.2.0` and then `3.3.0`, but
  not `3.2.1`);
- no substitute XGBoost version or ranking library was installed.

Decision: `BLOCKED_DEPENDENCY`.

## Full pytest

The full suite was run explicitly from the IDX Trade repo root after the
failed exact-version installation attempt:

```text
306 passed, 1 failed, 3 warnings in 22.8s
```

The only failure was the frozen dependency guard:

```text
tests/test_ranking_v3_true_ranking.py::test_lambdamart_parameter_contract
RuntimeError: V3-E requires xgboost==3.2.1, actual=3.1.3
```

The three warnings are the existing pandas FutureWarnings in curated identity
and tradability-anchor tests.

## Protected boundary

Because the dependency gate failed:

- V3-E prepared rows were not materialized;
- V2 prepared table, V2 manifest, V2 reference summary, and V2 reference
  predictions were not read for the run;
- exact V2 control was not executed;
- LambdaMART ordinal 011 was not executed or interpreted;
- no V3-E output directory or model/prediction/metric artifact was created;
- ordinals 010/011 remain `result_viewed=false` and cumulative evaluated count
  remains `7`;
- V3-D remains parked at `BLOCKED_PIT_SECTOR_HISTORY`;
- V2F5/V2F6 and reserved post-2026-07-31 fresh-forward outcomes were not
  accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written;
- integration, calibration, Stage 6, IDX-VAL-002, execution/PnL, paper/live,
  and main merge were not started.

## Required unblock

Provide a Python environment/package index containing the exact frozen
`xgboost==3.2.1` wheel compatible with this runtime. Then rerun the full
pytest gate and only after it passes resume the unchanged V3-E run handoff.
