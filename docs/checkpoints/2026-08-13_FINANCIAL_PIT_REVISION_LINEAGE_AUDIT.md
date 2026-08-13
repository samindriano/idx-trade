# Financial PIT Correction / Restatement Lineage Audit

**Date:** 2026-08-13  
**Branch:** `data/financial-pit-revision-lineage-v1`  
**Status:** `BOUNDED_VERSION_LINEAGE_GO_POLICY_FAIL_CLOSED_OUTSIDE_SAMPLE`

## Scope

This is a bounded lineage audit of the three correction markers identified in
the accepted Financial PIT fact-schema feasibility work:

| Ticker | Fiscal period | Known marker |
|---|---|---|
| RONY | FY 2024 | `KOREKSI` |
| BAPA | FY 2025 | `REVISI` / IDX title `(KOREKSI)` |
| MUTU | H1 2025 (`tw2`) | `KOREKSI` |

No market-wide fact extraction, unit/scale repair, ratio/feature derivation,
model work, or protected-outcome access was performed.

## Retrieval contract

The accepted direct transport was used with `curl_cffi` Chrome impersonation:

1. `https://www.idx.co.id/primary/ListedCompany/GetFinancialReport`
2. `https://www.idx.co.id/primary/ListedCompany/GetAnnouncement`
3. exact target filename join to the official announcement attachment URL;
4. direct official attachment download and SHA-256 verification.

The six metadata requests returned HTTP 200: one report and one bounded
announcement-history request per issuer-period. Three additional HTTP 200
downloads retrieved the current `GetFinancialReport` target XLSX for a
byte-level comparison. No pagination was needed beyond the requested
`indexFrom=0,pageSize=1000` bounded responses; the returned payloads were
preserved verbatim.

Announcement timestamps are returned as IDX-local naive values and are
interpreted as Asia/Jakarta before UTC conversion. `File_Modified` is not used
as a substitute for an announcement timestamp.

## Result

All three cases expose two independently retrievable versions with distinct
announcement timestamps and distinct bytes for the target XLSX, `inlineXBRL`
and `instance` attachments. The older target XLSX URL still returned the
older bytes when fetched during this audit; it was not retrospectively
replaced by the latest version.

| Case | Observable versions | Original → latest publication (Asia/Jakarta) | Current report target | Target XLSX current SHA | Classification |
|---|---:|---|---|---|---|
| RONY FY2024 | 2 | 2025-03-27 22:20:39 → 2025-04-09 17:32:13 | corrected | `be5330ec91d307f7168c8acabe743dad13a26b440b81c189f903d9db4c1b5c1c` | `VERSION_CHAIN_PIT_SAFE` |
| BAPA FY2025 | 2 | 2026-04-09 23:03:51 → 2026-05-12 13:44:40 | revised/corrected | `0713d8d5522c62501cd1e43f640495f980201e3d95c6ae88deb5d97299cc15aa` | `VERSION_CHAIN_PIT_SAFE` |
| MUTU H1 2025 | 2 | 2025-07-25 20:19:27 → 2025-08-07 19:27:33 | corrected | `6cb2c62585a2cd49944189a534ebd9eb3509658c2b0a7acba8808c0cec741142` | `VERSION_CHAIN_PIT_SAFE` |

The exact announcement references were:

- RONY original: `007/AESLER/OJK-IDX/III/2025`; correction:
  `007/AESLER/OJK-IDX/III/2025 (KOREKSI)`.
- BAPA original: literal IDX response value `tes`; correction:
  `02/CORSEC/BAPA/V/2026REVISI`.
- MUTU original: `5756.77/EXT-MUTU/VII/2025`; correction:
  `KOREKSI5756.77/EXT-MUTU/VII/2025`.

The BAPA `tes` reference is retained as an explicit metadata anomaly. It does
not erase the evidence because the official response supplies an exact
publication timestamp, deterministic attachment path and independently
retrievable bytes, but downstream provenance must preserve the literal value
and must not normalize it into an invented announcement number.

## File_Modified comparison

For each case, the current `GetFinancialReport` row points to the latest
corrected/revised target and its `File_Modified` agrees with the latest
`TglPengumuman` to the second:

| Case | Current `File_Modified` | Latest `TglPengumuman` | Comparison |
|---|---|---|---|
| RONY | `2025-04-09T17:32:13.227` | `2025-04-09T17:32:13` | same local time to second; `.227` is extra precision |
| BAPA | `2026-05-12T13:44:40.913` | `2026-05-12T13:44:40` | same local time to second; `.913` is extra precision |
| MUTU | `2025-08-07T19:27:33.197` | `2025-08-07T19:27:33` | same local time to second; `.197` is extra precision |

This does **not** prove `File_Modified` is a historical version-publication
field. `GetFinancialReport` exposes the current selected row; its current
`File_Modified` must not be retrospectively assigned to the older version.

## Policy decision

The following policy is defensible for the bounded evidence:

> Use an observed filing version only from its own proven publication timestamp
> onward. If an earlier version is unavailable, treat the issuer fact as
> missing before the observed version rather than backfilling.

Decision: `DEFENSIBLE_BOUNDED_POLICY`.

The policy is intentionally fail-closed outside this sample. A future filing
may be classified as `OBSERVED_LATEST_VERSION_ONLY_FAIL_CLOSED` if only the
current version is available, `RETROSPECTIVE_BYTE_REPLACEMENT_RISK` if an old
URL now serves replacement bytes, or `UNRESOLVED` if announcement linkage,
timestamp, version identity, or bytes cannot be proven.

## External evidence

Raw JSON, official attachment bytes and manifests remain outside Git at:

`D:\Documents\Project\idx-trade-financial-pit-revision-lineage-20260813-v1`

| Artifact | SHA-256 |
|---|---|
| `revision_lineage_audit.json` | `c016b32168383db6c3b82a9b8b0f62ed2cd849a3aae98307238f47a8d2e4f623` |
| `MANIFEST.json` | `70f8ee6f6efc1a2b4de73745021f8eff655e70461fe3032f98287a3ee037de82` |
| `request_manifest.json` | `f3a419f8edcc11f49bc44d17232349103565567f5b6ef6b8bc2dded287d6d900` |
| `lineage_candidates.json` | `2fb00496d8d38e94ab3ed6bb5b37666b7791e010fdae844e3ba41457ba0f796e` |

The external manifest contains 34 immutable files, including the six raw
responses, bounded announcement attachment captures, current-report pointer
captures and audit metadata.

## Boundaries and next decision

This result does not authorize market-wide correction-history reconstruction or
fact extraction. ChatGPT review should decide whether to authorize a larger
lineage coverage gate. Until then, a filing without independently proven
version history remains missing before its first observed version.
