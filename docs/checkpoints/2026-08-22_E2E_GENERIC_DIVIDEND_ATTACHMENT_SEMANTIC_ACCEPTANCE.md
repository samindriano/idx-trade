# E2E Generic Dividend Attachment + Semantic Acceptance

Date: 2026-08-22

## Verdict

`GENERIC_DIVIDEND_ATTACHMENT_AND_SEMANTIC_ACCEPTED`

## Scope

This checkpoint accepts the generic prospective cash-dividend evidence path:

`ListedCompany/GetAnnouncement`
? generic candidate discovery
? immutable official IDX attachment capture
? offline semantic extraction
? existing V1.1 certification gate.

No BBCA-specific economics, dates, or attachment hashes are hardcoded in the
production semantic extractor.

## Authority

Forward authority remains:

`DIRECT_IDX_ANNOUNCEMENT_PLUS_HASHED_ATTACHMENT`

`LINK_DIVIDEND` remains lagging corroboration only.

Zapi dividend data remains optional parity only and is not forward authority.

## Generic discovery provenance correction

`TglPengumuman` is the authoritative announcement timestamp when available.

`CreatedDate` is only a fallback.

This was required because the real BBCA response contained:

- `TglPengumuman = 2026-08-19T18:31:03`
- `CreatedDate = 2026-08-19T19:00:02`

Using `CreatedDate` changed the canonical certified-event hash despite identical
economic terms.

## Real BBCA live acceptance

Announcement:

- ticker: `BBCA`
- announcement id: `20260819183103-005/CSG-IVR/2026_id-id`
- announcement number: `005/CSG-IVR/2026`
- authoritative timestamp: `2026-08-19T18:31:03`

Generic attachment capture downloaded three official IDX PDFs with exact SHA-256:

- `4ee38c989b3ff09c5d721e6d56340d873e8183822eadd3c87cd8dbfa576e092c`
- `1d8b37031c4a0c23baeb6d511e8270c3f2be160c9c40c3102c7faaffdf54b94b`
- `93ff2e663af91ac6d87ed29c6a192725f2b4b86b0fc0432610ff7bdaad0c1949`

Generic semantic extraction independently recovered:

- gross dividend/share: `IDR 25`
- cum regular/negotiated: `2026-08-28`
- ex regular/negotiated: `2026-08-31`
- record date: `2026-09-01`
- payment date: `2026-09-16`

Two issuer documents independently contributed a complete consistent semantic
schedule.

## Exact certification parity

The generic pipeline passed the existing execution certification gate and
reproduced the previously admitted canonical event exactly:

- event id:
  `CASH_DIVIDEND_BBCA_6bb86334ebe6902946743804`
- source evidence SHA-256:
  `6bb86334ebe6902946743804650ca9b45bca5c85b3ad3fa76e13a6fbada7666a`

Result:

`GENERIC_PIPELINE_EXACT_CERTIFIED_EVENT_PARITY_PASS`

## Fail-closed behavior

The semantic parser rejects:

- non-cash dividend terms;
- missing ticker evidence;
- conflicting dividend-per-share amounts;
- conflicting schedules;
- incomplete schedules;
- invalid date ordering.

The reviewer also verifies the discovery-manifest lineage, raw announcement
artifact hash, attachment-manifest hash, individual PDF hashes, and PDF magic
before semantic admission.

## Remaining work

This acceptance does not yet install a recurring CA scheduler or complete the
E2E POST_EOD/PREOPEN orchestrator.

Next lane:

`Step 4D ? prospective dividend acquisition/orchestration policy`
