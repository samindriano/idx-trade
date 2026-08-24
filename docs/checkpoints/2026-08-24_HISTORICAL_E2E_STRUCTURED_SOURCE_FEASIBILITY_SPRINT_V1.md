# Historical E2E Structured-Source Feasibility Sprint V1

Date: 2026-08-24 (Asia/Jakarta)
Branch: `research/idx-historical-e2e-replay-v1`
Status: `STRUCTURED_DIVIDEND_POSITIVE_CONTROL_FAIL`

## Scope

This was a bounded source-design experiment. It did not access outcomes, P&L,
NAV, model scores, or the protected forward vault. No historical dividend or
corporate-action ledger was promoted and no production/forward ledger was
modified.

The first gate was the previously authorized known-positive BBCA dividend
request. The structured dividend path was stopped immediately when that
positive control returned no event, as required by the sprint contract.

## Positive control request

- Provider: Zapi IDX transport (`provider=idx` in the response payload)
- Endpoint: `GET https://api.zpi.web.id/v1/finance:idx/dividends`
- Exact parameters: `search=BBCA&year=2026&month=3&page=1&length=20`
- Catalog schema request: `https://api.zpi.web.id/api/public/scrapers/idx/endpoints/dividends/schema`
- Catalog HTTP status: `200`
- Catalog fields: `year`, `month`, `page`, `length`, `search`
- Authenticated request count: `1`
- Retry count: `0`
- HTTP status: `200`
- Content type: `application/json`
- Response envelope: top-level `data`, `project`, `timestamp`
- Dataset: `dividends`
- Nested provider: `idx`
- Nested search/year/month: `BBCA` / `2026` / `3`
- Nested pagination/count: `page=1`, `count=0`, `total=0`, `hasMore=false`
- Nested items: `[]`

The query was selected before observing the response because BBCA's official
known-positive March 2026 cash-dividend event is independently established by
the prior authorization checkpoint. The source therefore failed the required
positive-control reproduction test. The response cannot be used to establish
either event presence or event absence.

## Immutable probe evidence

External output root:

`D:\Documents\Project\idx-historical-e2e-zapi-dividend-positive-20260824-v2-03bd844008604928a82ac1a49534946c`

- `PROBE_MANIFEST.json` raw SHA: `not separately persisted in Git; see external root`
- `catalog_schema_raw.json` SHA-256: `72cecf672a3635868c30b38d0b5a4908ef28cd5817b686065c2cc9820f24efbd`
- `dividends_raw.json` SHA-256: `9bdd2a1ec6e12393e350dea75b96ff525e276406f122108bda431f18597d1247`
- `api_key_persisted`: `false`

The raw response is retained outside Git. Credentials were read only from the
process environment and were not printed or written to the artifact.

## Decision

`ZAPI_STRUCTURED_DIVIDENDS_POSITIVE_CONTROL_FAIL`

Do not:

- treat `total=0` as `CERTIFIED_NO_RELEVANT_DIVIDEND`;
- infer that the endpoint is a complete historical official event authority;
- issue the proposed all-ticker negative queries;
- continue this dividend structured-source path without a new source/contract
  explanation;
- use the endpoint as a replacement for official IDX announcement/attachment
  provenance.

This result does not prove that the underlying official IDX dividend source is
empty. It proves only that the observed Zapi structured query did not reproduce
the known-positive BBCA event, so its negative results are not admissible for
historical no-event certification.

## Boundary

The CA structured-source route remains a separate feasibility question. It may
be evaluated independently only with the same outcome-blind, exposure-scoped,
page-complete, provenance-preserving rules. No CA call was made in this
positive-control step.

