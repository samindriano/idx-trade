# IDX Malformed Latest Snapshot Recovery Audit V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`  
Verdict: `FAIL — LATEST_SNAPSHOT_FAILURE_NO_RECOVERY`

## Scope and safety

This is a read-only runtime-contract audit. It did not modify the pinned
runtime checkout, production/canonical data, cloud/capture/telemetry state,
scheduler, or protected outcomes. The only writes were synthetic snapshots
under a pytest temporary directory, using the exact retained runtime source.

Pinned runtime:

- Commit: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
- Source: `src/idx_trade/forward_dividend_runtime_v1_1.py`
- Source SHA-256: `98ebc637340757f03e36c3c8b876f134022ca1282b9bad35cf573b4b784eca23`

## Probe

Each synthetic case created a valid two-session chain (`2026-08-20.json` →
`2026-08-21.json`) and then corrupted only the latest snapshot:

1. malformed JSON (`{`); and
2. valid JSON with a changed cash field but the old declared payload hash.

For each case, `load_latest_runtime_snapshot()` was called twice. The prior
snapshot was also loaded directly to distinguish a corrupted latest artifact
from a corrupted full chain.

| Case | Latest-loader result | Latest file | Prior file | Direct prior load | Fallback/quarantine |
|---|---|---:|---:|---:|---:|
| Malformed latest JSON | `DIVIDEND_V1_1_RUNTIME_SNAPSHOT_INVALID` on both calls | remains | remains | succeeds | not observed |
| Latest payload tamper | `DIVIDEND_V1_1_RUNTIME_SNAPSHOT_PAYLOAD_SHA_MISMATCH` on both calls | remains | remains | succeeds | not observed |

The result is deterministic fail-closed selection, but not automatic recovery.
The loader chooses the chronologically latest filename first and propagates its
verification error. It does not quarantine/delete the invalid file or fall
back to the valid prior ancestor. A later call therefore encounters the same
poisoned latest artifact until an operator or an authorized recovery process
handles it outside this runtime function.

## Static contract evidence

`load_latest_runtime_snapshot()` builds candidates, sorts by session date, and
immediately calls `load_runtime_snapshot(candidates[-1][1])`. The function has
no quarantine, candidate-skip, prior-ancestor fallback, or recovery-manifest
branch. The later ancestor walk runs only after the latest snapshot verifies.

## Impact and boundary

This is an availability/recovery finding, not evidence that the hash checks
are weak. The latest artifact correctly fails closed, and the valid prior
snapshot remains independently loadable. However, a single malformed or
tampered latest file blocks the normal “load latest” path even when an intact
ancestor exists. Existing atomic-write behavior reduces the chance of a
partial write, but does not define post-write corruption, quarantine, or
operator recovery semantics.

Finding: `SYS-REC-003`.

No runtime fix is applied. Reopen only with an explicitly authorized recovery
contract that preserves immutability, records the rejected artifact and reason,
and proves that fallback cannot silently bypass a valid chain fork or missing
session.

## Reproduction artifacts

- Probe: `research/idx_malformed_latest_snapshot_recovery_probe_v1.py`
- Test: `tests/test_idx_malformed_latest_snapshot_recovery_probe_v1.py`
- Focused result: `1 passed`
