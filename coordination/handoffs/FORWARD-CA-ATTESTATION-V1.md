# Forward CA Attestation V1 — Handoff

reasoning_level: xhigh orchestration profile
source_repository: `samindriano/idx-trade`
branch: `integration/forward-ca-attestation-v1`
base_branch: `research/idx-v4-x1-decision-v1`
base_commit: `776ec2d5518a8a340ba01668191dd99f257d6d8d`
status: `ZAPI_DIVIDENDS_NO_GO_COMPANY_PROFILE_PARITY_AUDIT_PREPARED_V1_1_BLOCKED`
owner: `ChatGPT/Forward-CA-Attestation`

## Scope

Prospective, outcome-blind corporate-action attestation for paper Execution V1. This protects execution/portfolio accounting continuity; it is not the historical CA training-data lane and does not modify V4-X1 alpha.

## Primary provider

- repository: `nichsedge/idx-bei`
- pinned commit: `75d6c0f74fa360d225794c70c383348977de6798`
- upstream: direct `https://www.idx.co.id/primary`
- isolated provider environment managed by `uv` / Python 3.13

## Frozen live calendar schema

Accepted 2026-08-21 direct-IDX probe evidence:

- HTTP 200
- 260 `Results`
- raw SHA-256 `7ad2aeab850ea23a4df9f6aee91f1523b2a4110a30f48d6ecf51e8376be88c1c`
- structural fingerprint `09a2f81aaa291b27232ca610b228a28470cbe11d5599fa66f55a3b75030060f3`
- review status `PASS_ELIGIBLE_FOR_SCHEMA_FREEZE`
- no warnings or failures

Production `EXPECTED_CALENDAR_SCHEMA_FINGERPRINT` is pinned to that value. Future raw calendar schema drift fails closed.

## Required Forward CA V1 legs

1. `/ListingActivity/GetIssuedHistory`
2. `/NewsAnnouncement/GetAllAnnouncement`
3. `/Home/GetCalendar`

Both `POST_EOD` and `PREOPEN` captures are required with identical ticker/date scope. Raw bytes and source-chain hashes are verified before the final attestation.

Execution admission remains only:
`NO_RELEVANT_EVENTS`

Any relevant event, source incompleteness, hash mismatch, provider-pin mismatch or schema drift blocks normal execution and requires reconciliation.

## Cash dividend accounting

Preregistered contract:
`docs/checkpoints/2026-08-21_FORWARD_CA_DIVIDEND_ACCOUNTING_CONTRACT_V1.md`

Required semantics:

- entitlement snapshot = paper shares at EOD cum date after same-session execution;
- on ex date create a gross dividend receivable asset;
- receivable contributes to total-return NAV but is not spendable cash;
- selling on ex date does not erase already-earned receivable;
- buying first on ex date does not receive that dividend;
- on payment date transfer receivable to cash without recognizing PnL twice;
- dividend tax/withholding remains explicit/unresolved.

Automatic dividend reconciliation remains `NOT_IMPLEMENTED_FAIL_CLOSED`.

## Alpha boundary

Do not adjust V4-X1 price inputs/ranks for dividends through this lane. V4-X1 is frozen. Ex-date normalization, dividend-yield features, days-to-cum/ex or event-aware entry rules require a separately preregistered alpha/overlay challenger.

## Zapi dedicated `/dividends` — final NO-GO

The corrected, decision-complete known-positive request was:

`GET /v1/finance:idx/dividends?search=BBCA&year=2026&month=3&page=1&length=20`

Observed 2026-08-21:

- HTTP 200;
- server ticker filter active;
- provider/dataset = `idx` / `dividends`;
- `count=0`, `total=0`, `hasMore=false`, `items=[]`;
- raw SHA-256 `d65efaeb59ba9803e232cc04717c7bb795765f1a4b2c4db931b0c54b66aab1ab`;
- review `FAIL_NOT_ELIGIBLE_FOR_V1_1`;
- no warnings.

The period was independently known positive: BCA official history shows final FY2025 dividend Rp281/share with regular-market cum 2026-03-27, ex 2026-03-30, record 2026-03-31, payment 2026-04-08.

Decision:

`ZAPI_DIVIDENDS_ENDPOINT_NO_GO_FOR_FORWARD_CA_V1_1`

Do not spend more requests trying to rescue this endpoint unless Zapi materially changes the contract/data and a new versioned audit is authorized.

Checkpoint:
`docs/checkpoints/2026-08-21_ZAPI_DIVIDENDS_NO_GO_COMPANY_PROFILE_PIVOT.md`

## Zapi `company-profile` pivot

Current public Zapi reference documents:

`GET /v1/finance:idx/company-profile?code=BBCA`

with `dividends[]` fields including `cashPerShare`, `cumDate`, `exDate`, `recordDate`, `paymentDate`, `bookYear`, and `type`.

A strong exact parity target is preregistered from BCA's official June 2026 interim-dividend announcement:

- ticker BBCA;
- Rp20/share;
- cum 2026-06-15;
- ex 2026-06-17;
- record 2026-06-18;
- payment 2026-06-26.

Prepared audit-only entry points:

- `scripts/probe_zapi_idx_company_profile_dividends_v1.py`
- `scripts/review_zapi_idx_company_profile_dividends_v1.py`
- `scripts/run_zapi_idx_company_profile_dividend_audit_v1.ps1`
- `tests/test_zapi_idx_company_profile_dividends_harness.py`

Hard PASS:
`PASS_ELIGIBLE_FOR_V1_1_COMPANY_PROFILE_HELPER`

The audit performs exactly one authenticated BBCA request, zero retries, hashes raw bytes, verifies provider/dataset, requires complete dividend semantics, and requires exact match to the official June 2026 BCA event.

Even on PASS, direct IDX remains authority. Zapi is structured extraction/parity only; disagreement fails closed.

## Forward CA V1.1

Current status:
`NOT_AUTHORIZED`

Promotion sequence:

1. run the prepared company-profile parity audit;
2. only on PASS, implement V1.1 structured helper + cash-dividend event certification;
3. implement/test dividend receivable lifecycle and idempotency;
4. then split/reverse-split quantity transforms;
5. then wire recurring POST_EOD/PREOPEN Forward CA capture into Forward Paper orchestration.

Until an event-specific transformation is implemented, detected CA continues to block blind execution.
