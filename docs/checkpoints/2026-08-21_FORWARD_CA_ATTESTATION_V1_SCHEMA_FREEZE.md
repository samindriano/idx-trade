# Forward CA Attestation V1 — Calendar Schema Freeze

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Base: `research/idx-v4-x1-decision-v1@776ec2d5518a8a340ba01668191dd99f257d6d8d`
Status: `CALENDAR_SCHEMA_FROZEN_FORWARD_CA_ATTESTATION_READY_FOR_INTEGRATION`

## Purpose

Freeze the prospectively observed direct-IDX `/Home/GetCalendar` response schema required by Forward CA Attestation V1. This lane protects paper execution/accounting from corporate actions occurring between the decision state and execution/holding state. It is operational/provenance infrastructure, not alpha research and not a historical-CA model remediation.

## Live probe evidence

The user executed the repository-owned one-request probe on Windows through the isolated pinned provider:

- provider repository: `nichsedge/idx-bei`
- provider commit: `75d6c0f74fa360d225794c70c383348977de6798`
- provider module: `idx.core.client.IDXClient`
- transport: `curl_cffi`
- upstream: `https://www.idx.co.id/primary`
- endpoint: `/Home/GetCalendar`
- request: `range=m`, `date=20260821`, `start=0`, `length=9999`, `code=''`, `language=id-id`, `search=''`
- HTTP status: `200`
- result rows: `260`
- raw SHA-256: `7ad2aeab850ea23a4df9f6aee91f1523b2a4110a30f48d6ecf51e8376be88c1c`
- observed structural fingerprint: `09a2f81aaa291b27232ca610b228a28470cbe11d5599fa66f55a3b75030060f3`

The offline repository reviewer then recomputed and independently validated the evidence with:

- status: `PASS_ELIGIBLE_FOR_SCHEMA_FREEZE`
- `freeze_recommendation=true`
- no failures
- no warnings
- top-level keys: `ResultCount`, `Results`, `request`
- observed result fields include `AgendaTahun`, `FinalID`, `Jenis`, `MonthName`, `MonthNumber`, `Step`, `TglWaktuPE`, `TglWaktuRups`, `Year`, `description`, `id`, `location`, `start`, `title`

External immutable local evidence remains under:
`D:\Documents\Project\idx-forward-ca-calendar-probe-20260821-v1`

The raw bytes are intentionally not copied into Git.

## Frozen schema identity

`EXPECTED_CALENDAR_SCHEMA_FINGERPRINT` is now frozen to:

`09a2f81aaa291b27232ca610b228a28470cbe11d5599fa66f55a3b75030060f3`

The same value is recorded in `config/forward_ca_attestation_v1.json`.

Future calendar payloads are recomputed from raw bytes. A structural mismatch fails closed; the collector cannot self-declare a new schema and have it silently admitted.

## Forward CA V1 source contract

Primary authority remains direct official IDX through the pinned `idx-bei` transport.

Required legs:

1. `/ListingActivity/GetIssuedHistory`
2. `/NewsAnnouncement/GetAllAnnouncement`
3. `/Home/GetCalendar`

Required acquisition phases:

1. `POST_EOD`
2. `PREOPEN`

The same ticker/window scope must survive both phases. Raw response bytes, endpoint identity, content type, HTTP status, request metadata, SHA-256, provider pin and calendar fingerprint are verified before attestation.

Execution admits only a verified `NO_RELEVANT_EVENTS` attestation. Relevant CA evidence, incomplete source evidence, schema drift or provenance failure remains fail-closed.

## What this CA lane is for

This Forward CA lane is not the historical ~88% corporate-action continuity lane used when discussing possible V4-X2 data remediation.

It exists to keep paper/live portfolio state mechanically correct. Examples:

- stock split / reverse split can change share quantity and reference price;
- cash/stock dividend can change cash or share entitlement;
- rights/HMETD, bonus shares, conversions, additional listings or delisting-related events can require explicit reconciliation;
- if a relevant event appears, Execution V1 must not blindly treat raw next-session prices and prior share counts as normal continuity.

Forward CA V1 therefore answers a narrow operational question: `is this decision-to-execution/holding interval safe to process as ordinary continuity?`

It does not modify V4-X1 alpha, training data, frozen model hashes, Decision V1, historical CA representation, or historical PnL authorization.

## Zapi decision after 2026-08-20/21 endpoint additions

The user supplied a Zapi changelog showing newly exposed dedicated IDX endpoints including `issued-history`, `dividends`, `rights-offerings`, `stock-splits`, `additional-listings`, `delistings`, plus the existing `calendar` family.

These are highly relevant as a future redundancy layer, especially dedicated dividends/rights/splits. They do not replace direct IDX in Forward CA V1 because:

- the direct-IDX path has now been live-probed and schema-frozen with official upstream bytes;
- adding an intermediary at the same freeze boundary would expand the source contract and failure surface without fixing a demonstrated V1 gap;
- the dedicated Zapi endpoints were newly announced and should receive their own bounded response/provenance audit before becoming execution evidence.

Decision:

- V1 primary: `DIRECT_IDX_VIA_PINNED_IDX_BEI`
- Zapi in V1: `NOT_WIRED`
- future candidate: `Forward CA V1.1 parity/failover`
- highest-value Zapi candidate endpoints: `dividends`, `rights-offerings`, `stock-splits`, `issued-history`, `calendar`, `additional-listings`, `delistings`

A future V1.1 may use Zapi only after a bounded parity audit defines when disagreement with direct IDX blocks execution. No silent fallback is authorized.

## Remaining boundaries

Schema freeze alone does not authorize:

- historical CA backfill;
- historical PnL;
- V4-X2 creation;
- automatic Zapi fallback;
- automatic split/dividend/rights accounting transformation;
- changing V4-X1/Decision/Sizing rules.

The next implementation step is to integrate the now-frozen Forward CA source/attestation path into the Forward Paper Orchestrator and define the operational schedule for POST_EOD + PREOPEN captures. Actual CA events remain reconciliation-required until event-specific state transformations are separately frozen.
