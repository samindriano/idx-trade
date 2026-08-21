# Forward CA — Current Dividend Pair V1 503 / V2 Recovery

Date: 2026-08-21
Branch: `integration/forward-ca-attestation-v1`

## Observed V1 result

The current-forward paired V1 was run against BBCA / August 2026. The first
`LINK_DIVIDEND` request completed before the second leg. The second leg,
`/NewsAnnouncement/GetAllAnnouncement`, returned HTTP 503 and the probe stopped
fail-closed before producing an admissible paired manifest.

This does **not** reject the direct IDX dividend source. Earlier direct capture
already demonstrated HTTP 200 and structured dividend rows with the required
`cashDividend`, `cumDividend`, `exDividend`, `recordDate`, and `paymentDate`
fields.

## idx-bei zero-retry nuance

Pinned `idx-bei` commit
`75d6c0f74fa360d225794c70c383348977de6798` uses a loop where a retriable
HTTP status always logs `retrying in ...` and sleeps before incrementing the
counter. With `max_retries=0`, it then exits the loop; it does **not** send a
second HTTP request. Therefore the V1 log's retry message is misleading for
request accounting, although it adds an unnecessary sleep.

For V2 audit request counting, the helper retry loop is bypassed entirely.
V2 imports `curl_cffi` from the pinned idx-bei environment and performs direct
one-shot GETs with the same browser-compatible headers/impersonation.

## Official announcement endpoint pivot

V2 replaces the flaky announcement endpoint with the issuer-scoped official
IDX endpoint:

`/ListedCompany/GetAnnouncement`

This endpoint is independently used by IDX wrappers for disclosures and
returns a `Replies` envelope containing announcement details and attachments.

V2 request scope:

1. `/DigitalStatistic/GetApiDataPaginated`
   - `urlName=LINK_DIVIDEND`
   - `periodYear=2026`
   - `periodMonth=8`
   - `search=BBCA`
   - page 1 / size 100
2. `/ListedCompany/GetAnnouncement`
   - `kodeEmiten=BBCA`
   - 2026-08-18 through 2026-08-21
   - page/index bounded to 100

Exactly two HTTP attempts are made. No retry helper is used.

## Frozen current event gate

Expected BBCA current-forward dividend terms remain:

- gross dividend/share: IDR 25;
- cum date: 2026-08-28;
- ex date: 2026-08-31;
- record date: 2026-09-01;
- payment date: 2026-09-16;
- announcement date: 2026-08-19.

PASS status:
`PASS_DIRECT_IDX_CURRENT_DIVIDEND_PAIR_V2_ELIGIBLE_FOR_V1_1`.

## Boundaries

- direct IDX remains authority;
- Zapi is not required for V1.1;
- V4-X1 scientific identity remains frozen;
- no dividend alpha overlay is authorized;
- no paper-state mutation is authorized by this audit alone;
- V1.1 remains blocked until V2 semantic review passes.
