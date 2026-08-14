# Free Float / Effective Supply V1 — Source Preparation Checkpoint

Date: 2026-08-15 Asia/Jakarta
Branch: `data/idx-free-float-effective-supply-v1`
Status: `SOURCE_PREPARED_BOUNDED_LIVE_AUDIT_NEXT`

## Purpose

Prepare defensible ownership/free-float source acquisition for later liquidity, volume, and Foreign Flow research without inventing a historical `true free float` series.

This lane is source/data-foundation work only. It does **not** derive an effective-float percentage, supply-tightness score, model feature, or outcome/performance result.

## Why this matters

Reported/statutory free float and economically mobile trading supply are not guaranteed to be identical. Concentrated named holders can make the tradable supply materially tighter than a headline free-float percentage suggests. For a research stack that relies heavily on volume, turnover, liquidity and foreign flow, ownership concentration is therefore a potentially important conditioning variable.

The immediate objective is to preserve observable ownership facts first. Any later `effective_supply` inference must be separately specified and validated.

## Source hierarchy prepared

### A. IDX Company Profile Detail — current named-holder snapshot

Reference implementation audited: `nichsedge/idx-bei@75d6c0f74fa360d225794c70c383348977de6798`, `python/src/idx/scrapers/company.py`.

Endpoint contract:

- `GET https://www.idx.co.id/primary/ListedCompany/GetCompanyProfilesDetail`
- params: `KodeEmiten`, `language=id-id`
- relevant object: `PemegangSaham`
- observed/reference holder fields: `Nama`, `Jumlah`, `Persentase`, `Pengendali`, `Kategori`

Repo implementation:

- `src/idx_trade/providers/idx_ownership.py`
- raw response bytes preserved
- SHA-256 preserved
- retrieval start and observed-available timestamps preserved
- strict ticker/share/percentage/controller parsing
- missing `PemegangSaham` fails closed; explicit empty list remains an explicit empty snapshot

Scientific boundary:

- this endpoint is treated as a **current named-holder snapshot**;
- it is not backdated;
- no historical availability is inferred;
- no free-float complement is calculated from `PemegangSaham`.

Status: `READY_FOR_BOUNDED_LIVE_PROBE`.

### B. KSEI/BEI public ownership >=1% disclosure — named concentration evidence

KSEI/BEI announced the public disclosure of shareholders owning at least 1% on 2026-03-03. The KSEI announcement states that KSEI supplies the information and it is published monthly through the IDX website.

A public research mirror in `nichsedge/idx-bei` contains `data/1%ownership-2025-03-04.csv`, but the embedded `DATE` values sampled from the file are `27-Feb-2026`. Therefore the mirror filename is explicitly **not authoritative for as-of date**.

The parser uses only the embedded `DATE` column as the snapshot date and normalizes:

- `SHARE_CODE`
- `INVESTOR_NAME`
- `INVESTOR_TYPE` **or** `INVESTOR_CLASSIFICATION` (schema aliases; exactly one required)
- `LOCAL_FOREIGN`
- `NATIONALITY`
- `DOMICILE`
- `HOLDINGS_SCRIPLESS`
- `HOLDINGS_SCRIP`
- `TOTAL_HOLDING_SHARES`
- `PERCENTAGE`

Fail-closed invariants include:

- exactly one embedded snapshot date per file;
- integer non-negative share counts;
- `HOLDINGS_SCRIPLESS + HOLDINGS_SCRIP == TOTAL_HOLDING_SHARES`;
- percentage in `[0,100]`;
- exact duplicate holder rows rejected.

Scientific boundary:

- rows are **ownership-concentration evidence**;
- a holder above 1% is not automatically classified as locked/non-tradable;
- `100% - sum(holders)` is not an authorized effective-free-float estimate;
- mirror bytes are schema/reference evidence, not the preferred canonical acquisition path.

Status: `OFFICIAL_SOURCE_FAMILY_VERIFIED_LOCATOR_AND_ATTACHMENT_AUDIT_NEXT`.

### C. KSEI monthly holding-composition archive — aggregate ownership composition

Official KSEI archive exposes monthly download dates and files with URL form:

`https://web.ksei.co.id/Download/BalanceposEfekYYYYMMDD.zip`

Examples visible in the 2026 archive include 2026-01-30, 2026-02-27, 2026-03-31, 2026-04-30, 2026-05-29, 2026-06-30, and 2026-07-31.

Repo implementation:

- `src/idx_trade/providers/ksei_ownership.py`
- constructs the dated official ZIP URL;
- preserves exact ZIP bytes and SHA-256;
- preserves retrieval timestamps;
- rejects responses without ZIP magic.

Scientific boundary:

- `BalanceposEfek` is an aggregate holding-composition archive;
- it is not assumed to be the named-holder >=1% disclosure;
- it is not assumed to be statutory or effective free float;
- member/schema parsing remains closed until exact official ZIP bytes are inspected locally.

Status: `RAW_CAPTURE_SCAFFOLD_READY_SCHEMA_AUDIT_NEXT`.

## Explicitly prohibited inference in this lane

The following are intentionally **not** produced:

- `true_free_float_pct`
- `effective_free_float_pct`
- `100 - disclosed_holder_pct`
- `locked_holder_pct` inferred solely from a >1% threshold
- `effective_supply_tightness`
- Foreign Flow / volume interaction features

`OwnershipSnapshotMeta.reported_free_float_pct` remains `None` unless a later audit proves an explicit authoritative source field and its semantics.

## Candidate downstream observables — not implemented here

If source coverage is accepted later, a separate feature-contract lane may consider observables such as:

- reported free-float percentage/shares from an explicit official source;
- largest / top-3 / top-5 disclosed holder shares;
- sum/count of disclosed >=1% holders;
- ownership concentration / HHI;
- controller-related ownership where identity is explicit;
- residual/unidentified ownership as a descriptive quantity;
- time variation in concentration.

Any `effective_supply` proxy must remain clearly labelled as a proxy rather than a ground-truth free-float estimate.

## Current implementation files

- `src/idx_trade/providers/idx_ownership.py`
- `src/idx_trade/providers/ksei_ownership.py`
- `tests/test_idx_ownership_provider.py`
- `tests/test_ksei_ownership_provider.py`

Unit/adversarial test scaffolding covers named-holder semantics, Indonesian numeric formats, stale filename vs embedded date, >1% schema aliases, scrip/scripless reconciliation, strict percentages/share counts/controller booleans, raw ZIP preservation, and non-ZIP rejection.

Exact branch test execution and official live bytes remain local-runtime work; no provider call was made from this ChatGPT implementation lane.

## Next bounded milestone

Run a local, bounded source audit only:

1. Query IDX Company Profile Detail for a small adversarial ticker set including a concentrated/low-effective-supply example, a liquid large-cap control, and an illiquid/newer control.
2. Preserve raw bytes, source URL, observation timestamp and SHA-256; report actual `PemegangSaham` schema and whether any explicit free-float field exists elsewhere in the payload.
3. Download a bounded set of official KSEI `BalanceposEfek` ZIPs (first available 2026 disclosure-era snapshot, one middle snapshot, latest available), inspect member names/encoding/schema and archive consistency.
4. Locate at least one official IDX monthly >=1% ownership publication attachment; compare its bytes/schema with the public research mirror without treating mirror identity as authoritative.
5. Determine historical depth and whether source dates/publication dates can support a point-in-time ownership panel.
6. Do not bulk-acquire, infer effective float, design supply scores, touch outcomes, or integrate with Foreign Flow V2 in this milestone.

## Verdict

`SOURCE_PREPARED_BOUNDED_LIVE_AUDIT_NEXT`
