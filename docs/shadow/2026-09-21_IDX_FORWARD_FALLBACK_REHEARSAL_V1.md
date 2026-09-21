# IDX-Trade Forward-Only Fallback Rehearsal V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **PASS SYNTHETIC / REAL-STATE REHEARSAL BLOCKED**

## Boundary

The earlier adoption rollback matrix defines a forward-only fallback posture.
It does not authorize a live downgrade from V2 to V1, a scheduler change, a
runtime repin, or a production fallback.

## Required rehearsal sequence

1. Construct a new isolated fallback root from an immutable, hash-bound input
   manifest.
2. Verify candidate and fallback runtime lineage before loading state.
3. Use only explicitly compatible legacy state; quarantine unknown or
   non-ancestor state.
4. Prove create-only/idempotent writes and exact recovery boundaries.
5. Demonstrate that the active root and scheduler remain untouched.
6. Destroy or retain the isolated rehearsal output only under explicit policy;
   never overwrite the active root.

## Isolated synthetic rehearsal

The forward-only sequence was executed once successfully in the dedicated
shadow output root:

`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-operational-shadow\fallback-v3`

The fixture was intentionally shaped as a realistic V2 state with one open
partial BUY obligation/pending intent and one open corporate-action
receivable. The exact sequence was:

1. write and verify the synthetic V2 snapshot;
2. copy it into `frozen_v2` and verify byte/file/runtime-state hashes;
3. persist a `STOP_NEW_EXECUTION` fence and synthetic candidate-failure
   marker;
4. persist a repair marker without changing code, config, scheduler, or
   runtime identity;
5. resume the same frozen V2 snapshot from `resume_v2`;
6. verify the pending intent, quantity obligation, CA receivable, base-state
   hash, runtime-state hash, and frozen-copy hash are unchanged.

Measured result: `SYNTHETIC_FORWARD_ONLY_FALLBACK_PASS`.

| Measure | Result |
|---|---|
| Snapshot/file SHA-256 | `f8f6102a91fc5698aaea0607ad2f61d0cdb4934d0bcbef13737abe1a0ef3e371` before and after resume |
| Runtime-state SHA-256 | `36e7c3c04e797a9d18273099f8229b8862f6efe3db7d6a00dee0dd8557c2cf99` |
| Base-state SHA-256 | `48e882251a4b33ef47970c186c581f5d7147bdaa29d307785a61904fb26370e2` |
| Pending BUYs preserved | 1 |
| Open obligations preserved | 1 |
| Open CA receivables preserved | 1 |
| V1 downgrade attempted | `false` |
| Provider calls / active runtime / scheduler touched | `false / false / false` |

The first two disposable fixture builds stopped before writing a V2 snapshot:
the first exposed the canonical pending-intent projection requirement
(`EXECUTION_V1_OBLIGATION_PENDING_PROJECTION_MISMATCH`), and the second
exposed the synthetic review-admission requirement
(`DIVIDEND_V1_REVIEW_NOT_ADMITTED`). Neither was used as a PASS or deleted;
the successful run used the official pending-intent projection helper and an
explicitly labelled synthetic verifier token. These are fixture-construction
records, not real-runtime failures.

The real fallback gate remains blocked because no real migratable paper-state
artifact was available. This rehearsal closes only the synthetic operational
fallback evidence gap; it does not prove fallback from actual historical state.
