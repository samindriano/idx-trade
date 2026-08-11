# Corporate Actions V1 — Official IDX/Zapi Source Audit

Date: 2026-08-11  
Branch: `data/corporate-actions-v1`  
Scope: source discovery, provenance audit, and raw-price diagnostics only

## Decision

`CONDITIONAL_PASS_SOURCE_DISCOVERY_REVISION_SENSITIVE_NO_CANONICAL_PRICE_ADJUSTMENT`

The official IDX Listing Activity corporate-action source is reachable and
bounded for `2021-01-01` through `2026-07-31`. Zapi is a validated transport
and discovery layer for that source: the complete Zapi raw payload matched the
direct IDX record payload exactly. This does not make Zapi an independent
authority. The endpoint is revision-sensitive: a later live query changed the
historical result, so `recordsTotal == returned rows` proves page completeness
for a capture, not immutable historical completeness.

The source is sufficient to retain provenance-aware discovery records for all
listed action categories. It is not yet sufficient to promote every category
to the strict V1 canonical event table because the response exposes
`TanggalPencatatan`, not a verified first market session / ex-date, and omits
some type-specific terms such as HMETD subscription price. No price data was
rewritten or adjusted.

## Sources and captures

Primary official source:

- IDX page: `https://www.idx.co.id/en/listed-companies/corporate-actions`
- IDX endpoint:
  `https://www.idx.id/primary/ListingActivity/GetIssuedHistory?caType=&dateFrom=20210101&dateTo=20260731&start=0&length=9999`
- Raw capture: `D:\Documents\Project\idx-trade-corporate-actions-20260811\raw\idx_direct_issued_history_20210101_20260731.json`
- Raw SHA-256:
  `24ec30beabddda2053f825d06ef8b03de0df1ef727330724b6a6ab1bd661afc8`

Zapi transport/discovery source:

- Endpoint: `https://api.zpi.web.id/v1/finance:idx/raw`
- Raw request path: `ListingActivity/GetIssuedHistory`
- Raw query: `caType=&dateFrom=20210101&dateTo=20260731&start=0&length=9999`
- Raw capture: `D:\Documents\Project\idx-trade-corporate-actions-20260811\raw\zapi_raw_issued_history_20210101_20260731.json`
- Raw SHA-256:
  `e93f86cc51b43071464226f7ac94480f41a7fa396e3a3d40e5258c1a5c683006`

Zapi returned the upstream provider as `idx`, preserved the official row
fields, and returned `recordsTotal=535`, `recordsFiltered=535`, and 535 rows.
The direct IDX response returned the same counts and the same ordered row
payload: exact list equality true and zero row-field differences.

The Zapi `company-announcements` wrapper was also inspected for attachment
discovery. Representative metadata was found for:

- ASDM: `Peng-SS-00007/BEI.PP2/12-2023`, published 2023-12-11;
- BBNI: `Peng-SS-00004/BEI.PP3/10-2023`, published 2023-10-05;
- BUAH: `Peng-SS-00002/BEI.PP1/10-2025`, published 2025-10-22.

The wrapper exposed official IDX `StaticData/NewsAndAnnouncement` attachment
URLs. Direct attachment acquisition from this runtime returned HTTP 403
(Cloudflare), so those error responses were not promoted as evidence and no
PDF SHA was recorded as an official file SHA. The issued-history JSON remains
the only promoted raw source capture in this milestone.

Revision-control capture:

- Direct query through 2026-08-11: 549 rows, raw SHA-256
  `b14a065697bf7c79ac3e8814054f2d58defd86b1871f26b1b7384668d7406aa0`;
- Zapi query through 2026-08-11: 549 rows, raw SHA-256
  `3bc94baf68d77d95626bf7b9becf9d3afc91f1561bf9f6953e3ee4eea28634f0`;
- Direct query for the 1260 panel window `2021-04-29..2026-07-31` now returns
  519 rows and 54 `stockSplit` rows;
- the previously persisted 1260 official CSV contains 55 split rows and
  includes `SCMA / stockSplit / 2021-10-29`, which is absent from the current
  direct query. The discrepancy is an explicit source revision conflict, not
  silently resolved.

## Coverage and field semantics

The 2026-08-11 capture returned 535 records from 2021-01-04 through
2026-07-31; `recordsTotal == recordsFiltered == returned rows`, and
`length=9999` was larger than the returned set. A later query through
2026-08-11 returned 549 rows, while the same research panel window returned
519 rows. Filtered queries for each observed action type returned matching
`recordsTotal` and row counts. The response fields are:

- `KodeEmiten`: issuer ticker;
- `JenisTindakan`: IDX action category;
- `TanggalPencatatan`: official listing/activity date exposed by this source;
- `JumlahSaham`: action amount shown by IDX;
- `JumlahSahamSetelahTindakan`: total shares after the action shown by IDX.

`TanggalPencatatan` is not silently mapped to V1 `market_effective_date`.
The source does not provide a verified first exchange session, ex-date, cum
date, announcement time, knowledge time, or all type-specific economic terms.
Those facts require the linked official announcement/document or another
official source with explicit semantics.

## Record inventory

