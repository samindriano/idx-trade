# Joint Setup Readiness V1.1 Prospective Runtime Adapter

Status: `JOINT_SETUP_READINESS_V1_1_CONTROLLED_SMOKE_VERIFIED`

Branch: `integration/joint-setup-readiness-v1-1-forward-v1`

Accepted domain parent:
`research/idx-joint-setup-readiness-state-v1-1-domain-remediation@af2450c7e5166dba853a810ee77ebdc339198dc7`

Frozen V1.1 fingerprint:
`c1bd084dfe54dacd447ee15915e5210e539cfc99b19f42f1543bfa3f1801d5de`

## Controlled smoke

Command:

```text
python -m idx_trade.joint_setup_readiness_v1_1_runtime --runtime-root D:\Documents\Project\idx-trade-data-gate-20260808v
```

Source session: `2026-08-12`.

Feature session: `2026-08-13`.

Output namespace:

```text
D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\joint_setup_readiness_state_v1_1\2026-08-13\
```

The first run created the immutable pair. The one permitted replay returned
`created=false`; artifact and manifest hashes were unchanged.

* status: `JOINT_SETUP_READINESS_V1_1_CONTROLLED_SMOKE_VERIFIED`
* artifact:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\joint_setup_readiness_state_v1_1\2026-08-13\joint_setup_readiness_state_v1_1.parquet`
* artifact SHA-256:
  `d83593b61a25f9f32a82c153001e0c548f29ffb255485b29a84760ae6ae03418`
* manifest:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\joint_setup_readiness_state_v1_1\2026-08-13\joint_setup_readiness_state_v1_1.manifest.json`
* manifest SHA-256:
  `c3007af5af3061ee91be176fb0d29dc000cfc162fcc0c3642c5f26723646d646`
* rows/tickers: `836 / 836`
* first created: `true`
* replay created: `false`
* strict verification: `true`

## Parent revalidation

The adapter re-hashed actual bytes before materialization and on replay. It
did not trust declarations alone.

Foreign Flow Setup parent:

* artifact SHA-256:
  `b8791011659b33c62cf0890340e86de4abfb397eaa1b99c3639a6c240b682284`
* manifest SHA-256:
  `3c94eede15c35e4997643ef931538779940d6839136f7afca4b819402f17caed`
* contract: `FOREIGN_FLOW_SETUP_STATE_V1`
* status: `FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY`

Price State parent:

* artifact SHA-256:
  `8dab4a1d532c42cb46f9a9b86c5f853f99f00e13677222c7ae1e1ab0ca1901af`
* manifest SHA-256:
  `aad51b933ba8a8868c050e17fec52330a3b6c66002ba29d0ddd4ba84949cbd6f`
* contract: `PRICE_TREND_CONFIRMATION_STATE_V1`
* status: `PRICE_TREND_CONFIRMATION_STATE_V1_FORWARD_READY`

The strict verifier reopens both parents, verifies path and byte hashes,
manifest status/contract/session/flags, duplicate-free keys, parent schema,
source-to-feature causality, V1.1 domain reconciliation, output schema/rows,
state distribution, contract fingerprints, provenance fingerprint, and output
artifact/manifest hashes.

## Domain and state result

| Domain | Count |
|---|---:|
| Foreign Flow keys | 963 |
| Price State authoritative keys | 836 |
| overlap | 836 |
| Price-only | 0 |
| Foreign-Flow-only excluded | 127 |

The exact 127 excluded identities are persisted in the runtime manifest under
`domain.foreign_flow_only_keys`. All have `feature_session=2026-08-13`.

State distribution:

* `IGNORE=697`
* `WATCH=84`
* `READY=54`
* `ENTRY_ELIGIBLE=1`

`ENTRY_ELIGIBLE` remains descriptive context only. No trade recommendation is
produced.

## Validation

Focused V1/V1.1/runtime tests: `33 passed`.

Full pytest: `72 passed, 1 failed, 73 collected`. The only failure is the
known unrelated
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`:
the storage contract reports independent `raw_close` and
`vendor_adj_close` conflicts (2), while the old test expects 1. Storage was
not changed.

`git diff --check`: PASS.

Before the successful smoke, one runner-only comparison bug was corrected: the
frozen domain expectation now compares count fields while retaining the full
identity lists in provenance. That failed before any runtime output was
written; the focused suite was rerun and passed before the successful smoke.

Protected flags in the final manifest are explicit:

```text
provider_calls=0
outcome_blind=true
forward_outcomes_accessed=false
outcomes_or_labels_accessed=false
model_fitted=false
model_scoring=false
trade_recommendation=false
```

No scheduler integration, O2/counter change, provider/network call, outcome or
performance access, model fit/scoring, threshold/mapping change, or
Repository Hygiene work occurred.

