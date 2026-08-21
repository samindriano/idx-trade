# Forward CA Attestation V1 — Handoff

reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
branch: `integration/forward-ca-attestation-v1`
base_branch: `research/idx-v4-x1-decision-v1`
base_commit: `776ec2d5518a8a340ba01668191dd99f257d6d8d`
status: `CALENDAR_SCHEMA_PROBE_READY_EXECUTION_ADMISSION_STILL_BLOCKED`
owner: `ChatGPT/Forward-CA-Attestation`

## Scope

Prepare prospective, outcome-blind, direct-IDX corporate-action attestation required by paper Execution V1.

Primary acquisition transport is pinned `nichsedge/idx-bei@75d6c0f74fa360d225794c70c383348977de6798`. The provider runs in its own uv/Python environment. IDX-Trade consumes only immutable raw response artifacts/manifests and performs offline attestation logic.

## Hard boundaries

- no V4-X1 alpha/model changes;
- no Decision V1 changes;
- no historical CA backfill;
- no historical PnL;
- no protected/prospective outcome access;
- no paper fill/state mutation before promotion;
- no automatic Zapi fallback;
- no corporate-action quantity/cash transformation yet.

## Current gate before promotion

`Home/GetCalendar` direct-IDX response schema must be bounded-probed and its structural fingerprint independently reviewed/frozen. Until that happens, `EXPECTED_CALENDAR_SCHEMA_FINGERPRINT=None` intentionally blocks both final attestation promotion and the Execution V1 CA verifier.

The direct calendar parameter contract is independently corroborated as:
`range/date/start/length/code/language/search`, with `d/w/m` range values and response top-level `Results`.

## Prepared entry points

- provider setup: `scripts/setup_idx_bei_forward_ca_provider.ps1`
- one-request calendar probe: `scripts/probe_forward_ca_calendar_schema_v1.py`
- one-command Windows runner: `scripts/run_forward_ca_calendar_probe_v1.ps1`
- direct prospective capture: `scripts/capture_forward_ca_idx_bei.py`
- offline merge/attestation CLI: `scripts/build_forward_ca_attestation_v1.py`
- source verifier/classifier: `src/idx_trade/forward_ca_attestation_v1.py`
- Execution CA verifier: `src/idx_trade/v4_x1_execution_v1_verify.py`
- config: `config/forward_ca_attestation_v1.json`
- checkpoint: `docs/checkpoints/2026-08-21_FORWARD_CA_ATTESTATION_V1_PREPARATION.md`

## Hardening completed before live probe

- calendar capture changed from per-ticker weekly calls to one all-market monthly capture per calendar month touched by the decision-to-execution window;
- raw calendar JSON must contain non-empty `Results`;
- calendar structural fingerprint is recomputed from raw bytes by IDX-Trade and must equal the collector declaration;
- exact endpoint/content-type/raw SHA/source-chain checks are enforced;
- calendar RUPS/non-CA events do not block execution merely because the ticker appears; CA keyword + applicable date window are required;
- CA announcements published on the decision date are conservatively considered relevant;
- Execution V1 now verifies the complete Forward-CA source chain, provider pin, upstream, source manifest, raw hashes, ticker coverage and frozen calendar fingerprint rather than accepting a self-hashed arbitrary source file.

## Next authorized action

From the IDX-Trade checkout on the user's Windows machine, run exactly:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_forward_ca_calendar_probe_v1.ps1
```

Default provider checkout:
`D:\Documents\Project\idx-bei-forward-ca-provider`

Default output:
`D:\Documents\Project\idx-forward-ca-calendar-probe-<YYYYMMDD>-v1`

The runner performs provider setup/import validation and exactly one direct `/Home/GetCalendar` request with `range=m`, `start=0`, `length=9999`, no ticker filter and no search filter. It writes immutable raw bytes plus `PROBE_MANIFEST.json` and does not pin/promote the fingerprint automatically.

After the probe, review the manifest/raw schema and only then pin the accepted fingerprint. Do not schedule recurring capture or admit CA attestations to Execution V1 before that review.
