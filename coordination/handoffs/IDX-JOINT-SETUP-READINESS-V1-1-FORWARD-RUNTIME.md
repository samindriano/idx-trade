# Handoff — Joint Setup Readiness V1.1 Prospective Runtime Adapter

from: Codex/Joint-Setup-Readiness
to: ChatGPT independent review
task_id: IDX-JOINT-SETUP-READINESS-V1-1-FORWARD-RUNTIME
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: af2450c7e5166dba853a810ee77ebdc339198dc7
branch: integration/joint-setup-readiness-v1-1-forward-v1
scope: one controlled outcome-blind V1.1 runtime materialization plus strict replay verification

## Result

Final status:
`JOINT_SETUP_READINESS_V1_1_CONTROLLED_SMOKE_VERIFIED`

Source session: `2026-08-12`.

Feature session: `2026-08-13`.

Artifact SHA-256:
`d83593b61a25f9f32a82c153001e0c548f29ffb255485b29a84760ae6ae03418`.

Manifest SHA-256:
`c3007af5af3061ee91be176fb0d29dc000cfc162fcc0c3642c5f26723646d646`.

Rows/tickers: `836 / 836`.

First materialization created the pair; one replay returned `created=false`
with stable artifact and manifest hashes.

## Domain

Foreign Flow: `963`; Price State authoritative domain: `836`; overlap: `836`;
Price-only: `0`; Foreign-Flow-only excluded: `127`. Exact excluded identities
are in the runtime manifest and dated checkpoint.

State distribution: `IGNORE=697`, `WATCH=84`, `READY=54`,
`ENTRY_ELIGIBLE=1`.

Frozen V1.1 fingerprint:
`c1bd084dfe54dacd447ee15915e5210e539cfc99b19f42f1543bfa3f1801d5de`.

## Validation

Focused tests: `33 passed`.

Full pytest: `72 passed, 1 failed, 73 collected`; only the known unrelated
storage revision-conflict expectation fails (`raw_close` and
`vendor_adj_close` are intentionally independent conflicts). Storage was not
changed.

`git diff --check`: PASS.

## Boundaries

No provider/network call, scheduler integration, O2/counter change, model fit
or scoring, outcome/performance access, threshold/mapping change, trade
recommendation, or Repository Hygiene work occurred.

recommended_next_action: independent review of the runtime adapter and the
immutable 2026-08-13 joint artifact; no scheduler integration yet.

