# Canonical EOD Calendar-Parent Attestation V1 — Temporal Remediation

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/canonical-eod-calendar-parent-attestation-v1`

Independent review: `review/idx-price-trend-runtime-smoke-blocker-v1@d862d3ac22672b30642cd2f5285f292b2b2645ac`

## Remediation scope

The accepted audit result and canonical 2026-08-11/12 artifacts were preserved.
Only the two verifier temporal dependencies identified by review were changed:

1. `current_declared_calendar_path_sha256` remains immutable audit-time
   diagnostic evidence, but verifier no longer compares it with the mutable
   shared calendar later.
2. The audit-time result that the old declared SHA was not found remains
   immutable diagnostic evidence, but verifier no longer rescans the runtime
   or rejects later recovery of an exact copy.

The verifier now requires the original `calendar_path` and `calendar_sha256`
to remain unchanged in the hash-pinned canonical manifest. It still verifies
the full canonical artifact/session contract, bridge identity and ordering,
fingerprint, and all prohibited-access flags.

The writer now creates the fully serialized file through a same-directory
temporary file, flush/fsync, and exclusive hard-link publication. A competing
writer cannot overwrite a valid attestation; identical content is idempotent
and different content fails closed.

## Required adversarial behavior

Covered by tests:

- later normal extension/mutation of the shared calendar remains valid;
- later exact recovery of the old calendar elsewhere remains valid;
- even later current-path recovery of the old bytes does not become a new
  attestation invariant;
- changing the canonical manifest's original declared calendar SHA fails;
- canonical manifest, snapshot, or evidence tampering fails;
- wrong session/order and bridge SHA/path tampering fail;
- missing attestation retains the existing strict parent-calendar failure;
- idempotent/exclusive immutable writer behavior remains enforced.

## Read-only runtime preflight

No runtime attestation was written and no Price State smoke was rerun.

- 2026-08-11: `DECLARED_CAPTURE_TIME_CALENDAR_BYTES_UNRECOVERED`, zero exact
  SHA matches in the approved runtime-root scan; official bridge neighbors
  2026-08-10 and 2026-08-12.
- 2026-08-12: `RECOVERED` at its declared path; official bridge neighbors
  2026-08-11 and 2026-08-13.

Both sessions remain untouched and outcome-blind. Provider calls and outcome,
model, and trade-state access remain zero/false.

## Validation

- Focused attestation + Price State bridge tests: `15 passed`.
- Full pytest: `86 passed, 1 failed` out of `87` collected. The only failure is
  the unrelated existing storage test expecting one revision conflict while
  current behavior reports separate `raw_close` and `vendor_adj_close`
  conflicts.
- `git diff --check`: passed.

## Decision

`TEMPORAL_DEPENDENCY_REMEDIATED_REVIEW_REQUIRED`.

Runtime attestation materialization and a second Price State smoke remain
blocked pending independent review of this remediation.
