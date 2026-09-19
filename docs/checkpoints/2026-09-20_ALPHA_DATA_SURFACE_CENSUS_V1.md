# Local data surface census — 2026-09-20

Lane: isolated `codex/alpha-available-data-20260919`
Scope: read-only inventory of locally staged acquisition artifacts. No network,
feature construction, candidate creation, target/outcome access, or mutation of
canonical/active data.

## Inventory boundary

The census covers four manifests, 26 normalized JSON files, and 25 raw response
files under
`D:/Documents/Project/idx-alpha-data-acquisition-staging-20260919/`. All 25
persisted raw files match their manifest SHA-256 values. One Stockbit stream
response is intentionally privacy-redacted and has no persisted raw payload.

| Surface | Classification | Evidence and limitation |
|---|---|---|
| `panel-depth` IDX history | `PARTIAL / ADMISSION_BLOCKED` | 12 tickers, 18,835 rows, 2020-01-02–2026-09-18; OHLCV, bid/offer, listed shares, foreign flow; no row-level PIT/revision/vintage/ISIN/issuer/CA. |
| Historical IDX BBCA | `PARTIAL / DUPLICATE` | 1,616 rows; exact normalized rowset duplicate of panel-depth BBCA. |
| TradingView BBCA max | `PARTIAL / ADMISSION_BLOCKED` | 6,356 rows, 2000-05-31–2026-09-18; static ISIN and adjustment metadata, but no available-at/revision/CA-event contract. |
| Investing BBCA max | `PARTIAL / ADMISSION_BLOCKED` | 2,065 rows, 2018-08-08–2026-09-18; no local basis/adjustment explanation and no PIT contract. |
| Official IDX summary | `PARTIAL / CROSS-CHECK ONLY` | 671 rows on 2020-01-02 and 963 on 2026-09-18; only two snapshots, no vintage history. |
| Current foreign flow | `PARTIAL / SNAPSHOT ONLY` | 20 rows of the 2026-09-18 snapshot; not historical PIT data. |
| Current stock summary | `PARTIAL / SNAPSHOT ONLY` | 20 rows; not an independent historical surface. |
| Active listings | `METADATA_ONLY` | 962 listing rows with listing date/shares; no historical membership or transition log. |
| IDX investor-type page | `METADATA_ONLY` | HTML received and hashed, but no embedded historical table or dated data. |
| TradingView technicals | `METADATA_ONLY` | One BBCA snapshot of scalar indicators; no date history or PIT publication contract. |
| Stockbit chart | `PARTIAL / CURRENT-INTRADAY` | 60 BBCA items for `today`; not daily historical OHLCV and no PIT/CA contract. |
| Stockbit stream | `METADATA_ONLY` | Five redacted metadata items; no persisted raw response. |

No surface is `ADMISSIBLE`. The only non-redundant deep-history surfaces are
TradingView BBCA max and Investing BBCA max; their basis reconciliation is
recorded separately in `2026-09-20_ALPHA_BBCA_PRICE_BASIS_RECONCILIATION_RESULT_V1.md`.

## Manifest anchors

| Manifest | SHA-256 |
|---|---|
| `historical-depth/20260919T035159Z/manifest.json` | `4f3e22128a8c2e1885f0a3dbd5e5fbcc3f33425fa11b5b01f37427647782d036` |
| `panel-depth/20260919T035510Z/manifest.json` | `e984da79aea14b4a4320ad903a6cf9afbfede94ab1d8dc1e500499462a6ba414` |
| `official-idx-summary/20260919T035641Z/manifest.json` | `662c005ba6fea49a7c34fc1681652f0530d20e4d2cd091c46ebf286f964362b1` |
| `runs/20260919T034636Z/manifest.json` | `8a783051cd043184ff6e36832461eaba047bcdf26f57cac7a2f0d9beebac8eff` |

## Next high-information frontier

Reconcile TradingView BBCA max against IDX and Investing using only these local
payloads and existing CA/issuer artifacts. Specifically explain the stable
TradingView 5x/1x basis blocks and the variable Investing scale without
declaring a corporate-action truth or admitting either source. Do not repeat
the panel-depth duplicate audit, scrape providers, or construct features from
these surfaces.
