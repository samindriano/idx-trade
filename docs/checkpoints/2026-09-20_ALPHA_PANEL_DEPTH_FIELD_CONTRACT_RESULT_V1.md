# Panel-depth Field Contract Result V1

Status: `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`

This checkpoint records a read-only, isolated-lane field-semantic audit of the
panel-depth source. It does not construct a feature, candidate, score, target,
model, evaluation packet, or production artifact.

## Scope and source

- Source manifest run: `20260919T035510Z`
- Source manifest SHA-256: `e984da79aea14b4a4320ad903a6cf9afbfede94ab1d8dc1e500499462a6ba414`
- Coverage: 12 symbols and 18,835 rows; 11 symbols have 1,616 rows and GOTO has 1,059.
- All 19 expected fields are present and numeric/date-valid for all 18,835 rows.
- Top-level metadata reports `unit=shares` and `valueBasis=close`; this does not
  establish field-level price, value, currency, adjustment, or publication semantics.
- There are no row-level identity, issuer/ISIN, PIT/available-at, revision/vintage,
  or corporate-action fields.
- The source covers only 12 of the 945-symbol panel universe. Official-calendar
  overlap is 14,886/18,835 rows; 3,949 rows are outside that calendar. Official
  parity is available for only 23 pairs on two dates.

## Field contract

| Field family | Observed contract | Status and blocker |
|---|---|---|
| `date` | 1,616 dates; source date only | `PARTIAL`; no knowledge time |
| `open/high/low/close/previous/change` | Numeric and internally shaped as price fields | `UNKNOWN`; adjustment, currency, and price basis are not established |
| `volume` | Non-negative; top-level unit says shares | `PARTIAL`; session aggregation and publication semantics are undefined |
| `value` | Non-negative traded-value-like field | `UNKNOWN`; monetary unit/currency is absent |
| `bid/offer` | Bid/offer-like quote state; both positive on 18,604 rows; 2 rows have positive bid and zero offer; no bid>offer when both positive | `PARTIAL`; quote timestamp/age/depth/zero semantics are absent and price units are unknown |
| `listedShares` | Populated on all rows; 35 values; 23 adjacent transitions over BBCA, BBRI, BMRI, GOTO, KLBF, and MDKA | `PARTIAL`; transition cause, effective timing, issuer/ISIN continuity, and CA/share basis are absent |
| `foreignBuyShares/foreignSellShares` | Non-negative shares; complete row coverage | `PARTIAL`; actor scope, aggregation, publication time, and revision/vintage are absent |
| `netForeignShares` | Exact `buy - sell` arithmetic on 18,835/18,835 rows; 9,519 negative rows | `PARTIAL`; arithmetic is verified, but PIT and actor scope are not |
| `foreignBuyValue/foreignSellValue/netForeignValue` | Non-negative buy/sell values; exact net arithmetic on 18,835/18,835 rows | `UNKNOWN` for value fields; currency/unit and PIT/publication semantics are absent |
| `frequency` | Non-negative; 13,371 distinct values and one zero | `UNKNOWN`; field definition and aggregation meaning are absent |

Structural observations are not provenance authority. In particular, listed-share
transitions do not establish corporate-action events or an adjusted-price basis.

## Novelty and future specification

Bid/offer is a genuinely new raw-input surface relative to the audited incumbent
families, but the mechanism is not admissible without quote timing, age, depth,
and executable semantics. Foreign-flow fields alone remain within the existing
H-FLOW/Foreign Flow family; their arithmetic exactness is not a new information
source. The only justified future specification is:

`FUTURE_QUOTE_FLOW_INTERACTION_V1` — EOD quote-state and foreign-pressure
interaction; `FUTURE_DATA / SOURCE_ADMISSION_BLOCKED / NOVELTY_UNKNOWN`.

It is explicitly not a candidate and no C5 or predictive evaluation was run.
Required future evidence is population-wide PIT/available-at and revision/vintage,
quote timestamp/age/depth/executable semantics, foreign actor scope and monetary
units, identity/ISIN and corporate-action/share-basis authority, and complete
universe coverage with a missingness policy.

## Artifact integrity

- Audit JSON SHA-256: `8625f83b83ea2e4d2072333b0410cdeb4ff01495eb3b4a1245116c080b5080a8`
- Verification JSON SHA-256: `2461dbfdc6df0759529dd402bc233c75550fd0bfd49f30bfec046dd40492aebb`
- Hash contract SHA-256: `6bd6271146e8b1f2ae8986adbb6123ebd2805b6cb242f64c5574836a56383d31`
- Target/privacy firewall SHA-256: `12d24790af0446f37d4026278b1f9a1d95ad9e00ae9892b5f79b1418d2ee3434`
- Builder SHA-256: `2f31b026418bcfc4344f9f9699fb7eef59c93cd99521d359e85c427815b2c938`
- Verifier SHA-256: `895f65dfcf497336594044646a61889eb5a64ef4f30b1c54ac4be1f5b7db7465`

Verifier, generic artifact-hash contract, and target/privacy firewall: `PASS`.
No canonical write, cloud/R2 write, network use, outcome access, model scoring,
feature creation, or incumbent modification occurred.
