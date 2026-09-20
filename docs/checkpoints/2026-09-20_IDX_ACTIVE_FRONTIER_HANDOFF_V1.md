# IDX Active Frontier Handoff V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`

## Active frontier

**Quantity-obligation contract → historical replay compatibility → isolated remediation harness**

## Current hypothesis

The system tracks target membership but not target quantity obligations. A positive partial buy can therefore look complete to execution, persistence, Decision, risk, and evaluation layers even though the requested notional was not delivered.

## Evidence completed

- Exact retained runtime source commit audited: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`.
- Existing focused execution/sizing/E2E suite: 59 passed.
- Synthetic positive partial buy: planned 5,000, filled 2,500, pending empty.
- Next session: no retry intent, position remains 2,500.
- Snapshot round-trip: same partial position, no pending, runtime hash equal.
- Durable checkpoint: `2026-09-20_IDX_SIZING_EXECUTION_PARTIAL_BUY_AUDIT_V1.md`.
- Trigger matrix: capacity/Open change, fee boundary, stamp-threshold boundary,
  and resolved paired replacement all produced positive underfill with empty
  pending state and no next-session retry.
- Durable checkpoint: `2026-09-20_IDX_PARTIAL_BUY_TRIGGER_MATRIX_V1.md`.
- Decision V2 ten-seat probe: one 2,400/5,000 partial seat plus nine full seats
  still produced `FULL`, zero unfilled slots, and no retry on the next plan.
- Positive underfill composed with synthetic cash-dividend lifecycle: actual
  1,200 shares received IDR 30,000 entitlement/settlement versus IDR 125,000
  planned-share hypothetical; CA replay remained exactly-once.
- Existing dividend-aware runtime snapshot reload preserved `AAA:1,200`, empty
  pending buys, and equal runtime hash; this is faithful persistence, not
  residual recovery.
- Serializer probe was a negative result: prepared execution payloads preserve
  per-entry planned sizing; the unresolved owner is filled/remaining quantity
  linkage in execution state and pending obligations.
- Full orchestration staged recovery returned identical execution/snapshot hashes
  after deleting both outputs, but preserved `T00:2,400` and empty pending buys.
- Historical archaeology confirmed an entry/exit asymmetry: positive partial
  sells were explicitly made pending in `d8d34b79`, while positive partial buys
  remained membership-complete in the earlier `e1531b3c` contract and replay
  oracle `ce91d60a`.
- New four-session synthetic matrix: repeated partial exits reduced `AAA`
  5,000 → 4,000 → 3,000 → 2,000, then zero capacity left the sell/buy pair
  pending; no age, attempt, or remaining-share field existed in the pending
  schema.
- CA composition: the original 5,000-share cum-date entitlement settled
  IDR125,000 exactly once; cash changed while the pending replacement remained
  unchanged.
- Target reversal: the Decision V2 adapter explicitly recognized shadow `BBB`
  → target `AAA`, produced no effective orders or fills, and removed both
  pending rows. No typed cancellation event or obligation lineage was emitted,
  leaving expiry/escalation and audit policy unresolved.
- Durable checkpoint: `2026-09-20_IDX_PENDING_CA_REVERSAL_MATRIX_V1.md`.
- Evidence-driven design checkpoint: `2026-09-20_IDX_QUANTITY_OBLIGATION_STATE_CONTRACT_V1.md`.
- Historical compatibility checkpoint: `2026-09-20_IDX_OBLIGATION_HISTORICAL_COMPATIBILITY_AUDIT_V1.md`.
- Spec harness checkpoint: `2026-09-20_IDX_QUANTITY_OBLIGATION_REPLAY_HARNESS_V1.md`.
- SELL/replacement harness checkpoint: `2026-09-20_IDX_QUANTITY_OBLIGATION_REPLACEMENT_REPLAY_V1.md`.
- Artifact boundary checkpoint: `2026-09-20_IDX_OBLIGATION_ARTIFACT_SERIALIZATION_BOUNDARY_V1.md`.
- Migration audit checkpoint: `2026-09-20_IDX_OBLIGATION_ARTIFACT_MIGRATION_AUDIT_V1.md`.
  The isolated 6/6 harness recovers only complete fills, explicit zero-lot
  pending, and positive partials backed by preserved fill vectors; a
  snapshot-only positive position remains `UNKNOWN_ORPHANED_PARTIAL`.
- Identity collision checkpoint: `2026-09-20_IDX_UNIVERSE_IDENTITY_COLLISION_AUDIT_V1.md`.
  The pinned runtime emits two selected `ABCD` rows from `ABCD` and `ABCD.JK`
  input aliases; the later Decision adapter rejects the duplicate, but the
  universe origin has no uniqueness guard.
- Runtime-config revalidation checkpoint: `2026-09-20_IDX_RUNTIME_CONFIG_ARTIFACT_IDENTITY_REVALIDATION_V1.md`.
  At current runtime HEAD `402fca4b...`, config/runner hashes remain present in
  the loader but absent from prepared/execution orchestration artifact identity.
- Security-master revision checkpoint: `2026-09-20_IDX_SECURITY_MASTER_REVISION_COLLISION_AUDIT_V1.md`.
  Historical archaeology confirms active-vs-delisted preference is intentional;
  the unresolved defect is same-class revision order sensitivity.
- Reconciliation provenance checkpoint: `2026-09-20_IDX_RECONCILIATION_FLAG_PROVENANCE_AUDIT_V1.md`.
  The pinned runtime carries `reconciliation_required` through state/hash and
  uses it as a prior gate, but does not produce it from a mismatch detector;
  `false` is not reconciliation evidence.
- Exposure/cash taxonomy checkpoint: `2026-09-20_IDX_EXPOSURE_CASH_STATE_TAXONOMY_AUDIT_V1.md`.
  Decision artifacts preserve `capacity_state`/`unfilled_slots`, but the
  restartable state and shadow reconstruction do not; no-challenger and
  capacity-limited histories can therefore converge to the same state hash.
- Legacy fixture inventory checkpoint: `2026-09-20_IDX_LEGACY_OBLIGATION_FIXTURE_INVENTORY_V1.md`.
  The pinned runtime checkout is clean but contains no retained execution,
  snapshot, or fill-vector fixture; the migration harness remains synthetic
  until an authorized archive/artifact owner supplies provenance-bound data.
- Post-entry risk checkpoint: `2026-09-20_IDX_POST_ENTRY_WEIGHT_DRIFT_AUDIT_V1.md`.
  A synthetic 3x winner reaches 25% mark-to-market weight against a 15% entry
  cap; no active continuing risk overlay or mark lineage exists in PaperState.
- Formula-independence checkpoint: `2026-09-20_IDX_PROSPECTIVE_FORMULA_INDEPENDENCE_AUDIT_V1.md`.
  The protected gate and development evaluator share all five metric function
  objects; provenance/pin checks are independent, formula recomputation is not.
- Execution-evaluation quantity checkpoint: `2026-09-20_IDX_EXECUTION_EVALUATION_QUANTITY_BOUNDARY_AUDIT_V1.md`.
  The protected execution validator admits only aggregate gross notional/NAV
  columns; planned-versus-filled quantity and residual obligations are absent.
- Malformed-latest recovery checkpoint: `2026-09-20_IDX_MALFORMED_LATEST_SNAPSHOT_RECOVERY_AUDIT_V1.md`.
  The exact runtime fails closed on malformed or payload-tampered latest
  snapshots, but leaves the poisoned file in place and does not fall back to
  the valid prior ancestor; direct prior loading remains possible.

## Immediate next questions

1. Which authorized external/archive source can provide real retained legacy
   fixtures with enough fill-vector evidence to be migrated as complete,
   zero-lot pending, or recoverable partial?
2. Can an authorized versioned replay harness prove one obligation identity
   across partial fill, retry, CA payment, reversal, and restart?
3. Which versioned event-level fields can be added to actual snapshots/fills
   without changing the old oracle?
4. Which recovery invariant should reconcile the obligation ledger after
   restart or interrupted execution?
5. What evidence would justify moving the proposal from design-only to a
   separately authorized implementation lane?
6. Which other row-oriented consumers can receive the duplicate universe
   output before the Decision duplicate-ticker guard?
7. What separately authorized versioned stage/artifact contract can bind
   runtime config and runner identity without rewriting historical artifacts?
8. Which source/revision policy should adjudicate same-key security-master
   conflicts before universe eligibility is derived?
9. What explicit evidence source and mismatch taxonomy should produce
   `reconciliation_required=true`, and how should that evidence survive replay
   and restart?
10. Which versioned state owner should preserve exposure/cash causes and join
    them to quantity obligations without fabricating legacy history?
11. Is continuing post-entry weight/concentration control intentionally out of
    scope, or does paper admissibility require a separately authorized overlay?
12. Which independently reviewed formula oracle or verifier contract should be
    bound to the prospective evaluation gate without opening protected outcomes?
13. Which versioned execution-evidence join should bind planned, filled,
    remaining, position, pending, and cost state to evaluation metrics?
14. What authorized immutable recovery/quarantine manifest should handle a
    poisoned latest snapshot without silently bypassing a fork or missing
    session?

## Constraints

- No source patch has been applied.
- No production, canonical data, cloud/capture/telemetry, scheduler, or protected outcome access.
- No push or merge.
- New external data acquisition remains owned by another lane.

## Durable references

- Master dossier: `docs/checkpoints/2026-09-20_IDX_SYSTEM_DEEP_DIVE_AND_FULL_HISTORY_V1.md`
- Frontier matrix: `docs/checkpoints/2026-09-20_IDX_SYSTEM_FRONTIER_MATRIX_V1.md`
- Findings/no-retry log: `docs/checkpoints/2026-09-20_IDX_SYSTEM_FINDINGS_NO_RETRY_LOG_V1.md`
