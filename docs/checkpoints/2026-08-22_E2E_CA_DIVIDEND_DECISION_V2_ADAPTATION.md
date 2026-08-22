# E2E Baseline Paper V1 — CA/Dividend Decision V2 Adaptation

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`

## Scope

Selective transplant of the validated forward corporate-action and cash-dividend foundation into the current E2E paper lane.

Pinned source:

`9ba619916c37d28121c39f61148ab0d03ac21bf0`

No wholesale merge of the historical CA branch was performed.

## Verbatim transplanted components

The following files were verified byte-identical to the pinned source:

- `src/idx_trade/forward_ca_attestation_v1.py`
- `src/idx_trade/forward_dividend_execution_v1_1.py`
- `src/idx_trade/forward_dividend_v1.py`
- `tests/test_forward_ca_attestation_v1.py`
- `tests/test_forward_dividend_execution_v1_1.py`
- `tests/test_forward_dividend_v1.py`

## Decision V2 adaptation

`forward_dividend_runtime_v1_1.py` was minimally adapted from legacy Decision V1 shadow state to frozen Decision V2 Minimal.

Paper-to-shadow invariant remains:

`actual positions - pending sells + pending buys`

The reconstructed state is now `DecisionV2ShadowState`, bound to:

`V4_X1_DECISION_V2_MINIMAL_V1`

The maximum shadow size comes from the frozen Decision V2 profile.

No dividend accounting, evidence-registry, entitlement, receivable, settlement, persistence, Sizing V1, or Execution V1 economics were changed.

## Validation

- baseline CA/dividend selective transplant: `43 passed`
- post-adaptation CA/dividend regression: `43 passed`
- Decision V2 / Sizing V1 / Execution V1 bridge regression: `27 passed`
- cross-layer dividend runtime: `15 passed`
- final combined Step 1-2 regression: `72 passed`
- `git diff --check`: PASS
- six verbatim transplant files matched pinned-source blob SHA exactly

Cross-layer coverage proves:

- reconstructed paper shadow is admitted by the non-bootstrap Decision V2 planner;
- shadow state above the frozen V2 position cap fails closed.

## Commit

Implementation checkpoint:

`79ec9ce452377719fbea6174daff3e44cab29061`

## Verdict

`E2E_CA_DIVIDEND_DECISION_V2_FOUNDATION_ACCEPTED`

This does not authorize live CA acquisition or unattended paper-state mutation from future corporate-action evidence.

Next phase:

real certified BBCA dividend lifecycle regression, then generic prospective CA/dividend acquisition.
