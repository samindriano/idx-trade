# Direct IDX Endpoint Audit — Security-Challenge Blocked

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/idx-direct-endpoint-audit-v1`
IDX-BEI source: `nichsedge/idx-bei` at `75d6c0f`
Status: `BLOCKED_DIRECT_IDX_SECURITY_CHALLENGE`

## Scope

This was a bounded direct-source discovery audit for IDX-Trade. The scope was
limited to a light client setup check and, if permitted, a few direct IDX
probes for historical PIT sector classification, listing history, issued/share
history, and financial-report provenance. No IDX-Trade dataset, model,
protected outcome, or bulk backfill was accessed or changed.

The source repository was cloned outside Git at:

`D:\Documents\Project\idx-bei-direct-audit-20260813`

The source repository's existing Python tests passed with the available Python
runtime:

```text
python -m pytest tests/ -q
24 passed in 0.36s
```

`uv sync` could not be run because `uv` is not installed in this environment.
The existing environment already provided Python 3.13.5 and `curl_cffi` 0.13.0.

## Direct request result

The first bounded direct probe used the existing client path with browser
impersonation disabled (`impersonate=None`):

```text
GET https://www.idx.co.id/primary/TradingSummary/GetStockSummary
  date=20260811&start=0&length=5
```

The response was:

```text
HTTP 403
Content-Type: text/html; charset=UTF-8
Server: cloudflare
```

The body was a 4,546-byte HTML security/challenge response, not IDX JSON. A
second identical request was made only to preserve the raw response and its
metadata. A final one-request client-wrapper check used
`IDXClient(max_retries=0, delay_seconds=0, impersonate=None)` and returned the
same `403` response. Total direct requests: `3`; endpoint probes after the
challenge: `0`.

No browser impersonation, challenge bypass, alternate source, cookie solving,
or endpoint-specific retry was attempted. Per the audit boundary, acquisition
stopped at the first direct IDX security rejection.

## External evidence

Runtime evidence remains outside Git:

`D:\Documents\Project\idx-direct-endpoint-audit-20260813`

| Artifact | SHA-256 |
|---|---|
| `probe_001_stock_summary_20260811.response.bin` | `2919c6e6a047322a878fb2ef7114a47f387149b4f43cbd0a4714fdabf775ed81` |
| `probe_001_stock_summary_20260811.metadata.json` | `efc40ca227885974d486cf40949087873c497e77a4294671a20c3794573bdc5d` |
| `MANIFEST.json` | `9239312e103e636adc26074420a2abe1d096e89109efe8cb9c52bf256e369896` |

The metadata records the exact endpoint, parameters, headers, status,
content-type, response headers, raw-body hash, and the
`IDX_DIRECT_REQUEST_BLOCKED_SECURITY_CHALLENGE` classification.

## Static discovery inventory (not runtime-verified in this audit)

The cloned `idx-bei` source documents these candidate official IDX routes, but
none were runtime-verified after the challenge:

| Candidate | Intended use | Runtime status here |
|---|---|---|
| `/DigitalStatistic/GetApiDataPaginated` with `urlName=LINK_FINANCIAL_DATA_RATIO` | Year/quarter financial-ratio and classification-field probe | Not probed; blocked before endpoint expansion |
| `/ListingActivity/GetIssuedHistory` | IPO, listing activity, split/reverse-stock, issued/share history | Not probed |
| `/NewsAnnouncement/GetAllAnnouncement` | Announcement dates and attachment provenance | Not probed |
| `/ListedCompany/GetCompanyProfiles` | Current listing/reference universe | Not probed |
| `/TradingSummary/GetStockSummary` | Direct request smoke test | 403 Cloudflare HTML challenge |

The existing IDX-Trade PIT-sector evidence remains unchanged: canonical 2022
and 2023 dedicated classification references are unresolved, and 2026
`Peng-00100/BEI.POP/06-2026` still lacks explicit effective-date evidence.
This audit did not promote or alter any of those statuses.

## Decision

`NO-GO_FOR_DIRECT_ENDPOINT_ACQUISITION_IN_THIS_RUNTIME`.

`idx-bei` is useful as a static endpoint map and client scaffold, but direct
IDX acquisition cannot be evaluated without bypassing the observed security
challenge. Do not use the repository's default Chrome impersonation as a
silent bypass. A future retry requires a separately authorized, compliant
access path; it must not widen into bulk acquisition or model integration.
