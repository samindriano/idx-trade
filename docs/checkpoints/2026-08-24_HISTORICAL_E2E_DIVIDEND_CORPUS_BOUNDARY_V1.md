# Historical E2E Dividend Corpus Boundary V1

Date: 2026-08-24 Asia/Jakarta  
Branch: `research/idx-historical-e2e-replay-v1`  
Scope: outcome-blind official IDX announcement discovery only

## Objective

The historical E2E replay still requires a defensible dividend-event
continuity gate. This checkpoint records the bounded attempt to acquire
official issuer announcements for the exact 347-ticker Decision V2 exposure
universe over `2023-12-28..2026-07-17`.

No labels, realized returns, protected outcomes, model fitting, or model
rescoring were accessed.

## Source and request semantics

- provider checkout: `D:\Documents\Project\idx-bei-forward-ca-provider`
- provider commit: `75d6c0f74fa360d225794c70c383348977de6798`
- upstream: `https://www.idx.co.id/primary/ListedCompany/GetAnnouncement`
- request is direct IDX through the pinned `curl_cffi`/Chrome transport
- exact issuer parameters: `kodeEmiten`, `emitenType=*`, `indexFrom`,
  `pageSize`, `dateFrom`, `dateTo`, `lang=id`, `keyword=`
- date window: `20231228..20260717`
- required universe: 347 unique tickers

The endpoint reports `ResultCount`. A bounded probe showed that
`pageSize=100,indexFrom=100` can return an empty page while `ResultCount` is
106, whereas `pageSize=9999,indexFrom=0` returned all 106 rows. The research
launcher therefore uses `pageSize=9999` and retains the strict
`len( replies ) == ResultCount`/pagination checks. This is a transport
compatibility correction, not a completeness relaxation.

Issuer responses can contain security-class rows such as `BABY-R`. The raw
response remains preserved, while the candidate extractor excludes only a
`<requested-ticker>-<class>` row from the common-share dividend candidate
contract. A different issuer ticker remains a hard mismatch.

## Acquisition attempts

All attempts were one-shot and fail-closed. No retry or alternate provider
was used after a failure. The launcher preserved each incomplete stage outside
Git:

| Stage | Raw JSON files | Tickers reached | Result | Boundary |
|---|---:|---:|---|---|
| `D:\Documents\Project\.idx-historical-e2e-dividend-announcement-corpus-20260824-v1.partial.pfq058lj` | 4 | 3 | STOP | `ABMM` page 2 empty while `ResultCount=106` under the old page-size-100 launcher |
| `D:\Documents\Project\.idx-historical-e2e-dividend-announcement-corpus-20260824-v2.partial.z49qw3ov` | 34 | 34 | STOP | `BABY-R` security-class row; corrected extractor now excludes it explicitly |
| `D:\Documents\Project\.idx-historical-e2e-dividend-announcement-corpus-20260824-v3.partial.1it_3qff` | 28 files | 28 attempted | STOP | `ASSA` returned HTTP 403; one file is non-JSON transport evidence |

The three stages are not a complete corpus and must not be combined as if
they were a single atomic acquisition. Their raw bytes remain external for
forensic review.

## Result

The official endpoint is source-discoverable and can produce internally
coherent full issuer pages with the corrected page size. However, the bounded
market-wide acquisition did not complete: only 65 unique issuer attempts were
reached across preserved partial stages, and at least one issuer hit HTTP 403.

Therefore this lane does **not** establish a market-wide no-event proof and
does not remove `DIVIDEND_MARKET_WIDE_NO_EVENT_PROOF_MISSING` from the strict
historical replay scope freeze. No dividend event was promoted and no replay
scope was opened.

## Validation

- `tests/test_forward_dividend_acquisition_v1.py`: 9 passed
- full repository suite: 717 passed, 3 existing pandas `FutureWarning`s
- `py_compile`: PASS for the modified launcher, extractor, and test
- `git diff --check`: PASS

## Verdict

`DIVIDEND_SOURCE_PARTIALLY_VALIDATED_CORPUS_INCOMPLETE`

The next safe action is independent review of whether an authorized,
rate-limited acquisition strategy or another official archive can establish
complete per-ticker coverage. Do not infer no-event status from these partial
stages and do not access protected outcomes.
