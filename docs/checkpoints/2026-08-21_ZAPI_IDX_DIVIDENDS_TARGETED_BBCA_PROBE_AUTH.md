# Zapi IDX `/dividends` — Targeted BBCA Known-Positive Probe Authorization

Date: 2026-08-21 (Asia/Jakarta)
Branch: `integration/forward-ca-attestation-v1`
Status: `ONE_TARGETED_AUTHENTICATED_REQUEST_AUTHORIZED_V1_1_STILL_BLOCKED`

## Purpose

Resolve the remaining Zapi `/dividends` admission ambiguity after the first authenticated audit returned a valid but empty default August 2026 page and Codex established that the public catalog exposes `search`, `year`, and `month` query fields.

This authorization is for endpoint-contract certification only. It does not authorize Forward CA V1.1 promotion, paper-state mutation, alpha changes, historical backfill, or automatic dividend reconciliation.

## Independently pinned known-positive event

Target ticker: `BBCA`.

BCA's own investor-relations dividend history / official dividend announcement establishes a known-positive March 2026 event for the final FY2025 cash dividend:

- cash dividend remaining/final amount: IDR 281 per share;
- announcement: 2026-03-13;
- regular/negotiated-market cum date: 2026-03-27;
- regular/negotiated-market ex date: 2026-03-30;
- record date: 2026-03-31;
- payment date: 2026-04-08.

The period was selected before observing any targeted Zapi response. March 2026 is therefore a defensible known-positive query month rather than a post-response search for a passing example.

## Exact authorized request

Exactly one authenticated endpoint request, zero retry:

`GET /v1/finance:idx/dividends?search=BBCA&year=2026&month=3&page=1&length=20`

The public catalog-schema request performed before it remains unauthenticated and is used to ensure the declared fields still exist. If the live catalog no longer exposes the requested fields, the probe must stop before the authenticated request.

## Admission gate

After capture, the existing offline reviewer must independently validate:

- HTTP 200 and immutable raw SHA;
- provider `idx` and dataset `dividends` where exposed;
- server-side ticker scope `search=BBCA`;
- bounded page size;
- one or more dividend rows;
- a row with usable cash/share + cum date + ex date + record date + payment date;
- internally valid chronology;
- no API-key persistence.

Only `PASS_ELIGIBLE_FOR_V1_1_STRUCTURED_HELPER` allows ChatGPT to consider building V1.1. Direct official IDX remains authority even after a Zapi PASS; Zapi can only serve as structured extraction/parity helper under disagreement-fail-closed semantics.

## Harness remediation for this request

`probe_zapi_idx_dividends_v1.py` now accepts explicit paired `--year` and `--month` arguments and refuses to silently drop them. `run_zapi_idx_dividends_audit_v1.ps1` exposes matching `-Year` / `-Month` parameters and records them in the output directory / manifest. Regression tests cover search scoping and explicit-period forwarding.

## Command

From the branch checkout after pulling latest:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& .\scripts\run_zapi_idx_dividends_audit_v1.ps1 -Code BBCA -Year 2026 -Month 3
```

Do not issue additional Zapi requests if this targeted probe fails. Review its raw/manifest evidence first.
