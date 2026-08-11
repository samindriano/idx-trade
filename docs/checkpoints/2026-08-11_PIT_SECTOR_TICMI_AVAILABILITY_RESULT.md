# PIT sector TICMI/TICMIDATA availability investigation

Date: 2026-08-11 (Asia/Jakarta)  
Branch: `data/idx-pit-sector-history-v1`  
Scope: public TICMI/TICMIDATA availability only; no purchase or authentication

## Decision

`TICMI_PUBLIC_METADATA_INSUFFICIENT_FOR_PROMOTION`

The public TICMI/TICMIDATA surfaces confirm that historical capital-market data
and a custom-data route exist, but they do not expose a searchable, immutable
record for either missing annual IDX-IC announcement. No announcement ref,
attachment URL, source bytes, SHA-256, or effective-date evidence was
recovered. The PIT inventory remains **5 `READY_FOR_ACQUISITION` / 3 blocked**:

- dedicated annual 2022 IDX-IC classification source;
- dedicated annual 2023 IDX-IC classification source;
- explicit official effective-date evidence linked to
  `Peng-00100/BEI.POP/06-2026`.

No inventory entry was promoted and no date was inferred.

## Bounded public-only method

The investigation used only publicly reachable pages, sitemap metadata, and
page/frontend metadata. It did not create an account, submit credentials,
attempt to bypass authentication, purchase data, or inspect authenticated
requests.

Checked public surfaces:

- IDX terms of use, which state that company information older than three years
  is obtained through TICMI;
- TICMIDATA sitemap and public application shell;
- TICMIDATA public information page and its visible login/register,
  subscription, and help links;
- public TICMI data-service terms describing general and special data services;
- the current TICMI routes referenced by those terms.

The current TICMIDATA sitemap publicly lists the following relevant application
routes:

```text
/pricing
/pay_per_use
/data_custom
/document_area
/area-pelanggan
/market_overview/*
/news
```

The root and these application routes return the Flutter application shell. The
public HTML does not contain an announcement index, historical search result,
announcement reference, or attachment metadata for the 2022/2023 targets.
The public information page exposes the product/support surface, but not the
underlying historical records.

The older TICMI terms still point to:

```text
https://ticmi.co.id/datapasarmodal
https://ticmi.co.id/datapasarmodal-lainnya
```

Both paths returned HTTP 404 in the current public deployment. This is a
deployment/availability observation, not evidence that the underlying archive
does not exist.

## What can be identified before purchase

| Question | Public result |
|---|---|
| Does TICMI/TICMIDATA appear to have historical market-data capability? | Yes. The public TICMI terms describe capital-market data since 1977, and the IDX terms direct older company history to TICMI. |
| Can the 2022 annual IDX-IC record be identified by title/ref/attachment? | No. No public search result or metadata record was exposed. |
| Can the 2023 annual IDX-IC record be identified by title/ref/attachment? | No. No public search result or metadata record was exposed. |
| Is there a route for data not available in the general service? | Yes. TICMI terms describe `Layanan Data Khusus` with custom processing and `.xlsx`/`.txt`/`.pdf` output. |
| Is an exact single-file quote/price visible publicly? | No. The public app shell did not expose a usable price or fulfillment listing. |

The least-expansive request to TICMI should therefore be a **custom/special
data request**, asking for the two exact historical Exchange announcements,
not a broad market-data package. The request should explicitly ask TICMI to
confirm whether it can provide, for each target:

1. the dedicated annual IDX-IC Exchange announcement, not a sector-index
   reconciliation package;
2. official announcement reference, title, announcement timestamp, and
   attachment identity/path;
3. the original file or an immutable official archive identity;
4. SHA-256/hashable source bytes and explicit effective-date wording; and
5. publication/availability date so the PIT knowledge-time rule can be
   applied.

The public terms identify `data@ticmi.co.id` and `(021) 5152318` for data
questions. Public availability does not guarantee that TICMI will fulfill the
request or that the result will be individually priced; that requires a direct
quote/availability response. No purchase was made.

## 2026 boundary

The 2026 search remains bounded and exhausted for now:

- canonical `Peng-00100/BEI.POP/06-2026` exists;
- its canonical PDF has no explicit effective date;
- no linked ARGO/HRUM/PACK evidence was found through 2026-08-11;
- `Peng-00099/BEI.POP/06-2026` remains sector-index reconciliation evidence
  only and cannot supply the missing issuer-classification date.

No new 2026 discovery was performed in this task.

## Fail-closed policy for permanent source resolution failure

If official IDX escalation, TICMI/TICMIDATA custom/archive request, and any
later approved immutable official archive route all fail to recover a required
source, the project should record the item as
`PIT_SECTOR_SOURCE_UNRESOLVED_PERMANENT` only after an explicit review decision.
Until then it remains `DISCOVERY_REQUIRED`.

The required behavior is:

- do not promote the source or complete the PIT sector-history inventory;
- do not invent an effective date, backfill current sector membership, or use
  a sector-index reconciliation document as canonical issuer history;
- keep the affected ticker/date assignment `UNKNOWN` and fail the sector data
  gate for any downstream feature contract that depends on complete history;
- do not materialize or score V3-D sector-relative features from incomplete
  history; and
- preserve the unresolved item, attempted routes, and evidence of exhaustion
  in the ledger for a future separately authorized decision.

This policy permits the alpha/V3-B lane to remain frozen and unaffected. It
does not authorize a partial sector-model run or a silent downgrade of the PIT
contract.

## Validation and boundaries

This was a documentation-only availability investigation. No source inventory,
parser, materialization code, tests, model, outcome, OPEN backfill, Path Risk,
execution/PnL, or `main` branch was changed. No pytest run was required because
no executable code or inventory contract changed.
