# Zapi `/dividends` NO-GO and `company-profile` pivot

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Status: `DIVIDENDS_NO_GO_COMPANY_PROFILE_PARITY_AUDIT_PREPARED_V1_1_BLOCKED`

## Final `/dividends` verdict

The dedicated Zapi IDX `/dividends` endpoint is rejected for Forward CA V1.1 structured extraction.

The decision is based on a decision-complete known-positive request, not the earlier empty default-month probe:

`GET /v1/finance:idx/dividends?search=BBCA&year=2026&month=3&page=1&length=20`

Observed:

- HTTP 200;
- `scope_mode=SERVER_TICKER_FILTER`;
- `provider=idx`;
- `dataset=dividends`;
- `count=0`, `total=0`, `hasMore=false`, `items=[]`;
- raw SHA-256 `d65efaeb59ba9803e232cc04717c7bb795765f1a4b2c4db931b0c54b66aab1ab`;
- reviewer status `FAIL_NOT_ELIGIBLE_FOR_V1_1`;
- no warnings;
- failure reason is substantive: no dividend row and therefore no required dividend semantics.

The period was preregistered because BBCA had a known positive final FY2025 dividend in March 2026. BCA's official dividend history records Rp281/share, regular-market cum date 2026-03-27, ex date 2026-03-30, record date 2026-03-31, and payment date 2026-04-08. Therefore the zero-row targeted response is sufficient to reject `/dividends` for this integration purpose.

Do not spend additional `/dividends` requests attempting to rescue the endpoint for V1.1 unless Zapi announces a material contract/data fix and a new versioned audit is authorized.

## Why `company-profile` is the next candidate

Current public Zapi IDX reference documents:

`GET /v1/finance:idx/company-profile?code=BBCA`

and shows a `dividends[]` collection containing structured fields:

- `cashPerShare`;
- `cumDate`;
- `exDate`;
- `recordDate`;
- `paymentDate`;
- `bookYear`;
- dividend `type`.

The same public example shows a BBCA 2026 interim dividend row with:

- Rp20/share;
- cum 2026-06-15;
- ex 2026-06-17;
- record 2026-06-18;
- payment 2026-06-26.

BCA's own official 2026-06 dividend announcement independently confirms exactly those values. This creates a strong, preregistered parity target.

## Prepared company-profile audit

Audit-only files:

- `scripts/probe_zapi_idx_company_profile_dividends_v1.py`
- `scripts/review_zapi_idx_company_profile_dividends_v1.py`
- `scripts/run_zapi_idx_company_profile_dividend_audit_v1.ps1`
- `tests/test_zapi_idx_company_profile_dividends_harness.py`

The live audit contract is intentionally narrow:

1. exactly one authenticated `company-profile?code=BBCA` request;
2. zero retries;
3. immutable raw response + SHA-256;
4. provider must be `idx`;
5. dataset must be `company-profile`;
6. `dividends` must be a non-empty list;
7. at least one complete semantic dividend row must exist;
8. the official BBCA June 2026 parity event must match exactly.

Hard PASS status:

`PASS_ELIGIBLE_FOR_V1_1_COMPANY_PROFILE_HELPER`

Even on PASS:

- direct official IDX remains authority;
- Zapi is structured extraction/parity only;
- disagreement fails closed;
- no paper accounting mutation is authorized by the audit alone;
- V4-X1 alpha/Decision/frozen identity remain untouched.

## Forward CA V1.1 status

Still:

`NOT_AUTHORIZED`

Promotion requires the live company-profile parity audit to PASS, followed by implementation/tests of dividend event certification and receivable accounting.
