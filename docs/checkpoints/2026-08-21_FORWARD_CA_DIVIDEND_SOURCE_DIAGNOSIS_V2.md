# Forward CA — Dividend Source Diagnosis V2

Date: 2026-08-21
Branch: `integration/forward-ca-attestation-v1`

## Observed direct-IDX V2 result

The current-forward paired probe returned HTTP 200 on both direct official IDX requests:

1. `DigitalStatistic/GetApiDataPaginated?urlName=LINK_DIVIDEND` for BBCA / August 2026;
2. `/ListedCompany/GetAnnouncement` for BBCA / 2026-08-18..2026-08-21.

The announcement leg returned exactly one relevant row whose official metadata includes:

- ticker `BBCA`;
- announcement timestamp `2026-08-19T18:31:03`;
- title/subject `Jadwal Dividen Tunai Interim`;
- announcement number `005/CSG-IVR/2026`.

The prior reviewer reported `announcement_match=false` only because its date extractor required a word boundary after `YYYY-MM-DD`; ISO datetime values such as `2026-08-19T18:31:03` therefore failed the regex. This is an offline reviewer bug, not a source failure.

## LINK_DIVIDEND interpretation

The direct `LINK_DIVIDEND` response returned HTTP 200 but zero rows for the current BBCA event. Combined with prior observations that the endpoint does return structured dividend rows for other periods, this is evidence that `LINK_DIVIDEND` is not sufficiently timely to serve as the sole forward/current operational authority.

It remains useful as:

- lagging structured corroboration;
- historical normalization/backfill candidate after separate coverage work;
- a source for canonical fields (`cashDividend`, `cumDividend`, `exDividend`, `recordDate`, `paymentDate`) when rows are present.

It must not gate current Forward CA event detection by itself.

## Current authority direction

Preferred forward/current chain:

1. official IDX `/ListedCompany/GetAnnouncement` publication metadata;
2. official announcement attachment(s) for event terms;
3. official IDX calendar / other direct-IDX legs for corroboration where available;
4. `LINK_DIVIDEND` as lagging structured corroboration;
5. Zapi company-profile only as optional parity, never authority.

## Next bounded step

Run `scripts/inspect_forward_ca_idx_dividend_announcement_v2_offline.py` against the already captured V2 artifact directory. This performs zero network requests and surfaces the exact official attachment filename/path for the unique BBCA dividend announcement.

Only after attachment identity is known should a bounded attachment fetch/parser be authorized.

## Boundaries

- V4-X1 remains frozen;
- no alpha overlay is authorized;
- no paper state mutation;
- no V1.1 promotion yet;
- no more Zapi `/dividends` requests;
- do not treat the V2 reviewer failure as an announcement-source failure.
