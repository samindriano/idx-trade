# Forward CA Direct IDX Dividend Engine — Preparation

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Status: `DIRECT_IDX_LINK_DIVIDEND_PROBE_PREPARED_V1_1_NOT_YET_PROMOTED`

## Decision

Forward dividend handling should not depend on Zapi. The dedicated Zapi `/dividends` endpoint failed a decision-complete known-positive BBCA March 2026 probe with zero rows and is `NO_GO` for Forward CA V1.1.

The replacement path is a first-party IDX dividend engine implemented inside `idx-trade`, using the already pinned `nichsedge/idx-bei` checkout only as the HTTP/Cloudflare transport layer.

Do **not** fork or modify `idx-bei` for business logic. Keep the provider pinned and thin. Normalization, event identity, source hashing, entitlement, receivable accounting, revisions and conflict policy belong in `idx-trade`.

## Official IDX structured dividend endpoint

Direct endpoint:

`GET https://www.idx.co.id/primary/DigitalStatistic/GetApiDataPaginated`

with:

- `urlName=LINK_DIVIDEND`
- `periodYear=<year>`
- `periodMonth=<month>`
- `periodType=monthly`
- `isPrint=False`
- `cumulative=false`
- `pageSize=<bounded>`
- `pageNumber=<page>`
- `orderBy=`
- `search=`

Independent public implementation evidence reviewed before this probe:

1. `NeaByteLab/IDX-API` commit `910b8db70893b93920a1bba331d00a1a245907c6` implements `getDividendAnnouncements` against this endpoint and normalizes `code`, `name`, `cashDividend`, `cumDividend`, `exDividend`, `recordDate`, and `paymentDate`.
2. `rakasatriaefendi/Si-Cuan-Apps` commit `0b78bcaf04705f8eeea34cde05a7a394478c20c8` independently uses the same `LINK_DIVIDEND` endpoint and additionally models currency, final/interim/special type, source fingerprint, duplicate handling and validation warnings.

This is substantially stronger evidence than relying on the new Zapi wrapper surface.

## Why announcements still matter

The structured `LINK_DIVIDEND` feed is intended to certify **terms**:

- cash dividend/share;
- cum date;
- ex date;
- recording date;
- payment date;
- ticker/currency/type when present.

The existing direct IDX announcement leg remains necessary for **publication provenance and early detection**. A company may announce a dividend before the structured monthly table becomes operationally visible, or revise/cancel terms later.

Target event state therefore separates:

1. `ANNOUNCED_PENDING_TERMS` — dividend announcement detected from official disclosure feed, but structured terms are incomplete/unverified;
2. `TERMS_CERTIFIED` — `LINK_DIVIDEND` terms are captured and cross-checked with official disclosure/calendar evidence;
3. `ENTITLED` — paper shares frozen at cum-date EOD after same-session execution;
4. `RECEIVABLE` — gross dividend receivable recognized on ex-date and included in NAV but excluded from spendable cash;
5. `PAID` — receivable transferred to cash on payment date without second PnL recognition;
6. `REVISED_OR_CONFLICTED` — any disagreement/revision fails closed until reconciled.

## Alpha boundary

Dividend news can be economically relevant before cum/ex date: dividend surprises, large indicated yield, pre-cum run-up and post-ex behavior may all contain signal.

That information may be archived prospectively in an immutable dividend event research table with publication timestamp and certified terms, but **must not change frozen V4-X1**. Any use as an entry overlay or feature is a separately preregistered V4-X2/successor experiment.

Suggested future research fields:

- `announcement_published_at`;
- `gross_dividend_per_share`;
- indicated dividend yield using price known at publication time;
- `sessions_to_cum` / `sessions_to_ex`;
- final/interim/special flag;
- revision/cancellation flag;
- prior dividend amount and YoY change where PIT-safe;
- announcement-to-cum price path and post-ex normalized return.

## Bounded direct-IDX admission probe

Known-positive event is preregistered as BBCA final FY2025 dividend:

- cash dividend: Rp281/share;
- regular-market cum: 2026-03-27;
- regular-market ex: 2026-03-30;
- recording date: 2026-03-31;
- payment date: 2026-04-08.

Prepared files:

- `scripts/probe_forward_ca_idx_dividend_v1.py`
- `scripts/review_forward_ca_idx_dividend_probe_v1.py`
- `scripts/run_forward_ca_idx_dividend_probe_v1.ps1`

The probe performs exactly one direct official IDX request, zero retries, through the pinned `idx-bei` provider. It stores raw bytes + SHA-256 and never changes paper state.

Hard PASS status:

`PASS_DIRECT_IDX_DIVIDEND_SOURCE_ELIGIBLE_FOR_V1_1`

PASS requires exact known-positive BBCA parity plus expected first-party provider/upstream/request contract. Otherwise Forward CA V1.1 remains blocked.

## Implementation after PASS

Only after direct source admission:

1. add a `dividend_terms` leg to Forward CA POST_EOD/PREOPEN capture;
2. capture relevant monthly `LINK_DIVIDEND` pages immutably;
3. normalize each row to a deterministic event ID/source fingerprint;
4. reconcile terms against announcement + calendar evidence;
5. implement cash-dividend entitlement/receivable/payment state machine;
6. include receivables in NAV and state hash, never spendable cash pre-payment;
7. add idempotency/replay/revision tests;
8. keep structured dividend event archive available for future outcome-blind alpha research without changing V4-X1.

Stock splits, rights/HMETD and stock dividends remain separate processors.
