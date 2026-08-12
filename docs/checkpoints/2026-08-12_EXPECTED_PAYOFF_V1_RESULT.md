# Expected Payoff V1 Historical Experiment Result

Date: 2026-08-12 (Asia/Jakarta)

Branch: `research/idx-expected-payoff-v1`

Frozen specification: `a5f2ae154505ecc2c3a182711c0900afe38d1759`

## Decision

`EXPECTED_PAYOFF_V1_NO_SURVIVOR`

The frozen single candidate was evaluated once after the preflight and test
gates passed. The data-readiness gate passed, but the model-survivor gate did
not: the HGB payoff regressor improved the training-mean MSE baseline in only
1/6 folds and its median MSE skill was negative. The positive payoff-ordering
diagnostics do not override the mandatory MSE gate.

No rescue candidate, alternate loss/horizon, tuning, provider call, O2
rescore, forward outcome access, or fresh-forward marker was used.

## Frozen inputs and population

- Candidate: `PAYOFF_HGB_O2_FEATURES_V1`.
- Model: `HistGradientBoostingRegressor` with the frozen squared-error,
  learning-rate, 200-iteration, 31-leaf, L2=1, early-stopping-off,
  random-state-42 contract; median imputer with missing indicators fit within
  each training fold only.
- Features: exact 36-column V1 order (the accepted V3-B 33 features followed
  by `open_position`, `open_to_high`, `open_to_low`). Feature-order SHA:
  `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`.
- Target: accepted V0 `Open(t+1)` to raw `Close(t+10)`, normalized by the
  signal-date ATR14, with the same corporate-action and tradability rules.
- Accepted V0 validation rows consumed exactly: `140,595`.
- Validation key SHA: `f978ec6b81ddc72259e403e78698971f655721f94fbfdcc57f682c5cea3c4602`.
- Validation range: 2023-06-23 through 2026-06-10; six folds, 100 eligible
  signal sessions per fold, and all validation predictions finite.
- Resolved training rows across folds: `997,902`.
- Fold training target coverage: 99.3146%, 99.4311%, 99.5143%, 99.5725%,
  99.6080%, and 99.6557% for V2F1 through V2F6 respectively.

The exact parent artifacts were verified against the frozen hashes, including
the O2 manifest and predictions, common-support CSV/key identity, V2 prepared
table, official calendar, PIT security master, model-safe panel, accepted Open
panel/provenance, tradability anchors, corporate-action evidence, and V3-B
training table/manifest.

## Fold metrics

| Fold | Train rows | Validation rows | MSE skill vs train mean | Median session IC | Q25 IC | O2 contextual median IC | Mean D10-D1 ATR | Positive ordering |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V2F1 | 103,611 | 21,478 | -0.017863 | 0.070351 | 0.008143 | 0.0570728 | 0.596744 | yes |
| V2F2 | 129,152 | 20,046 | -0.094154 | 0.021819 | -0.028806 | 0.0526684 | 0.259721 | no (Q25 IC) |
| V2F3 | 153,661 | 20,261 | -0.101781 | 0.010541 | -0.056057 | 0.0358517 | 0.224503 | no (Q25 IC) |
| V2F4 | 177,701 | 20,178 | -0.022561 | 0.026770 | -0.022003 | 0.0042570 | 0.040763 | no (Q25 IC) |
| V2F5 | 202,249 | 25,345 | -15.213322 | 0.030192 | -0.032423 | 0.0324746 | -0.787390 | no (MSE/spread) |
| V2F6 | 231,528 | 33,287 | +0.462149 | -0.026647 | -0.077810 | 0.0490883 | 0.038350 | no (IC/spread) |

Aggregate gate values:

- Data-ready: PASS.
- Median MSE skill: `-0.0583575301`; positive MSE-skill folds: `1/6`.
- Median V1 session IC: `0.0242940252`; Q25: `0.0133601230`; positive folds:
  `5/6`.
- Median D10-D1 ATR spread: `0.1326330936`; positive folds: `5/6`.
- MSE survivor gate: FAIL. IC gate: PASS. D10-D1 gate: PASS.
- Final frozen verdict: `EXPECTED_PAYOFF_V1_NO_SURVIVOR`.

The result means the features contain some out-of-sample payoff ordering
signal, but this particular mean-payoff model is not a reliable conditional
mean estimator under the required MSE-baseline contract. Do not reinterpret
it as a license to tune or try another model in this lane.

## Artifacts and tests

Runtime output is external and was not committed:

`D:\Documents\Project\idx-trade-data-gate-20260808v\expected_payoff_v1_20260812_002`

- Artifact manifest SHA-256:
  `8f6a082016828bbd146b7ddfdf4d90ed0c4feedb946187dd2080aefdeeab63e2`.
- Manifest contains 21 hashed non-manifest artifacts and six fold model hashes.
- Validation parquet row count: 140,595; duplicate validation keys: 0.
- Runtime flags: fresh-forward false; marker false; provider calls false; O2
  modified false; O2 rescored false; hyperparameter search false; candidate
  count 1.

Focused V1 tests: `8 passed`.

Full IDX-Trade pytest: `62 passed, 0 failed, 0 warnings, 5.66s`.

The first full-suite command was discarded because PowerShell retained the
Project parent directory and collected unrelated repositories; the corrected
explicit worktree run above is the authoritative result.
