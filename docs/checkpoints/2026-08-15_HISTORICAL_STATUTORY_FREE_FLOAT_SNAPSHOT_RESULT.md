# Historical Statutory Free Float Snapshot V1 — Result

Date: 2026-08-15
Branch: `data/idx-historical-statutory-free-float-snapshot-v1`
Prepared parent: `6d5b7f28b4f2e0adf10fc47e63412b67896f5e27`
Scope: bounded official reported free-float snapshot acquisition and reconciliation only.

## Decision

Final verdict: `HISTORICAL_STATUTORY_FF_SNAPSHOT_READY_WITH_GAPS`.

The official reported snapshot contract is usable for exact observations with
publication time, correction lineage, and source hashes. The work does not
establish a complete quarterly market-wide history for 2024–2026, so no daily
panel, interpolation, forward-fill, holder reconstruction, HSC subtraction, or
effective-supply estimate is authorized by this result.

## External artifacts and provenance

External artifact root:
`D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`

Final external manifest SHA-256:
`7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`

The two reused parent reports were verified against the parent manifest:

- Parent manifest SHA-256:
  `ff25cefed69af8cd221530a23f6fc31e85e0c510a21ef5bfb78526d618a45454`
- `Peng-S-00006/BEI.PLP/02-2026`, position 2025-12-31 attachment SHA-256:
  `9b22e109be5b80643aa506c071fe45bd27a8f5e327edf32d64796ba6e136def4`
- `Peng-S-00011/BEI.PLP/04-2026`, position 2026-03-31 attachment SHA-256:
  `d22ca9aaeb662df0463f6398657a26f28fc22e2be497824a7cc11d76be6f1911`

Raw direct- IDX probe responses are retained outside Git under
`probes/`. The bounded `ListedCompany/GetAnnouncement` queries used the
official IDX endpoint with exact year/date parameters and keyword `Free Float`.
The warm direct transport returned 3 records for 2024, 6 for 2025, and 3 for
2026. These results did not expose a row-complete quarterly market-wide anchor
for every requested period.

## Quarterly market-wide anchor audit

Only exact official reported values were admitted. A report with a percentage
but no explicit free-float share count is not an exact observation under this
contract.

| Period | Result |
|---|---|
| 2024 quarterly anchors | Not proven complete; bounded announcement search returned no row-complete quarterly anchor. |
| 2025-03-31, 2025-06-30, 2025-09-30 | Not proven complete. |
| 2025-12-31 | Exact market-wide report reused; 956 reported issuer rows, 923 exact rows admitted. 33 rows had explicit 0% with no explicit share count and remained excluded. |
| 2026-03-31 | Market-wide report reused, but it exposed percentage without an explicit free-float share column/value; 0 exact share observations admitted from this report. |
| 2026-06-30 | No complete market-wide quarterly anchor proven by the bounded official search. |

The market-wide normalized artifact therefore contains 923 exact observations
for position 2025-12-31. Missing or incomplete fields remain missing and were
not repaired.

## Bounded issuer LBRE census

The census used existing official IDX issuer announcement captures and one
bounded position target, 2026-06-30. No full monthly acquisition was started.

- LBRE issuer announcements discovered: 1,068
- Unique main attachment URLs: 1,064
- Successful official PDF downloads: 1,064 / 1,064
- Exact parsed rows: 1,050
- Parser-unresolved rows: 18
- Exact 2026-06-30 input rows: 1,015
- Exact 2026-06-30 original/correction rows: 915 / 100
- Unique ticker-period keys before lineage: 907
- Current 2026-06-30 observations after conservative lineage replay: 871
- All exact rows by source-year/date were retained externally; no invalid row
  was converted into a valid observation.

Conservative lineage required one valid original plus a complete ordered
correction chain. Across the bounded exact input, 957 rows were admitted to the
lineage replay (877 originals and 80 corrections); 93 rows were excluded:

- `UNRESOLVED_NO_ORIGINAL`: 35
- `UNRESOLVED_MULTIPLE_ORIGINAL`: 29
- `UNRESOLVED_INVALID_CONTRACT_CHAIN`: 29

Publication timestamps were preserved as official IDX announcement timestamps,
interpreting IDX naive timestamps as Asia/Jakarta before UTC normalization.
Later retrieval time was not used as a historical publication time.

## Materialized observations and reconciliation

The unified external CSV is:
`normalized/historical_ff_observations.csv`.

It contains 1,882 admitted observations:

- 923 exact market-wide observations at 2025-12-31;
- 957 admitted LBRE observations from the bounded census and parent samples;
- corrections remain separate records with `supersedes_record_id` and are
  replayed without overwriting the historical version.

Cross-source reconciliation on the same ticker and position date:

| Status | Count |
|---|---:|
| `AGREE` | 1 |
| `CONFLICT` | 1 |
| `SINGLE_SOURCE` | 1,798 |

Examples:

- `BREN`, 2025-12-31: `AGREE`, exact shares and percentage.
- `BBCA`, 2025-12-31: `CONFLICT`; shares matched, but percentages were 42.70
  versus 42.74 percentage points. The conflict is retained; no source was
  silently preferred.

The parent DCII sample was explicitly for position 2024-12-31 and was not
incorrectly compared to the 2025-12-31 market-wide anchor.

## Fail-closed limits

The result does not claim:

- complete quarterly market-wide coverage for 2024–2026;
- an exact 2026-03-31 share observation from the percentage-only report;
- a complete 2026-06-30 market-wide anchor;
- a complete monthly LBRE history;
- statutory free float reconstructed from holders, HSC, investor categories, or
  `100% - holder total`;
- a daily free-float series or effective-supply series.

No Foreign Flow, feature, model, protected outcome, or forward-runtime artifact
was touched.

## Validation

- Focused tests: `14 passed`.
- Full repository test: `61 passed, 1 failed`.
- Warnings: none reported by the full run.
- Failure is unrelated to this lane:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
  The test expects one conflict, while the current storage implementation
  surfaces two independent conflicts (`raw_close` and `vendor_adj_close`). The
  storage semantics were not changed in this lane.
- `git diff --check`: passed.

The factual checkpoint and external manifest are the authoritative result for
this bounded snapshot run. A future task may separately authorize recovery of
missing quarterly anchors or a wider monthly census; it must not silently turn
the current gaps into interpolated values.
