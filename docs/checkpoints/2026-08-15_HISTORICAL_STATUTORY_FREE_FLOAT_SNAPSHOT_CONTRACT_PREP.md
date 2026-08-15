# Historical Statutory Free Float Snapshot V1 — Contract Preparation

Date: 2026-08-15 Asia/Jakarta  
Branch: `data/idx-historical-statutory-free-float-snapshot-v1`  
Scientific parent: `data/idx-statutory-free-float-reconstruction-v1@9eb73df879d44456adfc8d5f717e6c75be5d07a0`

## Status

`CONTRACT_PREPARED_RUNTIME_SOURCE_CENSUS_REQUIRED`

This branch defines a PIT-safe observation ledger for **official reported statutory free float**. It does not reconstruct holder eligibility, infer effective/mobile supply, create daily free-float values, or build model features.

## Why this lane exists

The parent bounded audit established that explicit official reported free-float shares and percentages exist in both:

1. issuer LBRE / monthly registration reports; and
2. BEI market-wide free-float status reports.

The parent also established that independently reconstructing statutory free float from holder buckets remains incomplete. Therefore this lane deliberately uses the explicit official values as observations and does not require holder-level reconstruction to admit them.

## Source families remain separate

Two official source families are represented independently:

- `IDX_MARKET_WIDE_FF_STATUS`
- `ISSUER_LBRE`

They are not silently coalesced. If both exist for the same ticker and position date, the current official observations are compared explicitly:

- `AGREE`: exact free-float shares and percentage within a small reporting-rounding tolerance;
- `CONFLICT`: shares differ or percentage difference exceeds tolerance;
- `SINGLE_SOURCE`: only one source family is available.

A conflict is an audit result, not a reason to choose whichever value looks more plausible.

## PIT semantics

Each observation carries:

- `as_of_date`: ownership/report position date;
- `published_at`: official IDX publication knowledge time.

Research availability begins at `published_at`, never retroactively at `as_of_date`.

No daily forward-fill or interpolation is authorized in this lane. A later feature/state contract may define staleness and carry-forward rules after ownership-change-event research is complete.

## Correction semantics

Original and correction records are append-only.

A correction must:

- supersede an already observed record;
- match ticker, position date and source family;
- be published strictly later;
- supersede the exact current record for that source identity.

Unknown, cross-identity, or stale correction lineage fails closed.

A PIT cutoff before a correction sees the original. A cutoff after the correction sees the correction.

## Implemented contract

### `src/idx_trade/historical_statutory_free_float.py`

`HistoricalFreeFloatObservation` requires:

- unique record ID;
- valid ticker;
- position date;
- timezone-aware publication timestamp;
- explicit official free-float shares;
- explicit official free-float percentage;
- optional explicit total listed shares;
- source family;
- revision kind and correction lineage;
- announcement number;
- exact official IDX attachment URL;
- attachment SHA-256;
- metadata-source SHA-256;
- market-wide row locator (`source_row_key`) when one PDF/attachment contains many issuers.

The market-wide row locator is important because hundreds of ticker observations legitimately share one official attachment hash.

`replay_historical_free_float()` enforces publication-time correction state.

`reconcile_cross_source()` keeps issuer LBRE and market-wide observations separate and reports agreement/conflict.

`arithmetic_percentage_difference()` is diagnostic only. It may compare reported `%` to `reported shares / reported total`, but it never replaces the explicit official percentage.

`census_historical_free_float()` reports only observed evidence:

- admitted/current record counts;
- unique tickers;
- exact observed position dates;
- issuer count per observed position date;
- source-family counts;
- correction count;
- cross-source agreement/conflict counts.

It intentionally does **not** manufacture a monthly grid or assume an expected issuer denominator.

### `src/idx_trade/historical_statutory_free_float_io.py`

Strict CSV schema:

```text
record_id
ticker
as_of_date
published_at
free_float_shares
free_float_pct
total_listed_shares
source_family
revision_kind
supersedes_record_id
announcement_no
source_url
source_sha256
metadata_source_sha256
source_row_key
```

The loader requires exact column order, ISO dates, publication timestamps with explicit timezone offsets, explicit official FF shares/pct, and then applies all observation invariants.

## Prepared tests

`tests/test_historical_statutory_free_float.py` covers:

