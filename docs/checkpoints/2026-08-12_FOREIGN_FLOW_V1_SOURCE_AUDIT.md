# Foreign Flow V1 Source Audit — 2026-08-12

Status: bounded source audit complete; bulk acquisition is not authorized.

Branch: `data/foreign-flow-v1`

## Decision summary

| Gate | Result | Meaning |
|---|---|---|
| Source discovery | PASS | Zapi foreign-flow and raw passthrough resolve the official IDX stock-summary source. |
| Unit semantics | PASS | The wrapper declares `shares`; its values match official IDX `ForeignBuy`/`ForeignSell` fields. |
| Buy/sell/net semantics | PASS | `netForeignShares = foreignBuyShares - foreignSellShares` for every sampled row. |
| PIT timing | NOT PROVEN | The observation payload contains a session date but no source publication/update time. Zapi `timestamp` is access time, not observation knowledge time. |
| Historical coverage complete | INCOMPLETE | Six representative sessions were complete relative to the returned Stock Summary, but market-wide date-by-date completeness and historical knowledge times are not proven. |
| Ready for bulk acquisition | NO-GO | Do not promote session date to same-day `knowledge_at` and do not bulk-fill a PIT panel yet. |

Overall verdict: `SOURCE_AND_UNIT_USABLE_BUT_PIT_TIMING_UNRESOLVED_COVERAGE_INCOMPLETE`.

Raw Zapi and official captures are outside Git at:
`D:\Documents\Project\idx-trade-foreign-flow-20260812`.

No foreign-flow features, models, outcomes, or execution/PnL work was performed.

## Preflight and minimal fix

- Initial focused run exposed a real validation-order defect: a deliberately invalid row was rejected as `knowledge_at precedes published_at` before the more fundamental `knowledge_at precedes its trading session` diagnostic.
- Minimal fix: validate the session lower bound before the optional publication lower bound. The Foreign Flow V1 contract itself was not changed.
- Focused: `python -m pytest tests/test_foreign_flow.py -q` → **7 passed**.
- Full: `python -m pytest -q -rA` → **478 passed, 0 failed, 3 warnings, 30.86s**.
- The three warnings are existing pandas `FutureWarning`s in `curated_identity.py` and `tradability_anchor_reconstruction.py`.

## Exact source path

Zapi wrapper:

`GET https://api.zpi.web.id/v1/finance:idx/foreign-flow`

Parameters used:

- `date=YYYY-MM-DD`
- `sort=code`
- `length=200` (documented maximum for this wrapper)
- `start=0,200,...` until returned `total` is covered.

Zapi raw passthrough:

`GET https://api.zpi.web.id/v1/finance:idx/raw?path=TradingSummary/GetStockSummary&query=...`

Upstream query used:

`date=YYYYMMDD&indexFrom=0&pageSize=1000`

The upstream official IDX endpoint is:

`https://www.idx.co.id/primary/TradingSummary/GetStockSummary`

The direct `www.idx.co.id` request returned HTTP 403 from this network. The same official endpoint on the accessible IDX block mirror returned the complete JSON payload and was used for byte/hash comparison. The original `www.idx.co.id` URL remains the canonical source URL; the mirror is a transport workaround, not a second market-data authority.

