# Statutory Free Float Reconstruction V1 — Preparation Checkpoint

Date: 2026-08-15 Asia/Jakarta
Branch: `data/idx-statutory-free-float-reconstruction-v1`
Status: `CONTRACT_PREPARED_OFFICIAL_SOURCE_AUDIT_REQUIRED`

## Objective

Build a defensible point-in-time statutory free-float data foundation for later
volume, liquidity and Foreign Flow research without creating false denominator
precision.

A wrong free-float denominator mechanically contaminates downstream quantities
such as volume/free-float, foreign-net/free-float, turnover, and free-float
market capitalisation. This lane therefore prefers explicit official reported
free float and only permits reconstruction under complete classification.

No HHI, effective-supply score, Foreign Flow feature, model, or outcome work is
authorized here.

## Regulatory rule versions

Free-float semantics are versioned explicitly:

- `IDX_I_A_2021`: historical regime before 2026-03-31.
- `IDX_I_A_2026`: revised regime effective 2026-03-31.

The 2026 reform is anchored by IDX Board Decision
`Kep-00045/BEI/03-2026` and Circular Letter `SE-00004/BEI/03-2026`.

Public legal analysis of the official rules indicates that Regulation I-A 2026
requires free-float shares to be scripless and listed on IDX and, among other
criteria, excludes holdings at/above the ownership threshold, controller or
controller-affiliate holdings, board/director holdings, treasury shares and
shares subject to transfer restrictions. The Circular Letter provides further
transfer-restriction detail. These descriptions are useful for source planning,
but production classification must be pinned to official regulation/circular
bytes recovered in the bounded local audit rather than hard-coded from a
secondary article.

The historical 2021 regime must also be recovered from official bytes before
historical holder-level reconstruction is admitted. The code only versions the
regime boundary; it does not auto-classify holders from role/type/percentage.

## Critical source discovery

### A. BEI market-wide free-float monitoring announcements — preferred

BEI periodically publishes `Status Pemenuhan Kewajiban Jumlah Saham Free Float
dan Jumlah Pemegang Saham` based on issuer `Laporan Bulanan Registrasi
Kepemilikan Saham` (LBRE/Laporan Bulanan Registrasi Pemegang Efek).

Known locator targets from public references include:

- `Peng-S-00006/BEI.PLP/02-2026`, based on position 2025-12-31;
- `Peng-S-00011/BEI.PLP/04-2026`, published 2026-04-30, based on position
  2026-03-31.

The 2025-12-31 attachment is publicly mirrored and visibly contains, per ticker:

- `% Saham Free Float`;
- `Jumlah Saham Free Float`;
- number of shareholders;
- compliance/status fields.

The 2026-03-31 announcement is reported to cover 956 listed companies and is
based on the revised 2026 rule framework.

These market-wide official reports are the highest-value source candidate:
they provide issuer-reported/BEI-monitored statutory free float without needing
the research pipeline to guess holder eligibility.

Required local audit:

- recover official IDX metadata and StaticData bytes;
- confirm exact table schema and row count;
- recover publication timestamp and position/as-of date;
- determine historical cadence and retention depth, ideally 2021–2026;
- preserve correction/revision lineage where present.

### B. Issuer monthly registration reports — preferred for monthly detail

Issuer LBRE/monthly registration attachments can explicitly report free-float
shares and percentage as well as total shares and ownership structure. They are
preferred for monthly state and for explaining corrections between market-wide
BEI publications.

The source audit must determine:

- exact IDX announcement/category locator;
- attachment format/schema variation across BAEs/issuers;
- publication timestamp vs position date;
- correction handling;
- whether explicit free-float shares/pct are consistently present;
- historical retention depth.

### C. `ListingActivity/GetIssuedHistory` — supporting share-count ledger only

Accepted direct-endpoint audit already established that rows provide:
`KodeEmiten`, `TanggalPencatatan`, `JenisTindakan`, `JumlahSaham`, and
`JumlahSahamSetelahTindakan`.

It remains useful as an official candidate share-count/event cross-check but is
not a standalone point-in-time shares-outstanding timeline because publication
semantics and complete action coverage were not established.

### D. Current Company Profile, >=1% ownership, KSEI `BalanceposEfek`, HSC

These source families remain separate:

- Company Profile: current named/controller holders; not historical statutory FF.
- >=1% ownership: ownership concentration/disclosure; not a free-float list.
- `BalanceposEfek`: aggregate local/foreign composition; not statutory FF.
- HSC ledger: regulator-defined high-concentration state; not statutory FF.