| IDX category | Rows | V1 discovery mapping | Canonical status |
|---|---:|---|---|
| `stockSplit` | 56 | `STOCK_SPLIT` when positive old/new terms are derivable | Conditional: 40 strict rows / 39 logical dates; 16 placeholders/invalid terms |
| `reverseStock` | 0 | `REVERSE_SPLIT` | Source-level no-row result; no event observed |
| `hmetd` | 64 | `RIGHTS_ISSUE` candidate | Discovery only: subscription price and market-effective semantics absent |
| `sahamBonus` | 13 | `BONUS_SHARES` candidate | Discovery only; event terms/date semantics not complete |
| `Dividen Saham` | 7 | `STOCK_DIVIDEND` candidate | Discovery only; 2 rows have zero amount/total and terms are incomplete |
| `kurangModal` | 21 | `CAPITAL_REDUCTION` candidate | Discovery only; full economic/date semantics not verified |
| `tanpaHmetd` | 44 | `OTHER_SHARE_STRUCTURE` candidate | Discovery only |
| `gabungUsaha` | 7 | `OTHER_SHARE_STRUCTURE` candidate | Discovery only |
| `esopMsop` | 2 | `OTHER_SHARE_STRUCTURE` candidate | Discovery only; two same-date tranche rows |
| `obligasiWajibKonversi` | 3 | `OTHER_SHARE_STRUCTURE` candidate | Discovery only; zero amounts in the listing-history response |

Other returned categories (`ipo`, `waran`, `partialDelisting`, `partialRelisting`,
and `delist`) were retained as source inventory context but are outside the
share-structure canonical action scope for this milestone.

The complete year/category inventory is available in the external audit
capture; the headline counts are:

- 2021: 7 stock splits, 4 HMETD, 1 bonus, 1 capital reduction, 2 without
  HMETD, plus listing/warrant/delisting categories;
- 2022: 11 stock splits, 12 HMETD, 1 bonus, 1 without HMETD, 1 merger;
- 2023: 14 stock splits, 16 HMETD, 2 bonus, 2 stock dividends, 1 capital
  reduction, 6 without HMETD, 2 ESOP/MSOP, 2 mergers, 1 mandatory convertible;
- 2024: 14 stock splits, 10 HMETD, 3 bonus, 2 stock dividends, 6 capital
  reductions, 9 without HMETD, 2 partial relistings;
- 2025: 6 stock splits, 10 HMETD, 4 bonus, 1 stock dividend, 8 capital
  reductions, 15 without HMETD, 2 mergers;
- 2026 through July 31: 4 stock splits, 12 HMETD, 3 bonus, 2 stock dividends,
  5 capital reductions, 11 without HMETD, 2 mergers, 2 mandatory convertibles.

## Duplicate and conflict diagnostics

Repeated `(ticker, action type, TanggalPencatatan)` groups were:

- `BBNI / stockSplit / 2023-10-06`: three source rows; two positive rows
  imply the same 1:2 split and one placeholder row is `0 -> 1`;
- `ISAT / stockSplit / 2024-10-14`: two placeholder rows with zero action
  amounts (`0 -> 1` and `0 -> 0`);
- `BRIS / esopMsop / 2023-03-04`: two source rows with sequential totals.

The strict V1 canonicalizer correctly fails duplicate logical event IDs instead
of choosing silently. These groups need explicit document-level
reconciliation before canonicalization. No direct IDX/Zapi payload conflicts
were found: all 535 ordered rows matched exactly.

## Raw-price diagnostic

The existing 1260-session raw panel was audited without provider corporate
action flags or adjusted fields:

- panel: `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\prices_1260\raw`;
- 932 ticker Parquets, 1,036,575 rows;
- date range: 2021-04-29 through 2026-07-31;
- 40 strict positive official stock-split rows, all ticker files present;
- 38 rows had both a prior and post-date observation; two 2021 events were
  before the panel left boundary and had no prior observation;
- 0 rows matched the mechanical expected post-price ratio within 10% or 20%
  when `TanggalPencatatan` was used as the event date;
- therefore 0 discontinuities are declared explained by a verified action in
  this diagnostic.

This result is deliberately not a claim that the actions did not happen. It
shows that `TanggalPencatatan` cannot be treated as a proven market-effective
session for raw-price adjustment. A separate scan found large raw price jumps,
including repeated Rp1–Rp2 oscillations; those remain quarantined anomalies,
not corporate-action labels.

## Final completeness verdict

| Event type / range | Verdict |
|---|---|
| Official Listing Activity row discovery, all returned categories, 2021-01-01..2026-07-31 | `PASS_CAPTURE_COMPLETE_NOT_IMMUTABLE` — 535 rows at capture; later endpoint revision observed |
| Stock split row discovery, same range | `CONDITIONAL_PASS_REVISION_SENSITIVE` — terms missing/placeholder on 16 of 56 rows; SCMA conflicts with the older persisted 1260 artifact; market-effective semantics still require evidence |
| Reverse split row discovery, same range | `CONDITIONAL_PASS_NO_ROWS_OBSERVED` |
| HMETD, bonus, stock dividend, capital reduction, and other share-structure canonical events | `BLOCKED_CANONICAL_PROMOTION` — source rows found, but required terms and/or market-effective semantics are not established |
| Automatic price adjustment or model use | `NOT_AUTHORIZED` |

External audit summary SHA-256:
`613f89baff086892be8b232b810138dd768e7ec92443baff8dd4186a875f1893`

No OPEN backfill, historical-universe, PIT-sector, model, outcome,
Path-Risk, execution/PnL, or main work was performed.