- original → correction PIT replay;
- stale/cross-identity correction failure;
- market-wide row locator;
- shared attachment hash across market-wide ticker rows;
- cross-source agreement;
- cross-source conflict;
- explicit single-source state;
- timezone/causality checks;
- free-float shares not exceeding explicit total;
- diagnostic percentage arithmetic without overwriting official values;
- no synthetic month/forward-fill behavior;
- observation-only census.

`tests/test_historical_statutory_free_float_io.py` covers strict CSV header, non-empty input, timezone parsing, source identity, optional total listed shares, and mandatory explicit FF shares.

Exact branch pytest has not been executed in the ChatGPT connector environment and remains local-runtime work.

## Acquisition strategy

### Stage A — market-wide quarterly anchors first

The parent already hash-pinned two official full-universe reports:

- 2025-12-31 position: `Peng-S-00006/BEI.PLP/02-2026`, 956 parsed rows;
- 2026-03-31 position: `Peng-S-00011/BEI.PLP/04-2026`, 956 parsed rows.

Public/indexed cadence evidence indicates BEI monitoring around quarter-end positions, but V1 must discover exact official full-universe attachments rather than assume every quarter exists.

Search official/preserved IDX announcement metadata for full-universe free-float status reports around:

- 2024-03-31
- 2024-06-30
- 2024-09-30
- 2024-12-31
- 2025-03-31
- 2025-06-30
- 2025-09-30
- 2025-12-31 (already recovered)
- 2026-03-31 (already recovered)
- 2026-06-30 if published by the bounded cutoff.

These are **search targets, not assumed required records**. Preserve true gaps.

Do not mistake a suspension/sanction-only announcement for a row-complete full-universe free-float status attachment.

### Stage B — bounded issuer monthly LBRE census

Issuer LBRE appears monthly and is much larger operationally. Do **not** launch an uncontrolled market-wide monthly download in V1.

Instead, census one recent complete reporting month (prefer 2026-06-30 position if official metadata coverage is available) and answer:

- number of LBRE announcements discovered;
- number with exact official retrievable attachments;
- explicit FF field coverage;
- correction count/rate;
- BAE/template heterogeneity;
- publication-time coverage;
- duplicate/ambiguous issuer-position identities;
- approximate scale of a full monthly historical acquisition.

Use the parent seven-ticker sample as adversarial validation, but do not restrict the census to those seven tickers.

## Reuse, do not redownload blindly

Parent external evidence root:

`D:\Documents\Project\idx-statutory-free-float-reconstruction-20260815-v1`

Parent manifest SHA-256:

`ff25cefed69af8cd221530a23f6fc31e85e0c510a21ef5bfb78526d618a45454`

Reuse verified official bytes/metadata when exact identity and hash match. New history bytes belong in a new external artifact root.

## Acceptance gates

V1 can be considered useful only if:

1. every admitted observation comes from exact official IDX metadata + attachment bytes;
2. publication time is preserved separately from report position date;
3. explicit FF shares and percentage are present;
4. corrections replay deterministically;
5. cross-source conflicts are surfaced rather than overwritten;
6. market-wide anchor attachments are proven row-complete for the rows claimed;
7. history/cadence claims describe observed records only;
8. missing quarters/months remain missing;
9. no daily carry-forward or feature materialization occurs.

## Verdict vocabulary

Use one of:

- `HISTORICAL_STATUTORY_FF_SNAPSHOT_READY_QUARTERLY`
- `HISTORICAL_STATUTORY_FF_SNAPSHOT_READY_WITH_GAPS`
- `HISTORICAL_STATUTORY_FF_SOURCE_REMEDIATION_REQUIRED`

A quarterly-ready verdict does not authorize daily feature use. It only means a defensible official snapshot history exists at the admitted anchor dates.

## Hard boundaries

Do not:

- reconstruct free float from holders in this branch;
- subtract HSC or >=1% ownership;
- infer effective/mobile supply;
- create ownership-change events;
- interpolate or daily-forward-fill free float;
- compute volume/free-float, Foreign Flow/free-float, free-float market-cap features;
- build HHI/concentration features;
- access models, labels, or protected outcomes;
- modify O2, Financial PIT, Corporate Actions, TradingView, or Foreign Flow lanes.
