# Historical Official Foreign-Flow Source Audit Result V1

Status: `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`

This is a read-only capability audit of the locally persisted historical
official foreign-flow archive. It does not construct a feature, create a
candidate, open targets/outcomes, or alter canonical data.

## Structural evidence

- Source: `OFFICIAL_IDX_GETSTOCKSUMMARY`, label `OFFICIAL_IDX_HISTORICAL_EOD`.
- Acquisition mode: `RETROSPECTIVELY_ACQUIRED`.
- Coverage: 1,288 official sessions, 2021-04-01 through 2026-08-13.
- Rows: 1,129,024 across 983 tickers; unit `SHARES`.
- All 3,868 manifest-declared artifacts exist and their hashes match.
- Session dates exactly equal the archive's 1,288-date official calendar; no
  calendar-only or outside-calendar sessions were found.
- Normalized schema is stable and contains 12 fields: ticker, session date,
  foreign buy/sell/net, unit, label provenance, acquisition mode,
  `knowledge_at_utc`, source, source reference, and raw-source SHA.
- No within-session or cross-session `(ticker, session_date)` duplicates.
- All 1,129,024 rows satisfy exact `foreign_net = foreign_buy - foreign_sell`;
  buy and sell values are non-negative.
- Normalized dates, row counts, raw-source SHA references, and retrieval-time
  fields match their session manifests.

## PIT and identity contract

- Every session manifest has `publication_time_known=false`.
- The declared rule `SESSION_T_DATA_USABLE_FROM_NEXT_OFFICIAL_SESSION_T_PLUS_1`
  is a proposed causality rule, not an independently verified public-
  availability certificate.
- `knowledge_at_utc` matches the archive's observed/retrieval timestamp; it is
  not historical publication time.
- Normalized identity is ticker plus session date. Raw records also expose
  StockCode/StockName/IDStockSummary, but there is no ISIN/issuer transition,
  revision/vintage, or corporate-action linkage.
- The archive is structurally complete relative to its own acquired calendar,
  but population completeness relative to the research panel and survivorship
  continuity are not certified.
- The raw source includes many market fields, but this audit admits only the
  normalized foreign-flow fields for capability review; no price or volume
  field was used to construct an alpha.

## Decision

This archive is a promising future source for the existing H-FLOW/foreign-flow
research family, not a new candidate or an independent H-FLOW mechanism card.
It remains `PARTIAL / SOURCE_ADMISSION_BLOCKED` until public availability,
identity/ISIN continuity, corporate-action basis, revision/vintage, population
coverage, and missingness contracts are independently established. No feature,
C5, target evaluation, or candidate promotion is authorized from this audit.

## Artifact integrity

- Archive manifest SHA-256: `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`
- Coverage census SHA-256: `79e0627aa04e53b4cead58262f9e2af2b973ebb797434cf6354116fdecbb5a5e`
- Official calendar SHA-256: `2b597142190e7e7a3182b80c75dc3fec3e0bbbfe32948fb2d586b33b5844a536`
- Audit JSON SHA-256: `890cca6dbad0845d0c4abcb3bef91ac8e2f34ab57a9df9081d3627221273785e`
- Independent verification JSON SHA-256: `5035e0d4f4b5e713956238b0aa2268e8e3878ff88f029100ba177c131068a5d7`
- Hash-contract JSON SHA-256: `fd49f2af6cfcf139c1124f9af73ebc230ff0d6aa88175493655368ab5afc7255`
- Privacy/target firewall JSON SHA-256: `f40a7716751880e831a1f9ba8399e60f6c1a540c1f5789bf2317da73e225d22e`
- Builder SHA-256: `e57c2f86349bd13837a07ab18386f2e7c67b57a63e83fc4a74ab778cffedaf52`
- Verifier SHA-256: `08e6c81ff94fcab2d34a9f254a1b148fe64a7c15037c38f195193fc49ecff202`

Audit, independent verifier, generic hash contract, and target/privacy firewall:
`PASS`. No network, provider, credential, cloud, target, outcome, incumbent,
canonical, or production state was accessed or modified.
