# V4-3 CA Schedule-59 — Secondary KSEI News Acquisition Prep

Date: 2026-08-19
Branch: `data/v4-3-ca-training-domain-schedule59-ksei-news-v1`
Status: `READY_FOR_ONE_SHOT_SECONDARY_KSEI_NEWS_ACQUISITION`

## Parent diagnosis

Pinned diagnosis manifest:

`8c717e8f4bf7fb69edfe366cd0f219ef0c7d9f812006c409ed682eb6e9c9fb12`

Pinned residual identity:

`f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707`

All 59 residual events remain in scope. The dominant class is 47 mechanical events whose first official schedule candidate lacks an explicit Regular-Market Ex / first-new-basis transition. Six events had no first-stage candidate, and six additional events have event/cash linkage or cash-document/date gaps.

## Secondary official provider surface

This lane uses only KSEI's own public site search and KSEI News:

- `https://web.ksei.co.id/search/results/<query>`
- discovered result pages must be official `ksei_news/read/...` URLs;
- official KSEI attachments linked by admitted KSEI News pages are captured when present.

This is distinct from the already-exhausted first-stage category/month endpoint:

`publications/corporate-action-schedules/{slug}`.

No external search engine is called by the runtime.

## Deterministic query contract

Every one of the 59 events gets:

1. exact ticker query;
2. exact ticker + each frozen source year;
3. two source-type-specific queries frozen before provider access.

Examples:

- Stock Split: `TICKER stock split`, `TICKER pemecahan saham`;
- Reverse Stock: `TICKER reverse stock`, `TICKER nilai nominal baru`;
- Merger: `TICKER merger`, `TICKER penggabungan`;
- Voluntary Conversion: `TICKER penawaran tender`, `TICKER pembelian kembali`.

The query family never uses gate impact, target values, returns, or performance.

Each internal-search query follows KSEI's own `Next` pagination until no next link remains, a repeated-page cycle is detected, transport/parse failure occurs, or the frozen 20-page cap is reached. If a query still exposes `Next` at page 20, that query is explicitly marked truncated; the crawler does not silently certify completeness.

## Raw evidence contract

The acquisition writes fresh append-only local bytes for:

- KSEI search result pages;
- discovered KSEI News pages;
- official KSEI attachments linked by those pages.

It also writes exact event/query/news/attachment link tables, request records, summary, and manifest hashes.

No semantic admission is performed during this run. Ticker evidence in a news page is only a diagnostic count; exact transition/non-blocking classification is deferred to a separately frozen offline adjudication.

## Hard boundaries

- all 59 residual events queried;
- no pass-preserving subset;
- no impact ranking for provider discovery;
- KSEI official domain only;
- no Google/Bing runtime calls;
- no IDX/issuer/third-party source substitution;
- no price inference;
- no Record/Distribution-date transition fallback;
- no source-date inference;
- no parser/semantic relaxation after results;
- no target/rank materialization;
- no historical target loading;
- no model fit/prediction/performance/bootstrap;
- no protected-forward access.

## Run sequence

1. compile helper + runner;
2. run focused tests;
3. verify fresh output path does not exist;
4. execute exactly one acquisition into that fresh root;
5. stop after JSON, even if some queries/articles/attachments fail;
6. freeze the resulting raw manifest before any offline adjudication or retry decision.

Canonical `main:coordination/TEAM_STATUS.md` was inspected before this material lane and no overlapping active V4-3 schedule-59 secondary-KSEI lane was found in the visible live-work section. The canonical shared ledger was not rewritten because the available connector write path requires full replacement of the large file; branch-local ownership is recorded in the parent checkpoint without claiming a canonical TEAM_STATUS update.
