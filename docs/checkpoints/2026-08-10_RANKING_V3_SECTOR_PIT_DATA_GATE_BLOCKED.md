# Ranking V3-D PIT Sector Data Gate - Blocked

Date: 2026-08-10 (Asia/Jakarta)

Status: **BLOCKED_PIT_SECTOR_HISTORY**

Repository: `samindriano/idx-trade`

Branch: `research/idx-ranking-v2-spec-v1`

HEAD at audit: `1d62d8b73a3055a730e958178717a4910741f194`

## Scope completed

This checkpoint records only the outcome-independent V3-D pre-run review. The
amended-tree full test suite was run. No sector-history validator, V3-D cache
prepare, V3-D score, V2F5/V2F6 access, or forward-outcome access was performed.

## Validation

- full repository pytest: `290 passed, 0 failed, 3 warnings`;
- duration: `26.2 seconds`;
- branch clean and synchronized with `origin/research/idx-ranking-v2-spec-v1`;
- no `FORWARD_OUTCOME_ACCESS_STARTED` marker was written.

## Frozen identities retained

The following required V3-D inputs remain unchanged and were not materialized
into a new runtime cache because the PIT sector gate blocked first:

- signal panel: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`;
- V2 prepared table: `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- V2 prepared manifest: `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`.

No normalized sector-history SHA, cache SHA, or cache-manifest SHA exists for
this blocked attempt.

## Source audit

### Sources located

1. IDX stock classification page: `https://www.idx.id/en/products/stocks/`.
   It states that IDX-IC is implemented from 2021-01-25 and describes the
   taxonomy, but it is a current classification page, not a historical
   ticker-by-date interval archive.
2. IDX stock-list page: `https://www.idx.id/en/market-data/stocks-data/stock-list/`.
   It exposes a current sector-filtered stock list; no historical effective
   interval or publication-availability field was available in the retrieved
   page.
3. Official IDX monthly Table of Stock Price API, for example:
   `https://www.idx.id/primary/DigitalStatistic/GetApiDataPaginated?urlName=LINK_TABLE_STOCK_PRICE&periodYear=2024&periodMonth=11&periodType=monthly&isPrint=False&cumulative=false&pageSize=10&pageNumber=1&orderBy=&search=`.
   The response contains sector and ticker rows for a report month, but does
   not provide the classification's exact `effective_from`,
   `effective_to_exclusive`, or a reliable public `available_at` timestamp.

### Sources rejected for PIT use

- local `D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX\List Emiten\Sectors\*.csv`
  files are current sector-list snapshots with listing metadata only;
- current IDX stock-list/current sector pages cannot be backfilled into the
  historical signal window;
- a monthly report-month label cannot safely be promoted to an exact economic
  classification-effective date or publication availability timestamp;
- no immutable official ticker-level PIT sector-history archive with
  independently verifiable source bytes/hash was found in the repository or
  the existing `D:\Documents\Project` IDX data workspaces.

Because the required source semantics are not established, constructing rows
with guessed dates, current labels, or assumed availability would violate the
V3-D specification. No sector-history file was fabricated.

## Gate decision

`BLOCKED_PIT_SECTOR_HISTORY`

The required sector-history contract cannot be proven:

```text
ticker
sector_code
effective_from
effective_to_exclusive
available_at
source_id
source_sha256
```

Consequently:

- `validate-history` was not run against a fabricated artifact;
- V3-D prepare was not run;
- no F1-F4 sector assignment or feature-coverage metrics exist;
- no control/candidate outcome metrics exist;
- no V3-D candidate ordinal was evaluated; cumulative evaluated count remains 7;
- V3-C remains `V3_C_REGIME_KILL_KEEP_V2_CONTROL`;
- V3-D ordinals 008/009 remain unviewed and unauthorized.

## Required next action

Obtain or build an official immutable historical IDX sector-classification
archive that explicitly supports effective-date and availability semantics,
then independently hash and validate it before any V3-D cache prepare. Do not
use current-sector backfill or assumed report-month dates to bypass this stop.

