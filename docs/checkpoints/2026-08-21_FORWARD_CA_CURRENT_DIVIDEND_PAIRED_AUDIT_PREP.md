# Forward CA — Current Dividend Paired Direct-IDX Audit Prep

Date: 2026-08-21
Branch: `integration/forward-ca-attestation-v1`

## Why the prior March probe did not admit the source

The direct official IDX `LINK_DIVIDEND` March-2026 probe returned HTTP 200,
8 structured dividend rows, and the expected dividend schema fields:
`code`, `cashDividend`, `cumDividend`, `exDividend`, `recordDate`,
`paymentDate`, plus currency/note fields. The failure was only that BBCA's
known final-2025 dividend was not present in that monthly bucket.

Therefore the result is **not** evidence that the first-party endpoint is
unusable. It shows that the earlier assumption about the monthly bucket was
not established.

## New current-forward target

For Forward CA, a current event is more decision-relevant than forcing a
historical monthly-bucket assumption.

Current BBCA interim dividend terms independently observed before the paired
probe:

- announcement date: 2026-08-19;
- gross dividend/share: IDR 25;
- regular/negotiated-market cum date: 2026-08-28;
- regular/negotiated-market ex date: 2026-08-31;
- record date: 2026-09-01;
- payment date: 2026-09-16.

The same terms were observed in the already captured Zapi company-profile row,
and contemporaneous reports attribute the schedule to the issuer/IDX
announcement. Zapi remains non-authoritative.

## Paired official evidence contract

Exactly two direct official IDX requests, zero retries:

1. `DigitalStatistic/GetApiDataPaginated` with
   `urlName=LINK_DIVIDEND`, `periodYear=2026`, `periodMonth=8`,
   `search=BBCA`, `pageNumber=1`, `pageSize=100`;
2. `/NewsAnnouncement/GetAllAnnouncement` with ticker BBCA and publication
   window 2026-08-18 through 2026-08-21.

Both raw response byte streams are persisted externally and SHA-256 hashed.

## PASS gate

The paired audit passes only if:

- provider repository/commit and direct IDX upstream match the frozen Forward
  CA provider identity;
- both requests return HTTP 200 with expected JSON envelopes;
- the dividend feed contains BBCA with exact IDR 25 / 2026-08-28 /
  2026-08-31 / 2026-09-01 / 2026-09-16 terms;
- the announcement feed contains a dividend-related announcement on
  2026-08-19 within the bounded BBCA query;
- raw hashes verify;
- request count is exactly 2 and retries are zero.

PASS status:
`PASS_DIRECT_IDX_CURRENT_DIVIDEND_PAIR_ELIGIBLE_FOR_V1_1`.

## Interpretation of Zapi company-profile

The prior Zapi company-profile audit returned one complete BBCA dividend row
for the current August/September event. Its previous FAIL was caused by a gate
that expected an older June-2026 event. That result must not be interpreted as
"company-profile has no dividend data". For V1.1, however, Zapi remains only
optional parity/current-event corroboration. Direct IDX remains authority.

## Boundaries

- no V4-X1 alpha change;
- no historical performance rerun;
- no dividend overlay authorization;
- no paper-state mutation;
- no V1.1 promotion until the paired direct-IDX PASS gate succeeds.
