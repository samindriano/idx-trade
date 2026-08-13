# Clean V2 Open Alpha — Atomic Historical Run

Date: 2026-08-13 (Asia/Jakarta)
Status: **HISTORICAL_RUN_COMPLETE_PENDING_INDEPENDENT_REVIEW**
Branch: `research/idx-v2-open-alpha-prereg-v1`
Authorization: `review/idx-v2-open-alpha-prereg-remediation-acceptance-v1@cede829`

## Scope and stop boundary

This is the single authorized historical-development comparison after the
outcome-blind remediation. It fit and scored exactly CONTROL, V2.1, and V2.2
on the accepted common-support population and six frozen V2 folds. No 31-feature
combined candidate, tuning, rescue, final refit, canonical promotion, provider
call, or fresh-forward outcome access was performed. The run stops here for
ChatGPT review.

## Frozen inputs and model identities

- common-support rows: **277,244** / **729** tickers;
- common-support key SHA-256: `e058e5ce4ce650eeab5acd57a7d697c155548e40bbbb8ffe0eab120987d857df`;
- common-support parquet SHA-256: `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`;
- clean-V2 H10 label source SHA-256: `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`;
- every common-support identity joined to exactly one frozen H10 label;
- historical boundary: 2026-07-31;
- HGB preprocessing: median imputation with missing indicators, keeping empty
  features, numeric-only ColumnTransformer;
- HGB parameters: learning_rate=0.05, max_iter=200, max_leaf_nodes=31,
  l2_regularization=1.0, random_state=42;
- folds: V2F1 through V2F6 with the frozen 20-session purge and 100-session
  validation windows.

| model | features | feature-order SHA-256 |
|---|---:|---|
| CONTROL_CLEAN_V2_HGB_XS_MARKET | 25 | `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72` |
| V2.1_CLEAN_V2_OPEN_GEOMETRY | 28 | `9bf62fd9fec1edeaebd7b3024512f942fcef9c7d12dd01797f2c2020bf636c34` |
| V2.2_CLEAN_V2_PREVIOUS_RANGE_OPEN_DISPLACEMENT | 28 | `228c3afad2d4f786923c480e9b91be0467a646b08e770097552c8905dd30ff74` |

The 31-feature all-six-Open concatenation remained **PROHIBITED**.

## Per-fold metrics

Values are PR-AUC, PR-AUC minus prevalence, ROC-AUC, Q5-Q1, and top-decile
lift respectively.

| model | fold | rows | PR-AUC | PR-AUC-prevalence | ROC-AUC | Q5-Q1 | top-decile lift |
|---|---|---:|---:|---:|---:|---:|---:|
| CONTROL | V2F1 | 21,478 | 0.402509 | 0.022445 | 0.528588 | 0.064880 | 0.027783 |
| CONTROL | V2F2 | 20,023 | 0.404377 | 0.016822 | 0.518619 | 0.058739 | 0.026627 |
| CONTROL | V2F3 | 20,244 | 0.418413 | 0.004562 | 0.527633 | 0.043184 | 0.022170 |
| CONTROL | V2F4 | 20,159 | 0.425622 | 0.041228 | 0.509210 | 0.033076 | 0.009088 |
| CONTROL | V2F5 | 25,179 | 0.495203 | 0.033033 | 0.536896 | 0.055060 | 0.042899 |
| CONTROL | V2F6 | 32,986 | 0.353070 | 0.016564 | 0.491028 | 0.047170 | 0.027266 |
| V2.1 | V2F1 | 21,478 | 0.413521 | 0.033458 | 0.534352 | 0.073635 | 0.041013 |
| V2.1 | V2F2 | 20,023 | 0.407912 | 0.020358 | 0.523393 | 0.068406 | 0.029561 |
| V2.1 | V2F3 | 20,244 | 0.417128 | 0.003277 | 0.527165 | 0.041552 | 0.030379 |
| V2.1 | V2F4 | 20,159 | 0.427055 | 0.042661 | 0.514540 | 0.040762 | 0.008602 |
| V2.1 | V2F5 | 25,179 | 0.492292 | 0.030122 | 0.528053 | 0.043158 | 0.035879 |
| V2.1 | V2F6 | 32,986 | 0.346273 | 0.009767 | 0.493189 | 0.043534 | 0.022476 |
| V2.2 | V2F1 | 21,478 | 0.406674 | 0.026611 | 0.530076 | 0.068684 | 0.034626 |
| V2.2 | V2F2 | 20,023 | 0.405094 | 0.017539 | 0.520220 | 0.074662 | 0.034451 |
| V2.2 | V2F3 | 20,244 | 0.419821 | 0.005970 | 0.528672 | 0.043922 | 0.024585 |
| V2.2 | V2F4 | 20,159 | 0.418777 | 0.034383 | 0.501701 | 0.032065 | 0.023193 |
| V2.2 | V2F5 | 25,179 | 0.495085 | 0.032914 | 0.533975 | 0.057285 | 0.038609 |
| V2.2 | V2F6 | 32,986 | 0.349900 | 0.013393 | 0.488094 | 0.040076 | 0.016188 |

## Frozen paired gates

| comparison | median PR delta | q25 PR delta | positive folds | guardrail reversal | gate |
|---|---:|---:|---:|---|---|
| V2.1 vs CONTROL | +0.00007359 | -0.00250461 | 3/6 | false | FAIL |
| V2.2 vs CONTROL | +0.00029955 | -0.00240718 | 3/6 | false | FAIL |
| V2.1 vs V2.2 | +0.00006266 | -0.00276790 | 3/6 | false | FAIL |
| V2.2 vs V2.1 | -0.00006266 | -0.00583964 | 3/6 | false | FAIL |

Both challengers fail the frozen q25 paired-improvement requirement. The
deterministic verdict is:

**`RETAIN_CLEAN_V2`**

This is a historical-development result only; it does not promote or refit a
canonical model and does not authorize forward validation.

## External runtime artifacts

Runtime root (kept outside Git):
`D:\Documents\Project\idx-trade-data-gate-20260808v\open_alpha_historical_v1_20260813_001`

- summary SHA-256: `23d37a6c95cc7ae11f0eca6a745d9077622e809e012dc77b232d0d1adb0e3186`;
- predictions SHA-256: `21bf24d4c9bb8d10775edaaf10175013482fadb1bdd8a09df793b8fec7c68040`;
- fold metrics SHA-256: `dc0b3c876205a0d8d39aeb53fdf2ac9c852e57be4b4bbc67920e62029b6c41c9`;
- aggregate metrics SHA-256: `2df0b6afbd453d361c28224d66d13a4aeaa1aa0637d282158e59a9a5df94a090`;
- survivor decision SHA-256: `1478ae50eb25618cfe6b7b44cdb3b52cd972b7f2bc482507f37d5c45d07af500`;
- artifact manifest SHA-256: `f0b8a0a0f15655a3663084a4ecc988320b320f1ec63b5589262ac40e9893f97e`;
- artifact count: 28, including 18 fold-local model artifacts.

## Validation and stop state

- focused tests: **12 passed**;
- full pytest: **51 passed, 1 pre-existing failure** in
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  (the existing storage helper reports two revision conflicts while the test
  expects one; storage was not changed in this lane);
- no provider/network calls;
- no protected fresh-forward outcomes;
- no canonical model/counter change;
- no final refit, tuning, or promotion.

Stop for independent ChatGPT review. Do not automatically start another
experiment, refit, promote, tune, or open fresh-forward outcomes.