None of them is allowed to trigger a subtraction from free float merely because
a holder is disclosed or HSC is active.

## Source hierarchy

For a ticker/as-of date:

1. `OFFICIAL_REPORTED`
   - explicit official BEI/issuer free-float shares and percentage;
   - preserve reported value rather than recomputing from incomplete holders.

2. `RECONSTRUCTED_VERIFIED`
   - only if no suitable explicit official reported snapshot is available;
   - every relevant share is classified under the correct official rule version;
   - `eligible + excluded + unresolved == total_listed_shares`;
   - `unresolved == 0`;
   - exact free float is `confirmed_eligible_shares`.

3. `BOUNDED_ONLY`
   - some shares remain unresolved;
   - no point estimate is permitted;
   - lower bound = confirmed eligible shares;
   - upper bound = confirmed eligible + unresolved shares.

4. `UNRESOLVED`
   - insufficient source evidence to publish even a meaningful interval.

## Implemented fail-closed contract

`src/idx_trade/statutory_free_float.py`

Key objects:

- `FreeFloatRuleVersion`
- `FreeFloatSnapshotStatus`
- `FreeFloatSource`
- `StatutoryFreeFloatSnapshot`
- `official_reported_free_float()`
- `reconstruct_statutory_free_float()`

Hard invariants:

- source URL must be official IDX/KSEI;
- raw source SHA-256 required;
- knowledge timestamp must be timezone-aware;
- as-of date cannot be after publication date;
- rule version cannot cross the 2026-03-31 boundary;
- all share counts are non-negative integers;
- official-reported snapshots preserve official values without fabricated
  reconstruction buckets;
- verified reconstruction requires exact bucket reconciliation and zero
  unresolved shares;
- bounded reconstruction with unresolved shares forbids `free_float_shares`
  and `free_float_pct` point estimates;
- unresolved snapshots expose no numeric free-float values.

This contract deliberately has no API that accepts `sum(holder >=1%)` or HSC
concentration and converts it to free float.

## Tests prepared

`tests/test_statutory_free_float.py`

Covers:

- official reported values remain authoritative;
- unresolved shares force interval-only output;
- complete reconstruction collapses bounds to one exact value;
- bucket arithmetic must close exactly to total listed shares;
- rule-version boundary;
- causal publication time;
- unresolved status cannot leak numeric estimates;
- non-official source URLs fail closed.

Exact branch/full pytest remains local-runtime validation.

## Adversarial audit set

At minimum include:

- `DCII` — extreme HSC/tight-supply case;
- `WBSA` — HSC and recent-listing concentration case;
- `RLCO` — HSC case;
- `BREN` — large-cap / transition free-float case;
- `BBCA` — liquid large-cap control;
- one ordinary non-HSC issuer;
- one issuer with a corrected monthly registration report if available.

For each sample compare:

1. explicit official reported FF shares/pct;
2. total listed shares from the same report if available;
3. holder/category components from the same report;
4. separately available >=1% / Company Profile / KSEI/HSC evidence only as
   diagnostics;
5. whether a reconstruction can reproduce the reported figure without hidden
   assumptions.

A reconstruction mismatch is a blocker. Do not force reconciliation by
reclassifying unknown holders.

## Historical objective

The ideal output is a version-aware, sparse official snapshot history rather
than a guessed daily series:

`ticker, as_of_date, published_at, rule_version, status, free_float_shares,
free_float_pct, total_listed_shares, provenance...`

No daily forward-fill is authorized in this source milestone. A later feature
contract may define availability from publication time onward after source
coverage and revision semantics are accepted.

## Next milestone

Run a bounded local official-source audit/recovery:

1. recover/hash official `Kep-00045/BEI/03-2026` and
   `SE-00004/BEI/03-2026` bytes;
2. recover the official market-wide 2025-12-31 and 2026-03-31 free-float status
   announcements and attachments;
3. search official announcement history for prior market-wide free-float
   reports to establish historical depth/cadence;
4. recover issuer monthly registration reports for the adversarial set;
5. compare official reported values against holder-level reconstructability;
6. determine whether explicit reported history is sufficient for a useful
   historical panel and where only bounded reconstruction is possible;
7. preserve all raw evidence outside Git with a hash-pinned manifest;
8. run focused/full tests and document findings.

No bulk market-wide acquisition beyond what is necessary to audit the source
family is authorized until this bounded result is reviewed.

## Verdict

`CONTRACT_PREPARED_OFFICIAL_SOURCE_AUDIT_REQUIRED`
