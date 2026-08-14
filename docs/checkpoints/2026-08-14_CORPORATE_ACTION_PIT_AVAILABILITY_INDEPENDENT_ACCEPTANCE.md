# Corporate Action PIT Availability Provenance V1 — Independent Acceptance

Date: 2026-08-14 (Asia/Jakarta)
Reviewed branch: `data/corporate-action-pit-availability-provenance-v1`
Reviewed final HEAD: `50718c3f23352444630160dc54934eaa2201289d`
Substantive audit commit: `314b99a3a91e2297fa0061a52849ee3c64d60222`
Independent verdict: `KSEI_ASSET_TIMESTAMP_CANDIDATE_ONLY_ACCEPTED`

## Independent review conclusion

The bounded availability-provenance audit is decision-valid. The implemented semantics correctly separate event/source dates, asset metadata, observed retrieval time, and exact linked IDX publication timestamps. KSEI PDF dates, KSEI publication-table dates, filename timestamp candidates, HTTP Date/Last-Modified, and ETag are not promoted to historical knowledge time. Only an `EXACT` deterministic IDX linkage can produce `IDX_TIMESTAMP_CONFIRMED`.

The empirical result supports the frozen verdict rather than promotion of KSEI asset metadata:

- 34 official KSEI PDF records audited;
- 16 strict terminal `YYYYMMDDHHMM` filename candidates and 18 generic filenames;
- 14/16 candidate dates equal the source date, 2/16 are later, 0/16 earlier;
- YOII `KSEI-16506/JKU/0626` is a decisive +5-day source-date vs asset-candidate counterexample;
- comparable asset candidates closely track HTTP Last-Modified in the bounded sample, which supports an upload/storage-time interpretation but not a first-public-availability contract;
- exact deterministic KSEI-to-IDX timestamp linkages remain 0;
- generic filename cases remain availability-unresolved;
- the public schedule/search surface did not establish target-family coverage over three historical calendar years.

The final branch HEAD differs from the substantive audit commit only by a one-line handoff pin; there is no post-result scientific/code drift.

## Code review

`resolve_availability_provenance()` now fails closed as required:

- KSEI document/table dates => `knowledge_at_utc = null`, `knowledge_date = null`, `SOURCE_DATE_ONLY_NOT_AVAILABILITY_VERIFIED`;
- asset filename timestamp candidate => evidence only, no timezone/publication claim;
- non-exact IDX timestamp linkage => timestamp preserved as evidence but not promoted;
- exact linked IDX `TglPengumuman` => `IDX_TIMESTAMP_CONFIRMED`.

The KSEI parser also rejects asset URL/filename disagreement, parses only strict terminal timestamp patterns as candidates, preserves generic filenames as unresolved, and does not reinterpret schedule/record dates as PDF document dates.

## Accepted boundary

Historical Corporate Action PIT is **not** authorized for market-wide canonical materialization from KSEI dates or asset timestamps. Do not map KSEI source dates or filename candidates to trading sessions, do not reconstruct canonical shares outstanding, do not adjust OHLC, and do not use these timestamps in model features.

The highest-value next bounded research step is event-specific deterministic **IDX announcement/attachment timestamp linkage**: parse exact economic anchors from official IDX corporate-action attachments (ticker, event family, ratio, rights code/ISIN, record/listing/distribution dates, share-state values, and explicit correction lineage where present), then require exact agreement with the accepted KSEI event identity before admitting `TglPengumuman` as PIT knowledge time. This should be bounded and audited before any bulk acquisition.

No rerun of the KSEI filename-timestamp experiment is authorized absent new official semantics or materially new evidence.
