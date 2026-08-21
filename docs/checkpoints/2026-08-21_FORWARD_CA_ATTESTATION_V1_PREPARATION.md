# Forward CA Attestation V1 — Preparation

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Base: `research/idx-v4-x1-decision-v1`
Status: `CALENDAR_SCHEMA_PROBE_READY_EXECUTION_ADMISSION_STILL_BLOCKED`

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

Provider-dependent acquisition scripts must therefore be run with the provider uv project, not the IDX-Trade interpreter. Offline verification/attestation remains inside IDX-Trade.

Zapi is not wired in V1. It remains a future fallback/parity source, not the authority for this preparation.

## Direct calendar contract confirmation

Before the live probe, the current calendar request contract was corroborated against an independent IDX client implementation:

- endpoint: `/Home/GetCalendar`
- parameters: `range`, `date`, `start`, `length`, `code`, `language`, `search`
- valid range values: `d`, `w`, `m`
- response top-level event collection: `Results`

This is documentation/source corroboration only. It does not replace the required live schema probe.

## Prepared components

### Provider and live capture

- `scripts/setup_idx_bei_forward_ca_provider.ps1`
  - clones or validates the external provider checkout;
  - detaches exactly at the pinned commit;
  - creates/syncs the provider's own uv environment;
  - performs import-only smoke validation; no IDX data request.
- `scripts/probe_forward_ca_calendar_schema_v1.py`
  - self-contained one-request direct-IDX calendar probe;
  - validates provider git HEAD before network access;
  - uses `max_retries=0`, `delay_seconds=0` so the bounded probe is exactly one HTTP attempt;
  - writes raw bytes, SHA-256 and `PROBE_MANIFEST.json`;
  - requires object + non-empty `Results` before emitting a fingerprint;
  - never pins/promotes the fingerprint itself.
- `scripts/run_forward_ca_calendar_probe_v1.ps1`
  - one-command Windows wrapper around provider setup + exactly one bounded probe.
- `scripts/capture_forward_ca_idx_bei.py`
  - validates provider git HEAD before any request;
  - uses direct `/primary` requests;
  - captures immutable raw response bytes + SHA-256 + request metadata;
  - captures all 15 `GetIssuedHistory` action types;
  - captures `GetAllAnnouncement` per required ticker with pagination;
  - captures calendar all-market by month, not per ticker, for every calendar month touched by the decision-to-execution window;
  - requires non-empty calendar `Results` and one stable structural fingerprint per phase;
  - fails closed on non-200, invalid JSON, schema mismatch or detectable issued-history truncation.

### Offline source verification and attestation

- `src/idx_trade/forward_ca_attestation_v1.py`
  - immutable provider/upstream identity;
  - raw-artifact SHA verification;
  - exact endpoint and JSON content-type verification;
  - schema verification for `data`, `Items`, and calendar `Results`;
  - calendar structural fingerprint recomputed from raw JSON bytes rather than trusting the collector declaration;
  - POST_EOD/PREOPEN scope equality requirement;
  - source-manifest merge and verification;
  - conservative event classification;
  - final attestation builder.
- `scripts/build_forward_ca_attestation_v1.py`
  - merges two verified phase manifests;
  - builds final attestation only after calendar fingerprint promotion.
- `src/idx_trade/v4_x1_execution_v1_verify.py`
  - no longer accepts a merely self-hashed arbitrary CA source artifact;
  - requires provider repo/commit/upstream identity;
  - requires the frozen calendar fingerprint;
  - verifies source-manifest SHA and recursively verifies both phase manifests and all raw evidence hashes;
  - requires exact source/evidence ticker coverage and exact date scope;
  - remains fail-closed while the fingerprint is not frozen.

## Calendar capture topology

Frozen preparation topology:

`ALL_MARKET_MONTHS_TOUCHING_WINDOW`

For each POST_EOD/PREOPEN phase, the collector requests one monthly all-market calendar snapshot for each distinct month touched by `[decision_session, next_official_session]`. Typical windows require one request; a month-boundary or long-holiday window may require two.

