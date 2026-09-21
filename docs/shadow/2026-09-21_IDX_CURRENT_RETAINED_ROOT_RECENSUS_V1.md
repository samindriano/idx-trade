# IDX-Trade Current Retained-Root Re-Census V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **METADATA-ONLY FRESHNESS CHECK / NO NEW ARTIFACT CLASS**

## Scope

This check re-enumerated the three already approved local evidence roots in
read-only metadata mode. It counted files and bytes and recorded the newest
filesystem timestamp/path. It did not open provider/backfill or research/model
cluster contents, read protected outcomes, call a provider, modify a source,
copy a new input, or touch the active runtime/scheduler/cloud state.

This is not a replacement for the prior source/copy hash attestations. Because
this pass is metadata-only, it does not prove that every previously copied
source byte is still unchanged.

## Current census

| Root | Files | Bytes | Newest observed timestamp (UTC) | Newest relative path |
|---|---:|---:|---|---|
| `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1` | 135 | 79,770 | `2026-09-21T02:22:04.2991527Z` | `operational\latest.json` |
| `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring` | 819 | 63,136,721 | `2026-09-20T13:30:04.5877414Z` | `eod_automation\v4_x1_pipeline\latest.json` |
| `D:\Documents\Project\idx-trade-data-gate-20260808v` | 32,656 | 7,431,176,611 | `2026-09-20T13:30:04.5877414Z` | `forward_monitoring\eod_automation\v4_x1_pipeline\latest.json` |

## Delta against the admitted inventory

- Active runtime remains `135` files / `79,770` bytes, matching the prior
  bounded runtime census.
- Forward-monitoring remains `819` files / `63,136,721` bytes, matching the
  prior retained-root census.
- The approved parent-root path count remains `32,656`, matching the prior
  metadata-only boundary census.
- No new filename class or additional paper-state class was admitted by this
  check. Existing provider/backfill and research/model clusters remain outside
  the shadow input scope.

## Interpretation

The count-level frontier is unchanged. The real-state blocker is therefore not
closed by this re-census: no paper-state snapshots, prepared execution chain,
holdings/obligation ledger, or recovery ancestor was admitted. Existing
cryptographic attestations remain the evidence for the earlier immutable
copies; this record deliberately makes no stronger current-byte claim.

The qualification decision remains:

`REAL ARTIFACT DISCOVERY = PASS WITH LIMITATION`

`PRE-CANARY READINESS = NO-GO`

