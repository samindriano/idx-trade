# IDX-Trade Controlled Canary Design V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **DESIGN ONLY / CANARY NOT AUTHORIZED OR EXECUTED**

## Preconditions

The canary must not start until the following are independently PASS:

- immutable real shadow input copy with two-pass source stability and copy
  hashes;
- real state migration classifications with no unknown/unreconciled rows;
- old-vs-candidate differential on identical read-only artifacts;
- historical replay and CA composition evidence;
- real recovery and forward-only fallback rehearsal;
- authoritative identity/config lineage;
- explicit policy decisions and an independent challenge;
- active scheduler/cloud/provider scope separately authorized.

## Proposed controlled sequence

1. Freeze and hash the candidate, config, runner, schedule attestation, and
   identity artifact.
2. Create a new shadow/canary root; never reuse the active writable root.
3. Load only the immutable manifest and verify all hashes before any phase.
4. Run one bounded session with outcome access disabled and no model refit,
   provider mutation, or canonical-data write.
5. Compare lifecycle, state, CA, recovery, and output hashes against the
   predeclared acceptance matrix.
6. Stop on the first gate failure; do not retry the failed live operation.
7. Keep the active pinned runtime unchanged until a separate promotion review.

## Current decision

This design is not a launch authorization. Because G-01 through G-10 remain
open, `CONTROLLED_CANARY = NO-GO / NOT EXECUTED` and `PRODUCTION = NO-GO`.
