# IDX V4-X Clean-Data Consolidation V1 — Claim

Date: 2026-08-20 (Asia/Jakarta)
Owner: `ChatGPT/V4-X-Clean-Data-Consolidation`
Branch: `data/v4-x-clean-data-consolidation-v1`
Status: `WAITING_STAGE_B_INTERFACE_PREPARED_IDENTITY_ACCEPTANCE_REQUIRED`
Base main at lane creation: `79d4d6c2a02eb3677aa8e1d90fa22eacbf2451b9`

## Completed scope

Stage A is materialized and accepted:

- manifest SHA-256 `eaeabad3c2050142d973d3f8ec350934b995b4e890ea4a12588304d325073969`;
- exact parent population `981,940` rows / `945` tickers;
- accepted H/L/C corrections `1,657` rows / `12` tickers;
- accepted Open corrections `1,655` rows (`1,216` official IDX + `439` CA-factor fallback) with `2` fail-closed candidates;
- Volume and Regular-Market Value parity PASS;
- no identity/universe mutation.

The generic Stage-B interface is now also prepared and frozen. It can only consume an independently accepted identity package after the separately owned identity lane completes. It cannot infer or adjudicate that decision itself.

## Current owned scope

This lane owns only downstream offline consolidation and lineage packaging:

- preserve and hash-verify the accepted Stage-A panel/provenance/correction-ledger bytes;
- after independent identity acceptance, validate the exact Stage-C manifest and accepted action;
- deterministically materialize the final security master from the accepted identity action;
- produce a hash-pinned final clean-input bundle that references, rather than rewrites, Stage-A bytes;
- stop before deterministic replay/refit authorization.

## Explicit non-ownership / collision boundary

The concurrent ACTIVE lane `PIT Security Identity / Listing-Domain V1 adversarial audit` on `audit/pit-security-identity-stage-c-v1` owns FREN/KOCI, listing-domain correctness, ticker inclusion/exclusion, identity scientific adjudication, and exact V4-X final-training support intersection.

This consolidation lane MUST NOT:

- decide whether FREN/KOCI or any ticker belongs in the final clean universe;
- derive an identity action from Stage-C metrics or ticker names;
- add/drop/repair ticker identities or listing domains without an independently accepted identity package;
- reconstruct the final training support;
- mutate the concurrent identity lane.

Actual Stage-B materialization therefore remains blocked until the identity result is independently reviewed and represented by the frozen acceptance contract.

## Stage-B frozen interface

- config: `config/v4_x_clean_data_stage_b_interface_v1.json`
- protocol checkpoint: `docs/checkpoints/2026-08-20_V4_X_CLEAN_DATA_CONSOLIDATION_V1_STAGE_B_INTERFACE_LOCKED.md`
- helper: `src/idx_trade/v4_x_clean_data_stage_b.py`
- runner: `scripts/run_v4_x_clean_data_stage_b_v1.py`
- focused tests: `tests/test_v4_x_clean_data_stage_b.py`

The runner is fail-closed on exact Stage-A hashes, frozen security-master hash, independent acceptance, Stage-C manifest hash/decision, identity-overlay hash/counts when applicable, all guardrails, and frozen helper/runner Git blobs.

## Other hard exclusions

No provider calls, numeric target/return/rank access, predictions/performance inspection, model fit/scoring/tuning, protected/fresh-forward outcome access, forward-counter mutation/reset, HLC/Open redesign, Volume/Value mutation, feature/window semantic change, primary-liquidity-rule change, parent-panel overwrite, or V4-X2 execution.

V4-X2 session-aligned work remains separate and preregistered only.
