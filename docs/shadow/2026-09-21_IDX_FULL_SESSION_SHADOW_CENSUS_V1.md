# IDX-Trade Full Session Shadow Census V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **FULL SESSION DISCOVERY COPY ATTESTED / HISTORICAL REPLAY BLOCKED**

## Scope

This record extends the earlier two-session copy-only census to the complete
retained `forward_monitoring/sessions` package found in the approved local
root. The source was read-only. The copy is a discovery/shadow input package;
it is not an E2E paper-state migration root and no replay/controller/production
entrypoint was invoked against it.

The following were not read or admitted:

- provider checkout or provider calls;
- protected outcomes, PnL, H5/H10/OOS, and live counters;
- `monitor.sqlite3` and `o2_forward_counter.json`;
- active writable runtime or scheduler state.

## Discovery-root inventory

The approved `forward_monitoring` root contains 819 files and 63,136,721
bytes. The complete top-level breakdown is:

| Class | Files | Bytes | Treatment |
|---|---:|---:|---|
| attempts | 135 | 26,674,484 | retained capture attempts; not paper state |
| calendar | 3 | 3,017 | current calendar artifacts |
| context_bridge | 33 | 4,646,665 | bridge/context evidence; not paper state |
| eod_automation | 262 | 728,858 | run metadata; not paper state |
| model_calendar | 3 | 3,077 | model calendar artifacts |
| model_runs | 132 | 2,521,208 | score/model outputs; not paper state |
| prospective | 9 | 454,042 | prospective feature/context state, not portfolio state |
| provenance_attestations | 2 | 5,010 | calendar provenance attestations |
| reliability_v1_shadow | 2 | 23,521 | reliability shadow artifacts |
| sessions | 232 | 27,899,196 | 29 retained session packages |
| shadow_runs | 3 | 29,530 | shadow score evidence |
| v4_x1_clean_inputs | 1 | 16,832 | security-master input |
| excluded monitor.sqlite3 | 1 | 131,072 | protected/operational counter surface; not read |
| excluded o2_forward_counter.json | 1 | 209 | live counter surface; not read |

The non-excluded local inventory is therefore 817 files / 63,005,440 bytes.

## Full immutable discovery copy

Copied to:

`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-all-sessions`

| Component | Files | Bytes |
|---|---:|---:|
| session packages | 232 | 27,899,196 |
| current calendar files | 3 | 3,017 |
| calendar provenance attestations | 2 | 5,010 |
| total | 237 | 27,907,223 |

Per-file source pre-hash, source post-hash, and copy hash were calculated for
the 237 copied files. Results:

- source changes during copy: `0`;
- source/copy hash mismatches: `0`;
- sorted copy-attestation manifest digest:
  `5246c4ca7e25974db313ebc8f754014c2365d92eb88bac41d114fef0f2c12012`.

The earlier V2 manifest remains the admitted 20-file package for score/input
validation. This larger package is now an immutable discovery copy and is not
promoted to replayable state merely because its hashes match.

The per-file source/copy hash table is retained in
`2026-09-21_IDX_FULL_SESSION_COPY_ATTESTATION_V1.md`.

## Session package shape

| File family | Count | Sessions represented |
|---|---:|---:|
| `manifest.json` | 29 | all 29 |
| `model_input.parquet` | 29 | all 29 |
| `session_evidence.parquet` | 29 | all 29 |
| `session_ohlcv.parquet` | 29 | all 29 |
| `idx_stock_summary.csv` | 29 | all 29 |
| `idx_index_summary.csv` | 27 | 27 |
| `idx_stock_summary.raw.json` | 27 | 27 |
| `idx_index_summary.raw.json` | 27 | 27 |
| `idx_foreign_flow.*` | 2 pairs | 2 |
| `open_enrichment_manifest.json` | 2 | 2 |

The missing raw/index families are legacy package-shape differences. They are
not silently filled from another session.

## Manifest lineage and copied-child checks

The checks below were run on the immutable copies. They compare embedded child
hashes with the corresponding copied file; they do not infer missing paper
state.

| Embedded field | Match | Mismatch | Absent | Result |
|---|---:|---:|---:|---|
| `snapshot_sha256` | 29 | 0 | 0 | child hash aligned |
| `evidence_sha256` | 29 | 0 | 0 | child hash aligned |
| `stock_summary_sha256` | 29 | 0 | 0 | child hash aligned |
| `session_ohlcv_sha256` | 27 | 0 | 2 | legacy manifests omit field |
| `index_summary_sha256` | 27 | 0 | 2 | legacy manifests omit field |
| `calendar_sha256` | 1 | 28 | 0 | historical calendar lineage unresolved |

The current copied calendar SHA is
`8a5fd51630c331b651fcd41bd024a70c6f8fad6dcc9fe9d5393429e16766a6fe`.
Only the 2026-09-18 manifest embeds that current hash. The 29 manifests have
23 distinct embedded calendar hashes, so the current calendar cannot be used
as a universal historical substitute.

## All-session input-level validation

The existing read-only `verify_eod_execution_inputs` contract was applied to
the copied model-input/OHLCV files with required tickers derived from each
copied model-input file. No provider, outcome, scheduler, or live runtime was
accessed.

| Result | Sessions | Explanation |
|---|---:|---|
| `PASS_INPUT_LEVEL` | 27 | structural OHLCV/model/calendar check passed |
| `EXECUTION_V1_DECISION_DATE_NOT_OFFICIAL_SESSION` | 1 | 2026-08-03 is not in the copied current calendar |
| `EXECUTION_V1_NEXT_OFFICIAL_SESSION_UNAVAILABLE` | 1 | 2026-09-18 is the last session in the copied current calendar |

This is input-level evidence only. Because the calendar hash is unresolved for
28 sessions and the current calendar is not a complete historical parent for
the boundary cases, the 27 passes do not become historical E2E replay.

## State-population conclusion

The full retained package contains model/data/evidence/score and automation
metadata, but no admitted paper portfolio snapshot, prepared execution parent,
execution/fill vector, pending obligation ledger, CA entitlement/settlement
ledger, or recovery chain. Prospective artifacts with names such as
`*_state_v1` are feature/context contracts and were not reclassified as paper
portfolio state.

`FULL_SESSION_DISCOVERY = PASS WITH LIMITATION`.

`REAL_MIGRATION = BLOCKED` and `HISTORICAL_REPLAY = BLOCKED / INPUT-LEVEL
VALIDATION ONLY`. The next valid progression requires the exact historical
calendar lineage and a separately authorized immutable paper-state/CA/recovery
package; substituting the current calendar or inventing state is prohibited.
