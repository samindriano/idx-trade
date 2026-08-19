# V4-3 CA Schedule-59 — IDX Announcements Evidence Attempt Prep

Date: 2026-08-19
Status: `PREPARED_NOT_RUN`

This lane is the first post-KSEI bounded evidence attempt. It uses the official IDX listed-company announcement API and IDX-hosted attachments as a genuinely different evidence surface.

Frozen parent state:
- residual schedule events: 59;
- residual identity SHA-256: `f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707`;
- diagnosis manifest SHA-256: `8c717e8f4bf7fb69edfe366cd0f219ef0c7d9f812006c409ed682eb6e9c9fb12`;
- KSEI News adjudication manifest SHA-256: `cda56ccd03949aa2f95030179e14ee07328072b1ed59b6b7845b9e2257e07c76`;
- KSEI News newly resolved events: 0/59.

Provider contract:
- base: `https://www.idx.co.id`;
- endpoint: `/primary/ListedCompany/GetAnnouncement`;
- browser-compatible `curl_cffi` TLS;
- exact ticker filter;
- deterministic date window derived only from frozen source dates;
- API JSON captured raw before any attachment selection;
- deterministic event-family title/subject filtering;
- only official IDX-hosted attachments captured;
- acquisition is non-admissive; semantic adjudication occurs later and offline.

Scientific firewall remains unchanged: no price inference, no record/distribution date as transition fallback, no source-date inference, no target/rank materialization, no model fit, prediction, performance, or protected-forward access. The 90% gate is not changed.
