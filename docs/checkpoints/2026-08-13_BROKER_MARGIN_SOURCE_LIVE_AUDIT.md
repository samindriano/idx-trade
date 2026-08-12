# Broker / Margin Source Live Audit V0

Date: 2026-08-13 (Asia/Jakarta)
Branch: `data/broker-margin-source-audit-v0`
Base commit: `71416509369c4970a04f8bd2ea0d7039bb19b593`

## Decision

`UNRESOLVED_H2_LIKE_CATEGORY_VIEW_NOT_H1_MARGIN_FINANCING_FLOW`

The bounded evidence does not justify interpreting `margin-summary` as actual
margin-financed transaction flow. The safest operational label is
**H2-like category view**: an official IDX Margin reporting view over ordinary
market activity and the applicable margin-eligible universe. Literal H2 as
“the same All Stock rows and metrics filtered by eligibility” is **not proven**
on this date, because the generic metrics differ and 106 eligible names are
absent from the Margin Summary.

Do not derive margin usage, margin share, leverage, crowding, or financing-flow
features from this lane.

## Bounded inputs and provenance

Audit date: `2026-07-14`.

- Zapi Margin Summary: `GET /v1/finance:idx/margin-summary`,
  `length=300,start=0,date=2026-07-14`.
- Zapi All Stock Summary: `GET /v1/finance:idx/stock-summary`,
  `length=1000,start=0,date=2026-07-14`.
- Official eligible list: IDX July 2026 page row and workbook from
  `Peng-00101/BEI.POP/06-2026`, sheet `1.b`, 326 tickers.
- Official raw parity probes:
  `https://www.idx.id/primary/TradingSummary/GetMarginSummary` and
  `https://www.idx.id/primary/TradingSummary/GetStockSummary`.
- The official Stock Summary bundle calls the dedicated Margin endpoint and
  labels its source `IDX Reporting (Regular and Cash)`.

All raw and normalized runtime artifacts are outside Git at:
`D:\Documents\Project\idx-broker-margin-source-audit-20260813`.

## Results

| Check | Result |
|---|---:|
| Zapi Margin rows | 220 / reported total 220 |
| Zapi All Stock rows | 965 |
| official Margin raw rows | 220 / recordsTotal 220 |
| official All Stock raw rows | 965 / recordsTotal 965 |
| Margin tickers inside official eligible list | 220 / 220 |
| eligible tickers | 326 |
| eligible tickers absent from Margin Summary | 106 |
| absent eligible tickers still present in All Stock | 100 |
| absent eligible tickers with positive All Stock activity | 100 |
| absent eligible tickers with no All Stock row | 6 |
| Margin tickers absent from All Stock | 0 |
| all-six generic metrics exactly equal to All Stock | 0 / 220 |

Metric exact counts on the 220-ticker intersection with All Stock:

- High: `59/220`
- Low: `82/220`
- Close: `112/220`
- Value: `0/220`
- Volume: `0/220`
- Frequency: `0/220`

Margin activity metrics never exceeded same-date All Stock on the common
universe: Value `0`, Volume `0`, Frequency `0` cases. Price extrema can differ
because the two reports are different scopes.

## Source parity

Zapi is a faithful wrapper of the official raw endpoints for this probe:

- Zapi Margin vs official `GetMarginSummary`: `220/220` exact on date, High,
  Low, Close, Value, Volume, and Frequency.
- Zapi All Stock vs official `GetStockSummary`: `965/965` exact on date, High,
  Low, Close, Value, Volume, and Frequency.

The raw source confirms that the Margin view is a distinct official IDX
reporting endpoint. Its public fields are ordinary market summary fields; no
margin-loan, financing-account, collateral, or margin-position field was
returned. The official page source explicitly says `IDX Reporting (Regular and
Cash)`. This is strong evidence against H1, but it does not make the strict
All Stock-filter H2 parity gate pass.

Pagination/completeness was bounded and complete for this date: Zapi Margin
reported and returned 220 rows with `length=300`; the official raw Margin call
reported `recordsTotal=recordsFiltered=220` and returned all 220. Zapi All Stock
returned 965 rows with `length=1000`; the official raw endpoint reported 965.
No additional page was needed.

## Period/PIT status

The Zapi Margin payload returned `date=2026-07-14T00:00:00` and retrieval
timestamp `2026-08-12T19:46:25.147Z`. Zapi documents this dataset as a margin
period view rather than a daily financing ledger; the payload itself contains
no publication, effective, or knowledge timestamp. The official eligible-list
evidence is the July 2026 row for `Peng-00101/BEI.POP/06-2026`, but no
defensible PIT knowledge-time mapping was established. Therefore this audit is
not PIT-certified.

## Artifact hashes

External artifact manifest:

- path: `D:\Documents\Project\idx-broker-margin-source-audit-20260813\artifact_manifest_2026-07-14.json`
- SHA-256: `33195286e1fb47d80c96e0ab4dfb84cc85cc6eb2d40787bc7d0488206d8d6664`
- file count: `73`

Key raw artifacts:

- `zapi_margin_summary_2026-07-14.json`: `41d7b24b92054f74b03399ae0e79452eb54ba68c7183146e5dec3fc1ee5ff1d2`
- `zapi_stock_summary_2026-07-14.json`: `699dbc16f19794a32d2b587cd1b22e2dcf76e55b9e8ab61cbfc2deaed7e149b1`
- `official_margin_summary_raw_2026-07-14.json`: `832009b54e8b411dc145190c8e6636f630a4a372a3580943cfe379097334f36d`
- `official_stock_summary_raw_2026-07-14.json`: `196e00eefe53de54b2f598364c973aab6c749fcec8c3e27c652298f8bc462559`
- `official_margin_list_2026-07-14.zip`: `b88b578431d02438726ccf56e09ce907821706ab1593e8c8f91d1c84a1af3685`
- `official_margin_eligible_2026-07-14.csv`: `350c7d2632c2fe3e4bad851ac98c672e307c5b7c9d282d353d30e8b30e4372d4`
- `margin_summary_audit_report_2026-07-14.json`: `0821abe4324dbe8b0dee819e77a90c676aeef3d99b7bf08fdf553dd822398f68`

## Recommendation

Keep this lane out of feature/model development. It is worth retaining as an
official category-level market-summary source only if a future specification
explicitly accepts the H2-like interpretation and separately resolves PIT
effective/knowledge timing. Do not call it margin usage or use it for leverage,
crowding, or execution claims.
