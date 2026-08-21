# Zapi IDX `/dividends` — Bounded Audit Result

Date: 2026-08-21
Branch: `integration/forward-ca-attestation-v1`
Parent HEAD at audit start: `8e3be9f937f1ec7315b822d2f1c686042187b24a`

## Decision

Final procedural verdict:

`AUDIT_HARNESS_BUG_FIXED_REVIEW_EXISTING_ARTIFACT_AGAIN`

The existing capture is **not decision-complete** for admitting Zapi
`/dividends` and remains ineligible for Forward CA V1.1. It must not be
interpreted as a permanent endpoint `NO_GO`, because the request did not use
the catalog's declared `search` filter and returned an empty default-month
page. A second authenticated request was deliberately **not** made in this
task.

## Exact raw response shape

`dividends_raw.json` is a non-empty JSON object, not `null`, an empty root
object/list, or an HTTP-200 error/message envelope:

```json
{
  "project": "finance:idx:dividends",
  "data": {
    "provider": "idx",
    "dataset": "dividends",
    "year": 2026,
    "month": 8,
    "page": 1,
    "nextPage": null,
    "count": 0,
    "total": 0,
    "hasMore": false,
    "items": []
  },
  "timestamp": "2026-08-21T05:12:56.697Z"
}
```

Interpretation: the endpoint returned a valid nested `data` envelope with an
explicit empty result page. There are zero dividend rows, zero ticker-bearing
rows, and zero rows with the required dividend semantics. The raw bytes are
not an unrecognized non-empty row payload.

Raw SHA-256:
`963a2bd8a0599bf63ead4c517165ade688de72144584356ce646cf9e714bf3fa`

## Catalog contract

`catalog_schema_raw.json` SHA-256:
`72cecf672a3635868c30b38d0b5a4908ef28cd5817b686065c2cc9820f24efbd`

The public schema returned HTTP 200 and exposes these optional query fields:

| Field | Type | Semantics |
|---|---|---|
| `year` | number | report year; default current Jakarta month context; 1990–2100 |
| `month` | number | 1–12; default current Jakarta month context |
| `page` | number | page number; default 1; minimum 1 |
| `length` | number | page size; default 20; maximum 200 |
| `search` | string | upstream filter on code or company name |

The endpoint contract is `GET https://api.zpi.web.id/v1/finance:idx/dividends`.
The catalog payload itself does not declare an HTTP method/path, so the path
comes from the pinned probe/handoff rather than being inferred from a field.

## Harness audit and bounded fix

The old probe recognized `code`, `ticker`, and `symbol` but ignored the
catalog's `search` field. Consequently the existing authenticated request was
only `page=1&length=20`, recorded as
`GLOBAL_FEED_CLIENT_SIDE_TICKER_FILTER`, despite a server-side code/company
filter being available. The old reviewer also did not unwrap the raw `data`
envelope, so it missed `provider` and `dataset`, and omitted nested
`nextPage`/`hasMore` metadata.

Minimal remediation:

- the probe now uses `search=<target>` as `SERVER_TICKER_FILTER` when no
  dedicated ticker field exists;
- the reviewer unwraps `data` as well as `content`;
- nested `provider`, `dataset`, and pagination fields are audited;
- an old global manifest with catalog `search` now fails explicitly with
  `REQUEST_DID_NOT_USE_AVAILABLE_SEARCH_FILTER`.

No frozen semantic gate was relaxed. The original raw/manifest artifacts were
not rewritten.

## Offline rerun

The reviewer was rerun against the existing external directory only, writing
a new sibling report:

`D:\Documents\Project\idx-zapi-dividends-probe-20260821-v1-r2\PROBE_REVIEW_OFFLINE_REMEDIATED.json`

Offline review SHA-256:
`32e15d083211e85f1de4608a1b688357748ca40457f7ac1f231989edecdbab7a`

Result:

- status: `FAIL_NOT_ELIGIBLE_FOR_V1_1`
- provider: `idx`
- dataset: `dividends`
- row count: `0`
- explicit ticker rows: `0`
- pagination: `page=1`, `nextPage=null`, `count=0`, `total=0`, `hasMore=false`
- failures:
  - `REQUEST_DID_NOT_USE_AVAILABLE_SEARCH_FILTER`
  - `NO_DIVIDEND_ROWS_FOUND`
  - `GLOBAL_FEED_ROWS_HAVE_NO_TICKER_IDENTITY`
  - `NO_ROW_WITH_REQUIRED_DIVIDEND_SEMANTICS`
- V1.1 promotion recommendation: `false`

The original review remains unchanged:
`PROBE_REVIEW.json` SHA-256
`c7c4625df419212575962d05a6ab99814092310d268f92e42497f5c67fb2c154`.
The new remediation report is a separate external file.

## Request accounting and next action

Authenticated request count in this task: **0**. No provider call, retry,
credential read, or raw-artifact overwrite occurred.

The next bounded request, only after separate authorization, must use the
schema-declared server filter, for example:

`GET /v1/finance:idx/dividends?search=BBCA&year=<known non-empty BBCA dividend year>&month=<known non-empty BBCA dividend month>&page=1&length=20`

The year/month must be selected from an independently pinned known dividend
event; the current empty default-month page must not be reused as evidence.
That one request must be followed by the existing offline semantic gate. Do
not use `company-profile` as an automatic substitute; it is only a separately
audited fallback candidate.

## Boundaries preserved

- Forward CA V1.1 was not created or promoted.
- Direct IDX remains authoritative.
- V4-X1 alpha, Decision V1, model/panel/frozen scientific identity were not
  changed.
- No historical backfill, model, outcome, or execution accounting work ran.
