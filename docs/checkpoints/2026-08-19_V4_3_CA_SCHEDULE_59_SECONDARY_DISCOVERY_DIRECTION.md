# V4-3 CA Schedule-59 — Secondary Official Discovery Direction

Date: 2026-08-19
Status: `SECONDARY_OFFICIAL_KSEI_DISCOVERY_DIRECTION_FROZEN`

Parent diagnosis manifest SHA-256:

`8c717e8f4bf7fb69edfe366cd0f219ef0c7d9f812006c409ed682eb6e9c9fb12`

Residual 59-event identity SHA-256:

`f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707`

## Direction

The next provider surface is KSEI's own public full-site search and KSEI News archive, not the previously used `publications/corporate-action-schedules/{slug}` category/month index.

The acquisition must:

1. consume all 59 diagnosed residual events;
2. derive deterministic KSEI-search query families only from frozen ticker/source-type/failure-class metadata;
3. query only `https://web.ksei.co.id/search/results/...`;
4. paginate search results until deterministic exhaustion, repetition, or a frozen hard cap; reaching the hard cap with new results is retained as a truncation diagnostic, not silently accepted as complete;
5. admit discovery candidates only from official KSEI-hosted `ksei_news/read/...` pages;
6. capture official KSEI attachments referenced by admitted KSEI News pages when present;
7. retain raw search/news/attachment bytes and exact request diagnostics append-only in a fresh local evidence root;
8. perform **no semantic admission during acquisition**. Exact transition/non-blocking adjudication remains a later offline stage.

## Why this is a genuinely new evidence surface

The prior schedule-category crawl already produced official candidate documents for 53/59 residual events, yet 47 mechanical events lacked an explicit Regular-Market Ex / first-new-basis transition. Historical KSEI News pages can contain richer implementation schedules including explicit old/new nominal trading boundaries, so KSEI News is a justified secondary official discovery path rather than a retry of the same category/month endpoint.

## Hard boundaries

- official KSEI domain only;
- no Google/Bing/search-engine API in the runtime;
- no IDX/issuer/provider substitution in this lane;
- all 59 events retained;
- no pass-preserving subset selection;
- no outcome/target/rank/model/performance access;
- no price inference;
- no Record/Distribution-date fallback as transition;
- no semantic/parser relaxation after seeing provider results;
- conflicts and discovery gaps remain unresolved.

A later source expansion beyond KSEI, if needed, requires a separate preregistered lane after this official-KSEI secondary surface is exhausted and diagnosed.
