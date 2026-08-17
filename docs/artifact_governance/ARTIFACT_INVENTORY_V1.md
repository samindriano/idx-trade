# IDX-Trade Artifact Governance V1 — inventory and disposition

Status: bounded audit complete; accepted small-artifact promotion completed for
the certified 126-session data-gate snapshot.

Repository snapshot: `origin/main` at `2edee4baf1d1ef76b39ed3dde116ffd9231861b8`.
The scan was performed on 2026-08-17 from the IDX-Trade repository and a
targeted set of IDX-related external roots. It did not move, delete, rewrite,
open, or recapture source artifacts. It did not inspect model/outcome payloads.

## Decision

The safe boundary is:

- `PUSH_TO_GIT`: source/tests, contracts, schemas, sanitized fixtures, small
  canonical security/listing/session/fold identity tables, and accepted
  diagnostic summaries that are small and path-scrubbed.
- `PUSH_SUMMARY_OR_MANIFEST_ONLY`: external artifact identity, manifest,
  SHA-256, byte size, coverage/diagnostic summary, and frozen row/session
  identities. The payload remains external and is not copied automatically.
- `KEEP_EXTERNAL`: raw provider responses/attachments, full OHLCV or other
  panels, large CSV/JSONL/parquet archives, runtime databases/logs, joblib/pkl
  model binaries, credentials, and protected outcomes.

The actionable registry is
`artifacts/registry/ARTIFACT_REGISTRY_V1.json`; its validation shape is next to
it. The new `artifacts/` layout is a pointer/metadata convention, not a second
runtime or data store.

## Concrete snapshot

`origin/main` currently tracks 48 files. No tracked file has a data/model
binary extension; the largest tracked file is 89,290 bytes. The primary
worktree had an unrelated untracked `apps/` frontend directory on a different
branch; it was intentionally excluded and left untouched.

The targeted external scan found 122 IDX-related roots, 107,691 files, and
approximately 17.73 GB. These are grouped below; sizes are approximate and are
used for disposition, not as payload hashes.

| Family | Roots | Files | Approx. MB | Recommendation |
|---|---:|---:|---:|---|
| Data gate + forward/runtime | 23 | 27,358 | 4,934.5 | `KEEP_EXTERNAL` |
| Financial PIT | 50 | 13,159 | 10,413.1 | `KEEP_EXTERNAL` |
| Ownership/free-float/LBRE | 15 | 61,214 | 1,744.8 | `KEEP_EXTERNAL` |
| Foreign flow | 6 | 3,975 | 951.3 | `KEEP_EXTERNAL` |
| Corporate actions | 20 | 830 | 37.2 | `KEEP_EXTERNAL` |
| Market/index/sector/universe | 4 | 394 | 27.5 | `PUSH_SUMMARY_OR_MANIFEST_ONLY` |
| Open/provider archives | 1 | 9 | 14.6 | `KEEP_EXTERNAL` |
| Other targeted IDX audit roots | 2 | 128 | 6.7 | `PUSH_SUMMARY_OR_MANIFEST_ONLY` |
| **Total** | **122** | **107,691** | **18,155.2** | — |

Representative large roots include the 4.54 GB `idx-trade-data-gate-20260808v`
runtime, the 5.55 GB Financial PIT adapter census, 1.54 GB LBRE monthly
history, 749 MB Foreign Flow history, and repeated 387–793 MB Financial PIT
feature-provenance outputs. None should be placed in Git.

The external scan also found approximately 1,606 manifest-named files, 1,790
summary-named files, and 17 SHA-256 sidecars. These counts are evidence that
the project already has enough provenance metadata to curate Git-side pointers;
they are not a reason to copy every run directory. The Foreign Flow historical
root alone contains 1,288 `stock_summary.raw.json` session payloads (about 717
MiB), which remain external.

## Actual promotion — 2026-08-17

The promotion used only the accepted 126-session checkpoint from
`ed13ee0812e8db21d580e922f4e346873aa7b3cd`:
`docs/checkpoints/2026-08-08_FULL_MARKET_126_SESSION_CERTIFIED.md`.
The selected external snapshot was represented by the logical root key
`IDX_TRADE_EXTERNAL_ROOT` and relative snapshot
`idx-trade-data-gate-20260808u`. The older
`idx-trade-data-gate-20260808p` snapshot was checked for duplicate hashes;
exact duplicates were not copied a second time.

Promoted Git paths (13 artifacts, 123,650 bytes) are recorded with source and
promoted SHA-256 values in
`docs/artifact_governance/ARTIFACT_PROMOTION_V1.csv` and in the registry's
`promoted_artifacts` array:

- six `PUSH_TO_GIT` canonical/reference tables under
  `artifacts/canonical/idx_data_gate_126/`;
- six `PUSH_SUMMARY_OR_MANIFEST_ONLY` summaries under the same directory;
- one scrubbed certified-manifest pointer under `artifacts/manifests/`.

The certified manifest itself remains external because it contains
user-specific absolute paths. The Git pointer preserves its source SHA,
certification checkpoint, window, gate result, and the external model-safe
panel SHA without copying that panel. `tradability_anchors.csv` and
`model_safe_price_panel_126_sessions.parquet` also remain external because
they are large runtime/data payloads.

All promoted exact-copy files have source SHA equal to the Git SHA. No raw
provider payload, attachment, full OHLCV/Financial PIT/Foreign Flow panel,
model binary, runtime state, credential, or outcome was promoted.

## What belongs in Git

The existing tracked `config/`, `src/`, `tests/`, `docs/`, and
`coordination/` contracts remain the canonical home for reproducible logic and
small identity/reference tables. When a lane produces a new accepted small
artifact, put it under `artifacts/manifests/`, `artifacts/schemas/`, or
`artifacts/fixtures/`, and register it with a logical identifier and SHA.

For external run families, the Git-side record may include a scrubbed
`MANIFEST.json`, `*.sha256`, coverage summary, or frozen identity table only
when it is small, accepted, and free of absolute user paths, credentials, raw
payloads, and protected outcomes. The registry lists examples but does not
copy any existing external file during this task.

## What stays external

Keep all raw IDX/Zapi/Yahoo/TradingView/Investing/KSEI/provider bytes, full
daily/intraday OHLCV, Stock Summary session archives, Financial PIT filing
attachments and provenance JSONL, Foreign Flow raw sessions, LBRE/PDF history,
runtime/capture databases, generated model/score binaries, and outcomes under
the configured external root. Existing files are not renamed or relocated.

The `.gitignore` additions protect the future `artifacts/external`, `raw`,
`cache`, `runtime`, `models`, and `outcomes` drop zones plus large payload
extensions. They do not ignore the Git-owned registry, manifest, schema, or
fixture directories.

## Reconciliation and limitations

This is a layout/governance audit, not a claim that every external root is
scientifically accepted. A summary or manifest is eligible for promotion only
after its own lane's provenance/review contract accepts it. Historical source
bytes remain external even when a summary is pushed. The scan used filename
families and file metadata; it did not validate the scientific content of every
external artifact.

The complete row-level inventory and policy categories are in
`ARTIFACT_INVENTORY_V1.csv`. No model, outcome, provider, scheduler, or source
artifact was changed.
