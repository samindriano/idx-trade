# Forward CA Attestation V1 — Handoff

reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
branch: `integration/forward-ca-attestation-v1`
base_branch: `research/idx-v4-x1-decision-v1`
base_commit: `776ec2d5518a8a340ba01668191dd99f257d6d8d`
status: `CALENDAR_SCHEMA_FROZEN_READY_FOR_FORWARD_PAPER_INTEGRATION`
owner: `ChatGPT/Forward-CA-Attestation`

## Scope

Prospective, outcome-blind corporate-action attestation for paper Execution V1. This protects execution/portfolio accounting continuity; it is not the historical CA training-data lane and does not modify V4-X1 alpha.

## Primary provider

- repository: `nichsedge/idx-bei`
- pinned commit: `75d6c0f74fa360d225794c70c383348977de6798`
- upstream: direct `https://www.idx.co.id/primary`
- isolated provider environment managed by `uv` / Python 3.13

## Frozen live calendar schema

The user performed the exact bounded direct-IDX `/Home/GetCalendar` probe on 2026-08-21 and then ran the offline reviewer.

Accepted evidence:

- HTTP 200
- 260 `Results`
- raw SHA-256 `7ad2aeab850ea23a4df9f6aee91f1523b2a4110a30f48d6ecf51e8376be88c1c`
- structural fingerprint `09a2f81aaa291b27232ca610b228a28470cbe11d5599fa66f55a3b75030060f3`
- review status `PASS_ELIGIBLE_FOR_SCHEMA_FREEZE`
- no warnings or failures

Production `EXPECTED_CALENDAR_SCHEMA_FINGERPRINT` is now pinned to that value. Future raw calendar payload schema drift fails closed.

## Required Forward CA V1 legs

1. `/ListingActivity/GetIssuedHistory`
2. `/NewsAnnouncement/GetAllAnnouncement`
3. `/Home/GetCalendar`

Both `POST_EOD` and `PREOPEN` captures are required with identical ticker/date scope. Raw response bytes and source-chain hashes are verified before the final attestation.

Execution admission remains only:
`NO_RELEVANT_EVENTS`

Any relevant event, source incompleteness, hash mismatch, provider-pin mismatch or schema drift blocks normal execution and requires reconciliation.

## What Forward CA is for

Forward CA is an operational safety gate between Decision EOD and execution/holding state. It prevents normal-continuity accounting when splits, dividends, rights/HMETD, bonus shares, conversions, additional listings, delistings or similar events could change shares/cash/reference-price semantics.

It is separate from historical CA completeness (~88%) and possible V4-X2 data remediation.

## Zapi status

User-supplied 2026-08-20/21 Zapi changelog added dedicated IDX endpoints such as `dividends`, `rights-offerings`, `stock-splits`, `issued-history`, `additional-listings`, `delistings` and updated `calendar`.

Decision:

- do not replace direct IDX V1;
- do not silently fallback in V1;
- record Zapi as high-value `V1.1_PARITY_FAILOVER_CANDIDATE`;
- if pursued later, bounded-audit the new endpoint response/provenance contract and define disagreement behavior first.

## Prepared entry points

- provider setup: `scripts/setup_idx_bei_forward_ca_provider.ps1`
- direct capture: `scripts/capture_forward_ca_idx_bei.py`
- offline merge/attestation: `scripts/build_forward_ca_attestation_v1.py`
- source verifier/classifier: `src/idx_trade/forward_ca_attestation_v1.py`
- Execution CA verifier: `src/idx_trade/v4_x1_execution_v1_verify.py`
- config: `config/forward_ca_attestation_v1.json`
- freeze checkpoint: `docs/checkpoints/2026-08-21_FORWARD_CA_ATTESTATION_V1_SCHEMA_FREEZE.md`

## Next lane action

Integrate frozen Forward CA V1 into the Forward Paper Orchestrator:

1. derive relevant ticker set from actual paper holdings + pending transitions + Decision intents;
2. POST_EOD capture;
3. PREOPEN refresh;
4. merge + build attestation;
5. only then call Execution V1;
6. relevant CA stays reconciliation-required until event-specific quantity/cash transformations are separately frozen.

Do not rerun the 2026-08-21 schema probe unless a deliberate schema re-certification is required.
