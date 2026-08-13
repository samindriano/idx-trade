# Corporate Action PIT Availability Provenance V1 — Bounded Result

Date: 2026-08-14 (Asia/Jakarta)
Branch: `data/corporate-action-pit-availability-provenance-v1`
Base: `5222af3b68bf86765c43017912e990edf02148ad`
Status: `REVIEW`

## Scope and safety

This lane implements the availability-provenance semantic remediation and a
bounded public KSEI evidence audit. It does not create a canonical corporate-
action table, map events to trading sessions, adjust OHLC, reconstruct shares,
derive features, access outcomes, or touch Foreign Flow, Financial PIT, AKSes,
O2, or forward runtime.

The two input roots were read-only and their manifests were verified:

| Root | Expected manifest SHA-256 | Observed | Result |
|---|---|---|---|
| `D:\Documents\Project\idx-corporate-action-pit-source-audit-20260814-v1-final2` | `d44b9362909f5c05d8412ff07ca4c5616a74b43930bd1caf92242ed25b5e10cf` | same | PASS |
| `D:\Documents\Project\idx-corporate-action-pit-linkage-20260814-v1-final` | `1db444f6ceb815bdc29f1f80c8158c7a2050ebf7a5fe0ec0c4230e65940bb195` | same | PASS |

New immutable audit root:

`D:\Documents\Project\idx-corporate-action-pit-availability-20260814-v1-final`

Manifest SHA-256: `c8f8639b2d076fd91cb684925c6a0c6c13d2e3ed87a2e7a2fc0da8cad69a39f7`
(81 manifest-listed files).

## Semantic remediation

`resolve_availability_provenance()` now preserves, as separate evidence:

- KSEI PDF internal/document date;
- KSEI publication-table date;
- asset URL/filename and strict terminal `YYYYMMDDHHMM` candidate;
- HTTP `Date`, `Last-Modified`, `ETag` where available;
- observed retrieval timestamp;
- exact linked IDX publication timestamp.

Only an exact deterministic IDX linkage produces `precision=
IDX_TIMESTAMP_CONFIRMED` and a knowledge timestamp. PDF/table dates and asset
filename candidates produce no `knowledge_date` and carry
`availability_status=SOURCE_DATE_ONLY_NOT_AVAILABILITY_VERIFIED`. Their
precision remains the frozen vocabulary (`DATE_ONLY` or `UNKNOWN`). A
non-exact IDX linkage preserves the IDX timestamp as evidence but does not
promote it to knowledge time.

The parser no longer treats a schedule/recording date as the PDF's internal
date, does not derive an asset filename from a non-asset source URL, validates
metadata dates/timestamps, and fails closed on asset URL/filename disagreement.

## Bounded audit

The audit contains 34 official KSEI PDF URLs/records and 34 valid PDF byte
captures. Five documents were reused from the accepted immutable linkage root;
28 direct KSEI fetch attempts were made, including two transient retries. All
28 eventually returned HTTP 200 PDF bytes. No credentials were used.

The six mandatory cases are present: YOII KSEI-16506/JKU/0626, SINI
KSEI-17438/JKU/0726, MEGA KSEI-7347/JKU/0426, MEGA KSEI-7806/JKU/0426, MLPT
KSEI-18691/JKU/0726, and RAJA KSEI-18423/JKU/0726.

| Dimension | Result |
|---|---:|
| Rights / HMETD | 10 |
| Stock split | 3 |
| Bonus shares | 4 |
| Stock dividend | 1 |
| Cash dividend | 3 |
| Other / unresolved economic family | 13 |
| 2024 records | 1 |
| 2026 records | 32 |
| 2009 retention probe | 1, excluded from target-family coverage |
| Terminal filename timestamp candidate | 16 |
| Generic filename / no terminal candidate | 18 |
| Parsed identity/date rows | 7 |
| Fail-closed unresolved parser rows | 27 |

The public schedule/search surface did not establish a target-family sample
covering three calendar years. The 2009 file proves that an old generic asset
can still be directly retrievable, but it is a retention probe rather than a
complete historical schedule archive. No 2025 target-family coverage claim is
made.

## Timestamp findings

- PDF internal date and publication-table date were both available for 28
  records; they matched exactly in 28/28.
- Filename candidates were same calendar date as the source date in 14/16,
  later in 2/16, and earlier in 0/16.
- YOII is the decisive counterexample: table/PDF date `2026-06-26`, asset
  suffix `202607011721`, a five-day delay. The accepted evidence note records
  this same mismatch.
- One additional candidate was one day after the PDF/table date.
- HTTP `Last-Modified` was present for 29 records; the 14 comparable
  timestamped candidates were within 60 seconds of the converted local
  `Last-Modified` time (not exact because server seconds differ).
- `Last-Modified` therefore supports an upload/storage-time interpretation of
  the filename suffix in this sample, but neither field proves first public
  availability or an official publication-time contract.
- Exact deterministic KSEI-to-IDX publication timestamp linkages in this audit:
  `0`. The existing MLPT IDX correction timestamp remains separate
  event-specific evidence and is not relabeled as KSEI publication time.
- Existing MEGA base/follow-up documents remain independently hashed and
  append-only; the follow-up explicitly cites the base.

## Decision

`KSEI_ASSET_TIMESTAMP_CANDIDATE_ONLY`

KSEI schedule documents and asset metadata are useful for discovery and
bounded event evidence. They are not yet a canonical PIT knowledge-time source.
Generic filenames remain unresolved for availability. No date-only or asset
candidate was mapped to a market session or admitted as a historical
publication timestamp.

## Validation

- Focused corporate-action linkage/parser tests: `28 passed`.
- `git diff --check`: PASS.
- Full repository pytest: `72 passed, 1 failed` (73 collected). The single
  failure is the pre-existing unrelated
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`;
  current storage semantics report two independent conflicts (`raw_close` and
  `vendor_adj_close`) while that old assertion expects one. This lane did not
  modify `storage.py`.

No trading-session mapping, OHLC adjustment, bulk canonical acquisition,
model work, or protected-outcome access occurred.
