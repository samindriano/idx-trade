# Dataset-Saham-IDX Source Admission Audit — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `BLOCKED / NOT_ADMITTED`

## Scope and question

This is a read-only source-admission audit of the newly surfaced external
repository:

`D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX`

The question is whether its OHLCV, foreign-flow, bid/offer, shares, and sector
surfaces can be admitted for historical PIT-safe alpha research. No features
were constructed and no target/outcome was opened.

## Source identity

- Repository commit: `bc0ac7712ce5e46f1067349e13ab9f338883c6c4`.
- Repository tree: `b85e5df6bd941ee1798d78ef1110efd25c66a547`.
- Commit date: `2025-02-23T22:15:58+07:00`.
- `info.json` declares `last_update: 2024-07-19`.
- `info.json` SHA-256: `6c7c6481b69b4a7958a5a76619e4dad668eeed9e4f480ad2d67028ed91b5a30f`.
- README SHA-256: `a680b6f567c306bcf569df5bc96b930d8599cd831ceb9fc844d5394280589858`.
- Column reference SHA-256: `e0d84cefc2d13097ba9d35e24bf5d3c4a136704bbf3d4eee0031f2a31ac7c0a5`.

The README describes manual updates and does not provide a row-level
available-at, publication, revision, or vintage contract. The `info.json`
date is older than the repository commit date. This is provenance uncertainty,
not proof that every row is stale.

## Coverage and calendar checks

The `Saham` subtree contains `1,014` CSV files and `1,146,324` rows. Across
those files:

- `958` distinct filename tickers;
- date range `2019-07-29` through `2025-02-21`;
- `1,356` distinct dataset dates;
- `923` dataset dates intersect the admitted 1,260-session calendar;
- `337` admitted sessions have no date represented in this dataset;
- both `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS` date encodings occur;
- no duplicate dates within a file and no descending adjacent dates were
  observed in the read-only scan.

The calendar result is only a coverage observation. It does not establish
available-at timing or survivorship-safe population membership.

## Identity and duplicate-copy checks

The admitted reconciled security master contains `979` tickers. Four dataset
filename tickers (`CNTX`, `GOTOM`, `MAMIP`, `MYRXP`) were not found in that
master snapshot. The dataset contains `56` duplicate ticker filename groups
across folders; `45` groups are byte-identical, but `11` are non-identical.
Therefore a research consumer cannot select a unique historical row source
from the ticker name alone without an explicit folder/source policy.

The current security master is itself an identity/listing interval aid only; it
does not supply issuer/ISIN transition history or certify the dataset's CA
basis.

## Field and corporate-action checks

All 1,014 daily CSVs share one 25-field schema:

`date, previous, open_price, first_trade, high, low, close, change, volume,
value, frequency, index_individual, offer, offer_volume, bid, bid_volume,
listed_shares, tradeble_shares, weight_for_index, foreign_sell, foreign_buy,
delisting_date, non_regular_volume, non_regular_value, non_regular_frequency`.

The field names provide useful raw surfaces, but there is no row-level
knowledge-time field, no publication timestamp, no revision/vintage identifier,
and no explicit split/right/bonus/conversion event table. `delisting_date` was
not populated in the scanned daily files. `listed_shares` is non-constant in
`438` files, but that field alone cannot identify a corporate-action event or
establish the correct historical price basis. Approximately `1,021,702` rows
contain at least one zero among open/high/low/close; this is a quality/suspension
signal requiring policy, not permission to impute or reinterpret values.

`List Emiten` contains `13` CSVs: `all.csv`, `LQ45.csv`, and 11 sector-named
files. Their documented fields are static listing/sector metadata
(`code,name,listingDate,shares,listingBoard`), not historical PIT sector
intervals or knowledge-time observations.

## Admission decision

| Dimension | Result | Reason |
|---|---|---|
| Source identity | `PARTIAL` | Git identity is pinned, but update/vintage statement is inconsistent. |
| Calendar coverage | `PARTIAL` | 923/1,260 sessions intersect; dataset ends 2025-02-21. |
| Row-level PIT/knowledge time | `UNKNOWN` | No available-at/publication/revision/vintage field or contract. |
| Identity continuity | `UNKNOWN` | Four unmapped tickers and 11 non-identical duplicate copies. |
| Corporate-action basis | `UNKNOWN` | No authoritative event/scale transition table; share-count changes are not event proof. |
| Foreign-flow semantics | `PARTIAL / UNKNOWN` | Fields exist and are documented as totals, but timing, revisions, and historical semantics are not certified. |
| Sector history | `METADATA_ONLY` | Static listing files; no historical interval authority. |
| Historical alpha admission | `BLOCKED` | Multiple required PIT/identity/CA gates remain unresolved. |

## Safe conclusion and next action

Do not use this repository to construct an admitted alpha feature, repair the
canonical panel, or resolve C1/C2/C4/H-LIQ price-basis questions. It may remain
an explicitly blocked capability reference. A future re-review would require
an independent source contract covering row-level knowledge time, duplicate
folder selection, identity/issuer continuity, foreign-flow timing, sector
intervals, and corporate-action/scale semantics.

No provider/network/cloud/capture/telemetry/scheduler state was touched. No
protected outcome or target was accessed.
