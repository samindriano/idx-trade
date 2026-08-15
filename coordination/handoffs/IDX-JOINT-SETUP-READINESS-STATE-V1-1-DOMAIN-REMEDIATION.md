# Handoff — Joint Setup Readiness State V1.1 Domain Remediation

from: Codex/Joint-Setup-Readiness
to: ChatGPT independent review
task_id: IDX-JOINT-SETUP-READINESS-STATE-V1-1-DOMAIN-REMEDIATION
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 3ad481cc4b371f5022742101a12f6b9d603481a4
branch: research/idx-joint-setup-readiness-state-v1-1-domain-remediation
head_commit: 471287c (implementation/documentation push commit; branch HEAD may include later metadata-only synchronization)

## Scope

Implement the V1.1 applicability contract only. Keep accepted Foreign Flow
and Price State parent modules and formulas byte-identical. Treat Price State
keys as the authoritative domain, require `price_keys <= foreign_flow_keys`,
allow and record Foreign-Flow-only keys, and do not create a runtime joint
artifact.

## Files changed

* `src/idx_trade/joint_setup_readiness_state_v1_1.py`
* `tests/test_joint_setup_readiness_state_v1_1.py`
* `docs/checkpoints/2026-08-16_JOINT_SETUP_READINESS_V1_1_DOMAIN_REMEDIATION.md`
* this handoff

## Decisions and findings

* V1.1 fingerprint:
  `c1bd084dfe54dacd447ee15915e5210e539cfc99b19f42f1543bfa3f1801d5de`.
* Real 2026-08-13 parent audit is
  `JOINT_REAL_PARENT_DOMAIN_COMPATIBLE`.
* Foreign Flow keys: `963`.
* Price State keys: `836`.
* overlap: `836`.
* Price-only keys: `0`.
* Foreign-Flow-only excluded keys: `127`; exact identities are recorded in
  the dated checkpoint.
* In-memory output domain: exactly `836` rows.
* source-session mismatch: `0`.
* in-memory state distribution: `IGNORE=697`, `WATCH=84`, `READY=54`,
  `ENTRY_ELIGIBLE=1`.

## Parent provenance

Foreign Flow Setup State artifact SHA:
`b8791011659b33c62cf0890340e86de4abfb397eaa1b99c3639a6c240b682284`.

Foreign Flow Setup State manifest SHA:
`3c94eede15c35e4997643ef931538779940d6839136f7afca4b819402f17caed`.

Price State artifact SHA:
`8dab4a1d532c42cb46f9a9b86c5f853f99f00e13677222c7ae1e1ab0ca1901af`.

Price State manifest SHA:
`aad51b933ba8a8868c050e17fec52330a3b6c66002ba29d0ddd4ba84949cbd6f`.

Bridge calendar SHA:
`51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`.

## Boundaries

No provider calls, scheduler/counter/O2 changes, model/scoring, protected
outcome access, trade recommendation, parent formula/threshold changes,
runtime joint artifact, or Repository Hygiene work occurred.

## Validation

Focused V1 + V1.1 tests: `22 passed`.

Full pytest: `61 passed, 1 failed, 62 collected`. The only failure is the
known unrelated `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
expectation; storage independently reports `raw_close` and `vendor_adj_close`
conflicts (2), while the old test expects 1. Storage was not changed.

`git diff --check`: PASS.

recommended_next_action: independent review of V1.1 contract and real-parent
domain audit; do not wire prospective runtime until accepted.
