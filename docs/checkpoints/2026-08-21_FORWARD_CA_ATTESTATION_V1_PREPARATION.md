# Forward CA Attestation V1 — Preparation

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Base: `research/idx-v4-x1-decision-v1`
Status: `PREPARED_CALENDAR_SCHEMA_PROBE_REQUIRED`

## Purpose

Prepare the minimum prospective corporate-action evidence path required by the remediated paper Execution V1 without reopening or mutating frozen V4-X1 alpha, Decision V1, historical CA research, or historical PnL.

This lane is operational/provenance infrastructure. It is not an alpha experiment and it does not authorize any paper fill.

## Primary provider

The provider transport is the already-audited direct IDX path through:

- repository: `nichsedge/idx-bei`
- pinned commit: `75d6c0f74fa360d225794c70c383348977de6798`
- package client: `idx.core.client.IDXClient`
- transport: `curl_cffi`, browser impersonation `chrome`
- upstream: `https://www.idx.co.id/primary`

The pin matches the prior IDX-Trade direct-endpoint audit that recorded 14/14 bounded HTTP 200 responses using the same transport family. The provider remains isolated from the IDX-Trade Python environment because current `idx-bei` declares Python >=3.13 while IDX-Trade declares Python >=3.11.

Zapi is not wired in V1. It remains a future fallback/parity source, not the authority for this preparation.

## Prepared components

- `config/forward_ca_attestation_v1.json`
  - immutable provider identity and direct IDX base URL
  - POST_EOD + PREOPEN phases
  - required endpoint legs
  - all 15 `GetIssuedHistory` CA types
  - explicit no-historical-backfill / no-paper-mutation boundary
- `scripts/setup_idx_bei_forward_ca_provider.ps1`
  - clones or validates the external provider checkout
  - detaches exactly at the pinned commit
  - creates/syncs the provider's own uv environment
  - performs import-only smoke validation; no IDX data request
- `scripts/capture_forward_ca_idx_bei.py`
  - validates provider git HEAD before any request
  - uses direct `/primary` requests
  - captures immutable raw response bytes + SHA-256 + request metadata
  - captures `GetIssuedHistory`, `GetAllAnnouncement`, and `Home/GetCalendar`
  - fails on non-200, invalid JSON, or detectable issued-history pagination truncation
  - emits one immutable phase manifest per run
- `src/idx_trade/forward_ca_attestation_v1.py`
  - offline phase-manifest verification
  - raw-artifact SHA verification
  - POST_EOD/PREOPEN scope equality requirement
  - source-manifest merge
  - conservative event classification
  - final attestation builder
- `scripts/build_forward_ca_attestation_v1.py`
  - merge two phase manifests
  - build final attestation after promotion gate is satisfied
- `tests/test_forward_ca_attestation_v1.py`
  - provider-pin rejection
  - raw-hash mutation rejection
  - cross-phase scope mismatch rejection
  - calendar-schema freeze gate
  - no-event and relevant-event classification paths

## Promotion gate intentionally left closed

`EXPECTED_CALENDAR_SCHEMA_FINGERPRINT` is intentionally `None`.

Therefore `build_attestation()` fails with `FORWARD_CA_CALENDAR_SCHEMA_NOT_FROZEN` even if valid POST_EOD and PREOPEN phase manifests exist.

Reason: `/Home/GetCalendar` is reachable through the generic `idx-bei` client pattern, but this IDX-Trade lane has not yet performed its own bounded live schema probe and frozen the exact response structure. The preparation must not silently promote an unverified calendar schema into an execution gate.

Required next step is exactly one bounded direct-IDX calendar probe using the pinned provider, followed by independent review of:

1. HTTP/status stability;
2. response schema and date/ticker semantics;
3. empty-event versus event-present shape;
4. pagination/completeness behavior;
5. schema fingerprint to freeze in config/code.

Only after that review may the fingerprint be pinned and the final attestation path wired into Execution V1.

## Intended operational sequence after promotion

1. Decision EOD(t) determines relevant set = paper holdings + pending transitions + decision target/intents.
2. POST_EOD direct IDX capture for the exact relevant set.
3. PREOPEN capture before the immediate next official IDX session.
4. Verify both phase manifests and immutable raw hashes.
5. Merge them into one source manifest.
6. Build attestation:
   - `NO_RELEVANT_EVENTS` -> eligible for Execution V1 CA gate;
   - `RELEVANT_EVENT_DETECTED` -> fail closed / CA reconciliation;
   - any source/schema/completeness error -> no execution.

## Current authorization boundary

Authorized now:
- code/config preparation;
- provider environment setup;
- offline synthetic tests;
- later one separately reviewed bounded calendar schema probe.

Not authorized by this checkpoint:
- historical CA bulk acquisition;
- V4-X1/X2 model changes;
- historical PnL;
- automated Zapi fallback;
- corporate-action quantity/cash transformations;
- forward paper execution or paper-state mutation.

## Validation performed during preparation

The pure offline attestation core was syntax-checked and exercised on synthetic no-event and relevant-event paths; both passed. The provider capture script was syntax-checked. No live IDX/Zapi provider request was made by this preparation.
