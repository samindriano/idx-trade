# V4-X1 Clean Phase-A Execution Lock — Frozen

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x1-clean-phase-a-execution-lock-v1`
Status: `V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_FROZEN_LOCAL_CAPTURE_REQUIRED`

## Decision

The hash-only execution contract for the clean V4-X1 Phase-A structural replay is frozen before any clean replay, numeric target access, model fit, prediction, or performance access.

This execution branch is based on the exact scientific V4-X1 lineage (`research/price-basis-clean-refit-v1`) rather than the documentation-only clean-contract branch. The accepted clean contract is pinned cross-branch by immutable commit/blob identity.

## Clean contract pin

- Git ref: `2bc38c4d4a966dd57be0cb62211ed47c32ce7be9`
- path: `config/ranking_v4_x1_clean_replay_refit_contract_v1.json`
- Git blob SHA-1: `6b46c622d2c620cc8c89ea42ca979e52080f8ed7`

## Accepted external-input pins

- final clean bundle manifest SHA-256: `561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`
- clean panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- final security master SHA-256: `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`
- field-level provenance parquet SHA-256: `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`
- V4-3R CA80 prefit manifest SHA-256: `0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc`

## Runtime pin

The accepted V4 prefit runtime is reused exactly:

- immutable Git ref: `ffa79256c4c8f2e202047bab5a9c8a4f3ddd3218`
- runtime manifest path: `docs/artifacts/ranking_v4_3_prefit_runtime_v1/v4_3_prefit_environment_manifest.json`
- Git blob SHA-1: `20f971be7d16c8b64def6829448b9a6a6091ba3b`
- manifest SHA-256: `cf6f1b0c859dd21b1c0f377f45d62ecdc98165ff6e0975b852a85b11cfbcaac6`

The local capture runner fails closed unless Python and the exact package versions inside this manifest match.

## Frozen implementation

Machine-readable execution lock:

- `config/ranking_v4_x1_clean_phase_a_execution_lock_v1.json`
- Git blob SHA-1: `d9660e7f3323a12d4edee032d4a4f7e3cd55dc7e`

Hash-only capture runner:

- `scripts/capture_v4_x1_clean_phase_a_execution_lock.py`
- runner is pinned by the execution-lock config and must match exactly at local capture.

Focused guard tests:

- `tests/test_v4_x1_clean_phase_a_execution_lock.py`
- tests are pinned by the execution-lock config and must pass before capture.

The lock also pins the inherited V4-X1/V4-3R scientific blobs, including the final-refit runner, historical one-shot runner, CA80 preregistration, V4 feature/target/model/support code, and X1 decision/evaluation code.

## Allowed local capture

The next local action may only:

1. verify a clean Git worktree;
2. run the focused execution-lock tests / compile / diff check;
3. verify exact Git blobs and immutable cross-ref blobs;
4. verify the exact historical runtime environment;
5. hash-check the accepted clean bundle, clean panel, security master, provenance, and CA80 prefit manifest;
6. write one new immutable `v4_x1_clean_phase_a_execution_lock_manifest.json`.

A successful capture status must be:

`V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_CAPTURED_REPLAY_NOT_RUN`

## Hard exclusions

No Phase-A structural replay during the lock capture itself. No target numeric values, returns/ranks, target materialization, model fit/scoring, historical prediction/performance, provider/network call, protected/fresh-forward outcome, counter mutation, data repair, CA acquisition/semantic change, session-aligned semantics, tuning, or rescue.

## Next

`RUN_ONE_LOCAL_HASH_ONLY_LOCK_CAPTURE_THEN_STOP_FOR_REVIEW`
