# Forward CA Attestation V1 — Handoff

reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
branch: `integration/forward-ca-attestation-v1`
base_branch: `research/idx-v4-x1-decision-v1`
base_commit: `776ec2d5518a8a340ba01668191dd99f257d6d8d`
status: `PREPARED_CALENDAR_SCHEMA_PROBE_REQUIRED`
owner: `ChatGPT/Forward-CA-Attestation`

## Scope

Prepare prospective, outcome-blind, direct-IDX corporate-action attestation required by paper Execution V1.

Primary acquisition transport is pinned `nichsedge/idx-bei@75d6c0f74fa360d225794c70c383348977de6798`. The provider runs in its own uv/Python environment. IDX-Trade consumes only immutable raw response artifacts/manifests and performs offline attestation logic.

## Hard boundaries

- no V4-X1 alpha/model changes;
- no Decision V1 changes;
- no Sizing/Execution rule changes in this preparation;
- no historical CA backfill;
- no historical PnL;
- no protected/prospective outcome access;
- no paper fill/state mutation;
- no automatic Zapi fallback;
- no corporate-action accounting transformation yet.

## Current blocker before promotion

`Home/GetCalendar` direct-IDX response schema must be bounded-probed and its structural fingerprint independently reviewed/frozen. Until that happens, `EXPECTED_CALENDAR_SCHEMA_FINGERPRINT=None` intentionally prevents final `NO_RELEVANT_EVENTS` attestation generation.

## Prepared entry points

- provider setup: `scripts/setup_idx_bei_forward_ca_provider.ps1`
- direct capture: `scripts/capture_forward_ca_idx_bei.py`
- offline merge/attestation CLI: `scripts/build_forward_ca_attestation_v1.py`
- core verifier/classifier: `src/idx_trade/forward_ca_attestation_v1.py`
- config: `config/forward_ca_attestation_v1.json`
- checkpoint: `docs/checkpoints/2026-08-21_FORWARD_CA_ATTESTATION_V1_PREPARATION.md`

## Next authorized action

Run exactly one bounded calendar-schema probe through the pinned provider checkout. Do not schedule recurring capture or admit CA attestations to Execution V1 until the probe is reviewed and the schema fingerprint is frozen.
