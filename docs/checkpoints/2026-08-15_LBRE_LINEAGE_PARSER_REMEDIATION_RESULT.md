# LBRE Lineage / Parser Remediation V1 — Result

Date: 2026-08-15  
Branch: `data/idx-lbre-lineage-parser-remediation-v1`  
Scientific parent: `data/idx-historical-statutory-free-float-snapshot-v1@4762f4751cb4cc30d348704c7e19e65c47b7a329`  
Parent manifest SHA-256: `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`  
Frozen position: `2026-06-30`

## Decision

`LBRE_REMEDIATION_ACCEPTED_WITH_RESIDUAL_AMBIGUITY`

The bounded remediation is accepted as an evidence-preserving repair, but the
remaining source ambiguity is too large to authorize monthly-history expansion
without a separate review. No synthetic originals, arithmetic free-float
reconstruction, forward-fill, or ambiguous-original selection was used.

## Scope and evidence controls

- Reused only the immutable 2026-06-30 parent corpus.
- Parent manifest was verified before corpus inspection and replay.
- No provider/network calls were made.
- The parent artifact root was not modified.
- No models, outcomes, O2, Foreign Flow, Financial PIT, Corporate Actions, or
  other data lanes were touched.
- Retrieval timestamps were not promoted to publication/knowledge timestamps.

External remediation root:

`D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1-final6`

Remediation artifact manifest SHA-256:

`cb2e929a8e7d5fc481c0eed6add4a6ba848c5a3374c65ea38e5fbe3fa5727244`

## Frozen inventory

The parent problem set was accounted for before replay:

| Problem class | Rows | Unique evidence keys |
|---|---:|---:|
| Parser-unresolved | 18 | 18 |
| Lineage-excluded | 93 | 89 |
| Total | 111 | 107 |

The unique-key count is lower than the row count because the frozen corpus has
duplicate transport records for the same official attachment identity. No
inventory row was silently dropped.

## Parser forensic result

Before: `1,050` exact rows, `18` unresolved.  
After: `1,051` exact rows, `17` unresolved.  
Recovered: `1` exact row (`BTPS`).

The BTPS report contains an authoritative labelled two-column summary with
explicit current free-float shares, total listed shares, and percentage. The
narrative “became” line was treated only as corroboration; it did not override
the primary summary. The parser change is template-specific and fail-closed.

Residual parser taxonomy:

- `13` `GENUINE_SOURCE_AMBIGUITY_CURRENT_PERCENTAGE_MISSING`: the visible
  percentage is only a prior-column value; no current percentage was invented.
- `1` `GENUINE_SOURCE_AMBIGUITY_SHARE_NUMBER_FORMAT`: IRRA has a malformed /
  non-integer current share token.
- `1` `GENUINE_SOURCE_AMBIGUITY_INVALID_LISTED_SHARES`: TECH has invalid zero
  current listed shares.
- `1` `GENUINE_SOURCE_AMBIGUITY_INVALID_FREE_FLOAT_CONTRACT`: MPOW free-float
  shares exceed listed shares.
- `1` `UNSUPPORTED_IDENTITY_AND_FIELDS_MISSING`: CHEK lacks the required
  identity and exact fields.

## Lineage forensic and replay result

Before: `957` admitted rows, `93` excluded rows, `871` current observations.  
After: `963` admitted rows, `87` excluded rows, `877` current observations.  
Recovered lineage rows: `6`.

Admitted lineage revision counts changed from `877 ORIGINAL / 80 CORRECTION` to
`882 ORIGINAL / 81 CORRECTION`. The full replay contains `964` observations,
including the one newly parsed BTPS original (`883 ORIGINAL / 81 CORRECTION`).

Deterministic lineage recoveries:

- `HILL`, `WINS`, `SKBM`: `3` byte-identical duplicate transport references
  collapsed to one canonical official observation per ticker.
- `PGUN`: `1` same-announcement, same-economic-content re-upload retained as a
  single canonical observation; the differing attachment bytes were not used
  to manufacture a second state.
- `BAPA`: explicit `KOREKSI` announcement marker repaired the metadata
  classification and linked the correction to the unique earlier original.

Residual lineage taxonomy:

- `35` `SOURCE_EVIDENCE_MISSING_NO_ORIGINAL`;
- `29` `UNSUPPORTED_INVALID_ORIGINAL_REQUIRED_FOR_CHAIN`;
- `19` `GENUINE_SOURCE_AMBIGUITY_MULTIPLE_ORIGINALS`;
- `3` duplicate transport references collapsed;
- `1` same-announcement re-upload collapsed;
- `4` deterministic exact canonical duplicate/recovery rows;
- `1` explicit correction-marker recovery;
- `1` explicit original retained for that correction.

The `29` multiple-original cases not listed as deterministic are retained
fail-closed. No latest-by-time, filename ordering, numeric closeness, or
unproven supersession rule was applied. The `35` no-original cases remain
missing rather than being backfilled from a correction.

## Integrity checks

- Parent manifest verification: PASS.
- Exact problem inventory accounting: PASS (`111` rows accounted).
- Recovered observations satisfy the existing
  `HistoricalFreeFloatObservation` contract: PASS.
- Replay chronology / correction validation: PASS.
- Previously admitted semantic changes: `0`.
- PIT publication-time violations: `0`.
- Non-official evidence promoted: `0`.
- Synthetic original/correction records: `0`.
- Parent artifact mutation: `0`.

## Validation

- Focused remediation + historical statutory FF tests: `19 passed`.
- Full repository pytest: `1 failed, 67 passed`.
- The sole failure is the pre-existing unrelated
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expectation (`1` conflict expected, `2` observed because both
  `raw_close` and `vendor_adj_close` are independently audited). The known
  storage expectation was not changed in this lane.
- `git diff --check`: PASS.

The exact per-case taxonomy, recovered rows, post-replay table, parent
verification, and hashes are in the external manifest above. No monthly
history acquisition is authorized by this result.

