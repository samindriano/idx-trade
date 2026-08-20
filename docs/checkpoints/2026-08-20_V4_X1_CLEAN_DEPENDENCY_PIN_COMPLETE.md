# V4-X1 Clean Remediation — Dependency Pin Complete

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x-clean-replay-refit-contract-v1`
Status: `V4_X1_CLEAN_DEPENDENCIES_PINNED_PHASE_A_EXECUTION_LOCK_NEXT`

## Completed pins

The clean-remediation contract now has both non-runtime dependencies accepted and hash-pinned before any clean structural replay or model fit.

### Final clean input bundle

Acceptance checkpoint commit:

`175210d8193e1d9ded6a988d1df26e517a378260`

Acceptance checkpoint:

`docs/checkpoints/2026-08-20_V4_X1_CLEAN_FINAL_INPUT_BUNDLE_ACCEPTANCE_PIN.md`

Accepted final bundle manifest SHA-256:

`561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`

Accepted clean panel SHA-256:

`25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`

Accepted final security master SHA-256:

`51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`

Accepted field-level provenance parquet SHA-256:

`cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`

### Corporate Action disposition

Acceptance checkpoint commit:

`ee9db46c7b55af7b961612c7264a302d0a9f0a0d`

Status:

`V4_X1_CLEAN_CA_DISPOSITION_ACCEPTED_REUSE_PARENT_CA80_RECOMPUTE_ON_CLEAN_INPUT`

Pinned CA80 prefit manifest SHA-256:

`0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc`

## Contract pin

The machine-readable contract was updated in commit:

`2bc38c4d4a966dd57be0cb62211ed47c32ce7be9`

Path:

`config/ranking_v4_x1_clean_replay_refit_contract_v1.json`

Git blob SHA-1 after dependency pin:

`6b46c622d2c620cc8c89ea42ca979e52080f8ed7`

Contract status:

`V4_X1_CLEAN_REPLAY_REFIT_CONTRACT_FROZEN_EXECUTION_LOCK_NEXT`

## Remaining dependency

Only the runtime environment / Phase-A execution lock remains unpinned.

The execution lock may pin exact runtime/package/code/input identities only. It may not alter the scientific contract.

## Still not authorized

- Phase-A runtime before the separate execution lock is frozen and reviewed;
- any model fit;
- historical predictions/performance recomputation;
- numeric target inspection during Phase A;
- provider/network calls;
- protected/fresh-forward outcomes;
- forward-counter reset/mutation;
- V4-X2/session-aligned semantics;
- new data repair or Corporate Action acquisition;
- tuning or rescue.

Next:

`FREEZE_HASH_ONLY_PHASE_A_EXECUTION_LOCK`
