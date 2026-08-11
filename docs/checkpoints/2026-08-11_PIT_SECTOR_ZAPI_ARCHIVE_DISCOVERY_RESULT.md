# PIT Sector Zapi and Official Archive Discovery Result

Date: 2026-08-11
Branch: `data/idx-pit-sector-history-v1`
HEAD at investigation: `f5689ee0f7e6faafaf2496786994590b6f27a108`
Scope: PIT sector-history source discovery only

## Decision

**BLOCKED - inventory remains 5 `READY_FOR_ACQUISITION` / 3
`DISCOVERY_REQUIRED`.**

No canonical source was promoted. No announcement reference or effective date
was inferred. The three remaining blockers are still:

1. dedicated annual 2022 IDX-IC classification source;
2. dedicated annual 2023 IDX-IC classification source;
3. explicit official effective-date evidence linked to
   `Peng-00100/BEI.POP/06-2026`.

## 2026 issuer-history investigation

The existing Zapi company-announcement captures cover the full requested
window from 2026-06-24 through the latest available records on 2026-08-11.
The returned pages are the latest 100 records, and each page's oldest record is
already before the requested window.

| Issuer | Total upstream records | Returned | Oldest returned | Window rows | Classification matches |
|---|---:|---:|---|---:|---:|
| ARGO | 116 | 100 | 2024-04-01 | 6 | 0 |
| HRUM | 134 | 100 | 2024-05-31 | 8 | 0 |
| PACK | 401 | 100 | 2026-02-23 | 25 | 0 |

The classification-match search covered announcement number, title and
subject for `Perubahan Klasifikasi Industri`, `Klasifikasi`, `Industri`,
`IDX-IC`, and `Peng-00100`. No later issuer disclosure referenced or clearly
linked to `Peng-00100` and stated an effective date.

The Zapi raw passthrough probes for ARGO, HRUM and PACK also returned
`ResultCount=0` for the classification/industry/IDX-IC searches over
2026-06-24 through 2026-08-11. The official canonical source remains:

- reference: `Peng-00100/BEI.POP/06-2026`;
- official ZIP:
  `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/No.%20Peng-00100_BEI.POP_06-2026-ID.zip`;
- ZIP: 290,000 bytes,
  SHA-256 `d95b27f4bab74a2da9ab737c3bdd96bc4626cfb97635ffa32a9449be78d7db98`;
- extracted PDF: 312,989 bytes,
  SHA-256 `8b5413f18afc75cc17260c2400611d710e8f270d46a49c5a396f557b27cf8b25`.

The canonical PDF lists issuer classification changes but does not state an
effective date. `Peng-00099/BEI.POP/06-2026` remains sector-index
reconciliation evidence and cannot establish the issuer classification date.
Therefore `effective_from`, `knowledge_at`, and the PIT usability boundary
remain unresolved. In particular, neither 2026-06-24 nor 2026-07-01 was
backdated or inferred.

## 2022 and 2023 Zapi/archive investigation

The already-exhausted public `NewsAnnouncement/GetAllAnnouncement` queries
were not repeated. Existing Zapi raw captures remain:

| Window | Zapi/raw result | SHA-256 of captured JSON |
|---|---|---|
| 2022-06-01 through 2022-07-31 | `Items=[]`, `ItemCount=0` | `d142b5295d58541100f13d4823a62658dfb7821ea9d789891bdcc457eb71f06b` |
| 2023-06-01 through 2023-07-31 | `Items=[]`, `ItemCount=0` | `675a131473a448eee98eb32ae7c3c6aa042f0070aa9dec5a962d619c15c422f` |

Zapi's documented raw passthrough supports an IDX `/primary/...` path plus a
raw query, but the bounded probes did not expose a historical canonical
announcement or an official attachment for either annual event. A bounded
issuer-path probe for the 2022 window produced no capturable response and was
not used as evidence for promotion.

The previously acquired official packages remain explicitly non-canonical
reconciliation evidence:

- `Peng-00150/BEI.POP/06-2022`: 1,266,053 bytes,
  SHA-256 `1f13b7b3cdc75ed22b9848c08666a18488690009a98aaaa6586f745a6e9c18be`;
- `Peng-00156/BEI.POP/06-2023`: 687,933 bytes,
  SHA-256 `da4589ee59889e606e5f8cd26cce19b119107e1a89bd9aa13b763b9071a06aca`.

Neither package was promoted as a canonical issuer-classification event.

## Archive boundary and next route

The public IDX frontend documents a three-year announcement-history boundary
and directs older history to TICMI. The official TICMI data-services page
exposes the TICMIDATA route (`https://ticmidata.co.id/`) and describes
historical capital-market data and special data requests. This is the next
highest-value official archive path for 2022/2023, subject to authorized
account/data access. It must be used to obtain the actual official document or
an immutable official archive identity; a TICMI/Zapi metadata row by itself
will not satisfy the PIT provenance contract.

## Boundaries and validation

- No config inventory entry changed.
- No tests were changed or run in this documentation-only discovery pass.
- No parser/materialization, IPO or incidental census, model, outcome,
  OPEN-backfill, Path Risk, execution/PnL, paper/live, or `main` work was
  started.
- External discovery captures remain outside Git under
  `D:\Documents\Project\idx-pit-sector-official-raw-20260811\zapi-audit`.
