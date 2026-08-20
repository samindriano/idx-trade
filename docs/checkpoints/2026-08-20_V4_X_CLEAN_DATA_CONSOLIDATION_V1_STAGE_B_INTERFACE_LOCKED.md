# V4-X Clean-Data Consolidation V1 — Stage-B Interface Locked

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `data/v4-x-clean-data-consolidation-v1`

## Purpose

Prepare non-conflicting Stage-B plumbing while the separately owned PIT Security Identity / Listing-Domain Stage-C audit remains ACTIVE.

This checkpoint does **not** decide FREN, KOCI, ticker inclusion/exclusion, listing dates, final universe membership, or whether the identity overlay must be applied. Those decisions remain upstream and require independent acceptance.

## Frozen boundary

Stage A is already materialized and accepted as the clean price-basis candidate:

- Stage-A manifest SHA-256: `eaeabad3c2050142d973d3f8ec350934b995b4e890ea4a12588304d325073969`
- panel bytes: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- rows/tickers: `981,940 / 945`
- HLC repairs: `1,657 / 12`
- Open repairs: `1,655`, plus `2` fail-closed
- Volume/Regular-Market-Value parity: PASS

Stage B will **reference**, not rewrite, the Stage-A panel bytes. Its only possible data-lineage addition is an independently accepted final security master.

## Upstream collision boundary

Canonical TEAM_STATUS currently has:

- `PIT Security Identity / Listing-Domain V1 adversarial audit` — ACTIVE on `audit/pit-security-identity-stage-c-v1`;
- `V4-X clean-data consolidation V1` — WAITING on this branch.

The identity lane owns the scientific identity/listing decision and exact V4-X training-support intersection. This lane owns only the downstream ingestion/validation interface after that decision is independently accepted.

## Required acceptance package

Stage-B materialization cannot run without an explicit small acceptance JSON using schema `v4_x_clean_identity_acceptance_v1` and status `IDENTITY_ADJUDICATION_ACCEPTED_FOR_CLEAN_CONSOLIDATION`.

It must state:

- exact Stage-C manifest SHA-256;
- exact Stage-C status and decision;
- `independent_review_accepted=true`;
- one explicit clean-consolidation action:
  - `APPLY_CERTIFIED_IDENTITY_OVERLAY`, or
  - `PRESERVE_FROZEN_SECURITY_MASTER`;
- accepted identity policy;
- exact identity-overlay SHA/counts when the APPLY action is chosen;
- all frozen guardrails false.

A blocked Stage-C decision is not admissible. The consolidation lane must never infer the action from Stage-C metrics or from ticker names.

## Materialization contract

If APPLY is independently authorized:

1. verify the frozen security master SHA `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`;
2. verify the acceptance JSON pins the exact Stage-C manifest and exact overlay bytes;
3. require the overlay to be right-only relative to the frozen master: no duplicate or replacement `security_id`/ticker identities;
4. construct a deterministic final security master;
5. write a small identity ledger and final clean-input manifest;
6. reference the existing Stage-A panel/provenance/correction-ledger hashes without rewriting those bytes.

If PRESERVE is independently authorized, Stage B requires an empty overlay and the final security master must be exactly the frozen master.

## Final bundle semantics

A successful Stage-B materialization may establish a hash-pinned **final clean input bundle**, but it still does not authorize model refit. The bundle is expected to reference:

- Stage-A clean panel;
- Stage-A field-level provenance sidecar;
- Stage-A correction ledger;
- unchanged official calendar lineage already pinned by Stage A;
- final accepted security master;
- identity acceptance artifact and Stage-C manifest.

## Hard prohibitions

No provider calls, numeric target/return/rank access, predictions, performance inspection, model fit/score/tune, protected/fresh-forward outcomes, forward-counter mutation/reset, HLC/Open redesign, Volume/Value mutation, session-window change, primary-liquidity-rule change, V4-X2 execution, or identity/universe decision-making in this lane.

## Status

`STAGE_B_INTERFACE_FROZEN_WAITING_FOR_IDENTITY_ACCEPTANCE`

Implementation of the generic validator/materializer may proceed now. Actual Stage-B materialization remains blocked until the identity lane completes and an independent acceptance package is created.
