# Canonical EOD Calendar-Parent Attestation V1

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/canonical-eod-calendar-parent-attestation-v1`

Base review: `review/idx-price-trend-runtime-smoke-blocker-v1@face365af462d2e050bb5b5e0c78d3226b1bc911`

## Scope and decision

This remediation addresses only the legacy capture-time calendar-parent
provenance edge for canonical EOD sessions 2026-08-11 and 2026-08-12. Price
State formulas, thresholds, canonical manifests, snapshots, evidence, and
runtime capture artifacts are not rewritten or recaptured.

The implementation adds an immutable sibling-attestation contract and a strict
compatibility verifier. The verifier can be used by the existing Price State
bridge path only when the attestation proves every non-calendar identity and
the accepted bridge calendar proves the official session ordering. Without an
attestation, the existing direct parent-calendar hash failure remains.

No external runtime attestation was materialized in this task: the requested
runtime check was read-only and no Price State smoke was rerun. Synthetic
fixtures exercise the immutable writer and the future compatibility path.

## Read-only audit

Approved runtime root: `idx-trade-data-gate-20260808v`.

Accepted bridge calendar:

- SHA-256: `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`
- session neighbors used for 2026-08-11: 2026-08-10 → 2026-08-11 → 2026-08-12
- session neighbors used for 2026-08-12: 2026-08-11 → 2026-08-12 → 2026-08-13
- membership and ordering are proven from the accepted bridge bytes; no byte-
  identity claim is made for the lost 2026-08-11 parent.

| Session | Manifest SHA-256 | Snapshot SHA-256 | Evidence SHA-256 | Declared calendar SHA-256 | Current SHA at declared path | Result |
|---|---|---|---|---|---|---|
| 2026-08-11 | `8a76175199aebb7bf3a0c0f852134584f1e0bd78cd389123f80d9d3eaa5ad1bd` | `d2dc3b29d51587050011e85dd621bceee3e501bb91419975fc5405cc7423c63e` | `bd4e51374ffd082c9502bba64890d09bdae8d281c4ca8ded466824b9fd948152` | `e61a3b7e01215f43c7fea094afc2c001710e53734eb940c3de57324e841ce9` | `bd33e977ac0dd690e4527f308080f63ebb5a8696d2022448d90d83771c4dfdc3` | `DECLARED_CAPTURE_TIME_CALENDAR_BYTES_UNRECOVERED` |
| 2026-08-12 | `39f5d02a37a59930ed02ecdbf98fbf5260ed2e6ce5754ff7f558d04357e8d51c` | `51cfe9abacd322f330025b0bcd43d569f6fbb715b53aea3c27ead7588d16b00b` | `51abd380f7cc4912b889ca0c8b3ae86c3b3b7ba0ad4b69932edacc9f2eb021b5` | `bd33e977ac0dd690e4527f308080f63ebb5a8696d2022448d90d83771c4dfdc3` | `bd33e977ac0dd690e4527f308080f63ebb5a8696d2022448d90d83771c4dfdc3` | `RECOVERED_AT_DECLARED_PATH` |

Both sessions were `DATA_READY`, had exact session dates in model input,
session evidence, and session OHLCV, and retained `outcome_blind=true` and
`forward_outcomes_accessed=false`. Declared Stock Summary and Index Summary
artifacts were present and hash-consistent for both sessions, with complete
records-total metadata.

An exact SHA search across all 23,756 files under the approved runtime root
found zero files matching the lost 2026-08-11 calendar SHA. The current
calendar is therefore not substituted for the declared parent. Session
2026-08-12 needs no attestation because its declared calendar bytes remain
available at the declared path.

## Contract implemented

New module: `src/idx_trade/canonical_eod_calendar_parent_attestation.py`.

It provides:

- non-writing canonical-session audit;
- strict verification of all declared canonical artifact hashes and session
  semantics before an attestation can be created;
- accepted bridge-calendar SHA, membership, and immediate-neighbor ordering
  proof;
- explicit `DECLARED_CAPTURE_TIME_CALENDAR_BYTES_UNRECOVERED` state;
- deterministic fingerprinting;
- immutable/idempotent write behavior;
- rejection of current mutable-calendar substitution, arbitrary calendars,
  changed declared SHA, tampered canonical artifacts, invalid flags, and
  missing ordering proof.

The existing Price State context bridge now checks this sibling attestation as
a narrowly scoped fallback. It preserves the original declared calendar path
and SHA in provenance and records the attestation path/SHA when the fallback is
used. Direct parent-calendar verification remains the normal path.

## Validation

- Focused attestation + Price State bridge tests: `14 passed`.
- Full pytest: `85 passed, 1 failed` out of `86` collected; the only failure is
  the pre-existing unrelated storage expectation that still expects one
  conflict while current revision auditing reports separate `raw_close` and
  `vendor_adj_close` conflicts.
- `git diff --check`: passed.
- Provider calls: 0.
- Price State smoke rerun: no.
- Outcome/model/trade access: false/not performed.

## Stop condition

This branch stops after the implementation, synthetic adversarial validation,
and read-only 2026-08-11/12 preflight. A subsequent task must independently
review the attestation contract before any runtime attestation write or second
Price State smoke is authorized.
