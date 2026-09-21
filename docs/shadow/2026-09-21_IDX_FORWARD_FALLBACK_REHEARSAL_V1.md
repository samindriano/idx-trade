# IDX-Trade Forward-Only Fallback Rehearsal V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **DESIGN RECORDED / REAL REHEARSAL NOT EXECUTED**

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

None of these real fallback steps was started in this packet. The result is
`FORWARD_FALLBACK = DESIGN_ONLY`, not PASS.
