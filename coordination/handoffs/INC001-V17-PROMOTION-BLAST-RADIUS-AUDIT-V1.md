# INC-001 V17 Promotion Blast-Radius Audit V1 Handoff

Date: 2026-08-31 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
Audit tree: `ad6f3bdf10f7768db5b1f597e81fd0d7dc2158a9`

## Decision

`PROMOTION_BLAST_RADIUS_AUDIT=PASS`

The external V17 artifact is not automatically consumed by the tracked
runtime, gate, or tests. The canonical runner imports the R3 gate and still
passes `structural_event_complete=False`, so the current result remains
fail-closed. A 10-check adversarial harness passed against the actual gate:
valid complete evidence passed; structural omission, bad family hash, missing
temporal semantics, uncertified promoted event, and uncertified coverage were
rejected.

## Boundaries

V17 remains a separately manifest-bound reconciliation artifact and does not
rewrite V16 or alter frozen science. Any future admission must use one explicit
reviewed adapter that binds event IDs, accepted transition semantics, family
coverage, temporal as-of evidence, and source hashes to the existing gate.

There are two same-named population-gate functions in the repository. The
canonical runner uses `ca_aware_feature_basis_r3`; the older source-authority
builder uses its own module. This is a non-blocking ownership risk, not a
reason to add another layer now.

## Prohibited actions preserved

No outcomes/targets, Phase-E, fit/refit/score, market-provider calls,
counter/PaperState/R2, V16 mutation, production execution, deployment,
backfill, or Actions rerun occurred.

Stop for review before any new adapter or admission wiring.