The public Zapi reference documents the wrapper as daily per-security foreign flow, with `shares` as the unit, and documents the raw Stock Summary fields and pagination: [Zapi IDX API reference](https://zpi.web.id/api/finance/idx).

## Field and unit semantics

Zapi foreign-flow fields:

- `code` → ticker;
- `date` → exchange session date;
- `foreignBuyShares` → official IDX `ForeignBuy`;
- `foreignSellShares` → official IDX `ForeignSell`;
- `netForeignShares` → calculated buy minus sell;
- response `unit` → `shares`.

The official raw Stock Summary payload does not carry a separate net field. For all six sampled sessions and all returned tickers, the identity held exactly:

`ForeignBuy - ForeignSell = netForeignShares`.

The exact foreign fields from Zapi matched the direct official payload for **5,231 / 5,231 rows** across the audit. All six sessions had zero mismatches.

No lots or IDR conversion was performed. The canonical contract should use `SHARES` only for this source.

## Six-session cross-check

Each session was queried through the paginated Zapi foreign-flow wrapper, Zapi Stock Summary wrapper, Zapi raw passthrough, and direct official IDX block mirror.

| Session | Foreign-flow rows | Stock Summary rows | Raw rows | Direct IDX rows | Zero-flow rows | Zero-volume rows | All parity/mismatch checks |
|---|---:|---:|---:|---:|---:|---:|---|
| 2021-01-04 | 717 | 717 | 717 | 717 | 438 | 81 | PASS, 0 mismatches |
| 2022-06-24 | 790 | 790 | 790 | 790 | 390 | 82 | PASS, 0 mismatches |
| 2023-06-22 | 871 | 871 | 871 | 871 | 365 | 91 | PASS, 0 mismatches |
| 2024-06-21 | 930 | 930 | 930 | 930 | 427 | 105 | PASS, 0 mismatches |
| 2025-06-30 | 960 | 960 | 960 | 960 | 394 | 130 | PASS, 0 mismatches |
| 2026-07-31 | 963 | 963 | 963 | 963 | 304 | 133 | PASS, 0 mismatches |

Across every session:

- no duplicate ticker rows;
- no invalid buy/sell/net identities;
- no date mismatch in Stock Summary rows;
- foreign-flow ticker set exactly equaled Stock Summary ticker set;
- Zapi raw Stock Summary fields exactly matched the direct official payload for the checked fields: `Date`, `StockCode`, `ForeignBuy`, `ForeignSell`, `Volume`, `Value`, `Frequency`.

## Missing-row semantics

The sampled foreign-flow result did not omit any row that was present in the same-date Stock Summary. It includes rows with zero foreign activity and rows with zero trading volume.

This matters because zero foreign flow is not equivalent to no trade:

- zero foreign-flow rows: 304–438 per sampled session;
- zero-volume rows: 81–133 per sampled session;
- the difference consists of rows with zero foreign flow but positive volume.

Therefore:

- a returned row with `ForeignBuy=ForeignSell=0` is a valid zero-flow observation, not a missing observation;
- an absent row in a future capture cannot safely be interpreted as zero flow, no trade, suspension, or delisting;
- missing rows must remain `UNKNOWN` until reconciled against the complete same-date official Stock Summary/security scope;
- Stock Summary is the completeness witness for this source, not the foreign-flow wrapper's row count alone.

## Historical date coverage and pagination

The endpoint returned complete same-date snapshots for all six representative exchange sessions spanning 2021-01-04 through 2026-07-31. Returned row counts rose from 717 to 963 as the listed universe changed over time.

This demonstrates historical reachability, not a proven complete daily archive. No exhaustive session-by-session census was performed in this bounded audit. The strongest bounded observation statement is therefore: **the source is reachable and internally complete relative to Stock Summary on the six sampled sessions; no market-wide historical completeness window is certified.**

## Revision sensitivity

The old session 2022-06-24 was queried twice through the foreign-flow wrapper and twice through raw Stock Summary. The repeated foreign-flow first-page payloads had identical SHA-256 and identical canonical row content; the repeated raw Stock Summary payloads also had identical SHA-256 and identical canonical row content.

This is evidence of repeat stability for one old session, not proof that historical values are immutable. The endpoint exposes no revision/version identifier. A production acquisition must preserve raw payload hashes and permit later versions at distinct knowledge times rather than overwrite prior observations.

## Publication and knowledge-time semantics

The official Stock Summary rows contain `Date` and market fields, but no publication/update timestamp. The Zapi response includes a top-level `timestamp`, but that is the API response/access time; it changes with the request and is not evidence that the observation became public at that time.

Consequences:

- `session_date` must not automatically become same-day `knowledge_at`;
- no same-day close, next-session open, or arbitrary end-of-day timestamp was invented;
- exact historical decision-time PIT is **not currently promoted**;
- the only defensible interim bound is `knowledge_at >= capture_time`, where capture time is recorded for a preserved raw payload. This is an upper bound on availability, not the first-knowable time.

## Contract mapping smoke check

A three-row sample from official Stock Summary (BBCA on 2021-01-04, 2024-06-21 and 2026-07-31) was mapped in memory to `canonicalize_foreign_flow` with `unit=SHARES`, `published_at=NaT`, and the respective Zapi capture timestamp as a conservative capture-time `knowledge_at`. The sample passed the buy/sell/net and timezone-aware `foreign_flow_asof()` checks:

- before the earliest capture: 0 visible rows;
- after the latest capture: 3 visible rows;
- no source publication time was claimed.

## Evidence hashes

Official IDX block mirror payload SHA-256:

- 2021-01-04: `eebc719917998389b8297e520099fbd486d2d9a1dde914d749e5c18a2927c554`
- 2022-06-24: `5fba88121d60845fc3e29462b05cf788c40d518dbe27fc11afa107cb7fd51833`
- 2023-06-22: `e61baa61926ed8aa80047c7fd0e7fac3eb2c8815e95664c2ebdd2b190f0adc27`
- 2024-06-21: `cdb00f3a4caa73d0e745bc1bc8f0a0745bd3c730da82e60c8071164f48b6e4fc`
- 2025-06-30: `e15a081868bbd9469f60c26ddb7fc2c4cf851b259a8b234b0d3bc95b611600cc`
- 2026-07-31: `684a435c8b911cb5805308d8502139ed6c6da519808c18a672493c244b93f53a`

Zapi raw passthrough payload SHA-256:

- 2021-01-04: `ceb65b37f45011adbffba778f888644425e5f12d0d9d9db6e5db18ee9166a8d7`
- 2022-06-24: `0b76bc91f0773d32e0cd590caac588804057ba437b7c8ed7eba95bdf7579a4fb`
- 2023-06-22: `4b81e2c4ca6863bc0edefc0c3785450983d142f6ac40ee4689be9fbc49486361`
- 2024-06-21: `3c541f6367b0a495623234fdd057ec5b4cef77adb29461870719b020a7e431cf`
- 2025-06-30: `6f0cce6b82e902af0757fead835be92ddc9eff99ad10ce28649e88f48dd82740`
- 2026-07-31: `b0c580ad2c92cf99769f28a3adf1ea7a3a06171674d209bc6b7891c3c1307508`

Repeated 2022-06-24 first-page foreign-flow response SHA-256: `46f09628edd1bca20e0e7ef5b07c4ae7e99822ab5dedaec13e37246fc27893d0` on both captures. Repeated complete raw Stock Summary response SHA-256: `0b76bc91f0773d32e0cd590caac588804057ba437b7c8ed7eba95bdf7579a4fb` on both captures.

## Remaining blockers / next safe step

1. Preserve capture-time bounds, but do not treat them as publication times.
2. Find an official IDX publication/update event or a defensible daily release schedule before exact historical PIT use.
3. If no timing source exists, define a separate non-PIT diagnostic use rather than weakening this contract.
4. Run a bounded session census against the official calendar and security scope before claiming historical completeness.
5. Preserve raw versions and compare later recaptures for revisions.

No bulk acquisition is authorized by this audit.
