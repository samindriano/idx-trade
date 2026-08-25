# V4-X1 Prospective Pre-Access Adapter Audit V1

Date: 2026-08-25 (Asia/Jakarta)

Status: `V4_X1_PREACCESS_ADAPTER_OUTCOME_BLIND_ACCUMULATING_TARGET_PRODUCER_DEPENDENCY`

## Scope

This lane adds a thin, read-only adapter over
`src/idx_trade/prospective_preaccess_readiness_v1.py`. The pure readiness core
was not changed. The adapter reads only operational metadata and JSON
manifests, re-hashes declared score-artifact bytes without deserializing rows,
and never opens target/outcome/label artifacts.

No provider call, scheduler/runtime mutation, counter mutation, model work, or
protected-outcome access occurred.

## Actual production shapes audited

The external `forward_monitoring` root contains:

- `model_runs/<session>/<model>/manifest.json` with `model_id`, `generation`,
  `model_fingerprint`, `session_date`, `status`, false outcome/provider guards,
  `output.artifact_path`, `output.artifact_sha256`, `output.columns`, and
  declared row count;
- `eod_automation/v4_x1_pipeline/latest.json` with nested `x1_counter` status
  (`completed`, `target`, `remaining`, `sessions`, and artifact-verification
  status);
- `calendar/exchange_sessions.csv` plus
  `calendar/exchange_session_summary.json` with official IDX source identity,
  session range, completeness, and schedule hashes;
- session manifests and E2E operational metadata, but no persisted
  `PaperState`/Session Audit attestation, benchmark attestation, or prior-access
  audit artifact discoverable under the audited runtime root.

The adapter’s score discovery is exact-model only:

- `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`
- generation `V4-X1-CLEAN`
- fingerprint pinned to the pure core
- manifest guards must be explicitly false
- declared score artifact bytes are re-hashed and must equal the manifest
- score rows are never loaded

At audit time, two exact clean score manifests were present (sessions
2026-08-21 and 2026-08-24). The runtime counter reports `2/100`, but this is a
runtime status, not a canonical inventory-bound attestation; the adapter maps
it to `ACCUMULATING` and records `inventory_sha256_binding=false`.

## Target producer finding

The frozen contract/provenance documentation references
`src/idx_trade/ranking_v4_3_target_execution.py` as the retained target
materializer. A remote-ref audit found that source on retained non-active
lineage branches (including the historical clean-replay/refit and CA bridge
branches), but the producer path is not present in the active pre-access branch
tree and no persisted `target_attestation`/`target_manifest` artifact was
discovered under the external runtime root. Therefore the source implementation
exists elsewhere, but the active lane does not yet have a sealed producer /
attestation pair. The adapter returns:

`NOT_AVAILABLE / SEALED_PROSPECTIVE_TARGET_MATERIALIZER_OR_ATTESTATION_NOT_FOUND`

It does not create a replacement materializer, infer target readiness, or read
target values. Promoting/reusing the retained producer and producing a sealed,
inventory-bound attestation remain explicit dependencies for eventual real
preflight assembly.

## Component disposition

| Component | Adapter disposition | Evidence |
|---|---|---|
| Partial score inventory | `ACCUMULATING` | 2 exact model manifests; artifact bytes re-hashed |
| Canonical counter attestation | `ACCUMULATING` | runtime `x1_counter` only; no inventory binding |
| Official schedule | `READY` | official IDX calendar CSV + complete summary |
| Session Audit / PaperState | `NOT_AVAILABLE` | no persisted attestation discovered |
| Benchmark | `NOT_AVAILABLE` | no persisted benchmark attestation discovered |
| Prior-access audit | `NOT_AVAILABLE` | no persisted audit artifact discovered |
| Code pins | `READY` metadata-only | frozen pin manifest and referenced files present; final gate must revalidate blobs |
| Sealed target materializer/attestation | `NOT_AVAILABLE` | producer/attestation pair not present in active/runtime shapes |

Overall result remains `ACCUMULATING_OUTCOME_BLIND` and is not eligible for the
existing protected-access gate.

## Safety decisions

- no target materializer was added;
- no target/outcome/label/parquet rows were read;
- no runtime artifact was written or modified;
- no canonical counter was read as an authorization and no counter was changed;
- final gate validators remain authoritative and are not replaced by this
  adapter.

## Next dependency

An independently reviewed, sealed prospective target materializer plus a
manifest/attestation producer must be supplied before exact preflight-bundle
assembly can be considered. PaperState/session-audit, benchmark, prior-access,
and inventory-bound counter attestations also remain required.