Rationale:

- monthly all-market output is small enough for bounded daily use;
- avoids empty/non-empty per-ticker payloads producing artificial schema fingerprint differences;
- naturally covers long weekends and month boundaries;
- ticker and event relevance is filtered offline under the immutable evidence set.

Calendar events are not all treated as corporate actions. A ticker match alone is insufficient: the event also requires a CA keyword and a date in the post-decision execution window. Thus events such as plain RUPS do not automatically block execution.

Company announcements are intentionally conservative: CA-keyword announcements published on the decision date are treated as relevant, because a post-close disclosure may affect the next execution session.

## Promotion gate intentionally left closed

`EXPECTED_CALENDAR_SCHEMA_FINGERPRINT` remains intentionally `None`.

Therefore both final attestation generation and Execution V1 CA admission fail closed even if otherwise-valid POST_EOD and PREOPEN manifests exist.

Required next step is exactly one bounded direct-IDX calendar probe using the pinned provider, followed by review of:

1. HTTP/status and content type;
2. exact top-level schema and `Results` row fields/types;
3. event/date/ticker semantics;
4. record-count/completeness behavior for the requested monthly snapshot;
5. raw SHA-256 and structural fingerprint.

Only after that review may the fingerprint be pinned in config/code.

## Exact next local command

From the IDX-Trade checkout on the user's Windows machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_forward_ca_calendar_probe_v1.ps1
```

Defaults:

- provider checkout: `D:\Documents\Project\idx-bei-forward-ca-provider`
- anchor date: current local date as `yyyyMMdd`
- output: `D:\Documents\Project\idx-forward-ca-calendar-probe-<YYYYMMDD>-v1`

The wrapper sets up/validates the pinned provider and then runs the probe under:

```text
uv run --project <provider-checkout>\python ...
```

No recurring task, final attestation, paper order, or paper state mutation is performed by this command.

## Intended operational sequence after promotion

1. Decision EOD(t) determines relevant set = paper holdings + pending transitions + decision target/intents.
2. POST_EOD direct IDX capture for the exact required ticker set plus all-market monthly calendar evidence.
3. PREOPEN capture before the immediate next official IDX session.
4. Verify both phase manifests and recompute all raw integrity/schema evidence.
5. Merge them into one source manifest.
6. Build attestation:
   - `NO_RELEVANT_EVENTS` -> eligible for Execution V1 CA gate;
   - `RELEVANT_EVENT_DETECTED` -> fail closed / CA reconciliation;
   - any source/schema/completeness error -> no execution.
7. Execution V1 independently re-verifies the complete source chain before admitting the attestation.

## Current authorization boundary

Authorized now:
- code/config preparation;
- provider environment setup;
- offline synthetic tests;
- one bounded calendar schema probe.

Not authorized by this checkpoint:
- historical CA bulk acquisition;
- V4-X1/X2 model changes;
- historical PnL;
- automated Zapi fallback;
- corporate-action quantity/cash transformations;
- recurring forward-CA scheduler;
- forward paper execution or paper-state mutation before fingerprint promotion.

## Validation state

Synthetic regression coverage now includes:

- provider-pin rejection;
- raw-hash mutation rejection;
- forged collector-declared calendar fingerprint rejection through raw recomputation;
- cross-phase scope mismatch rejection;
- calendar-schema freeze gate;
- no-event and issued-history event paths;
- non-CA calendar event not blocking;
- CA calendar event blocking;
- same-day CA announcement conservative blocking;
- Execution verifier rejection before schema freeze;
- Execution verifier full verified-source-chain success path;
- incomplete ticker coverage rejection;
- source SHA mismatch rejection;
- downstream raw evidence mutation rejection.

No live IDX/Zapi provider request has been executed from this ChatGPT runtime because outbound DNS to `idx.co.id` is unavailable here. The one-request local probe is now the sole promotion prerequisite.
