# V4-X1 Clean Replay / Refit Contract V1 — LOCKED

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x-clean-replay-refit-contract-v1`
Status: `V4_X1_CLEAN_REPLAY_REFIT_CONTRACT_FROZEN_EXECUTION_BLOCKED_PENDING_FINAL_INPUT_LOCK`

## Purpose

Freeze the remediation procedure for V4-X1 before any clean-model result or performance can be observed. This is not a new alpha experiment and not V4-X2.

The parent V4-X1 generation is `V4_X1_GEOMETRY3_PROSPECTIVE`. Its successful historical-training-only final refit remains pinned by manifest SHA-256 `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`. The parent explicitly generated no historical predictions/performance and accessed no protected forward outcome.

Machine-readable contract:

`config/ranking_v4_x1_clean_replay_refit_contract_v1.json`

Git blob SHA-1:

`36b9ed166efc8b58e37c439bd47d2c6a346ab901`

## What is frozen

The clean remediation inherits the exact V4-X1 scientific contract:

- control `V4_CONTROL_CONTEXT25_HGBR`;
- Geometry3 challenger `V4_CHALLENGER_SESSION_GEOMETRY3`;
- 25 control features / 28 challenger features;
- the same three Geometry3 additions;
- the same observed-ticker-row window semantics used by V4-X1;
- the same H5/H10 target definitions and consensus weighting;
- the same primary-liquidity rule;
- the same learner, preprocessing, target-rank transform, and hyperparameters;
- the same frozen historical end boundary;
- exactly four final fits if/when Phase B is separately authorized.

Strict official-session feature semantics are explicitly NOT part of this remediation. They remain isolated in the already-frozen V4-X2 challenger.

## Accepted reason for remediation

PIT Security Identity Stage C is pinned by manifest SHA-256:

`5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`

Verdict:

`V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION`

Therefore the final clean input must consume the independently accepted reconciled historical security-master lineage, including generic FINN + FREN right-only restoration. This contract does not derive or apply that correction itself.

## Phase A — clean representation replay

Phase A is outcome-blind and must happen only after a separate execution lock pins the independently accepted final clean-data bundle and the final CA disposition.

It may rebuild clean features/model frames and training-support identities under the frozen V4-X1 rules, then report old-vs-clean support, representation, and missingness deltas.

It may use only target state/availability information where needed for support reconstruction. It must not load numeric target values, fit/score a model, generate historical predictions, or compute historical performance.

Changes to support are not automatically an error. They must be deterministic consequences of the accepted clean lineage; unexplained changes fail closed.

## Phase B — clean final refit

Phase B is NOT authorized by this checkpoint.

After independent review of Phase A, a separate authorization may fit exactly:

1. CONTROL H5
2. CONTROL H10
3. CHALLENGER H5
4. CHALLENGER H10

Historical rows are training-only. Historical predictions, historical performance recomputation, model selection, rescue variants, feature search, and hyperparameter tuning remain forbidden.

A successful refit must emit one immutable four-model manifest with all input/code hashes.

## Dependency slots intentionally unresolved today

The contract is scientifically frozen even though execution inputs are not yet available. A later execution lock may fill only:

- accepted final clean-data bundle review anchor + manifest/panel/security-master/provenance hashes;
- accepted final Corporate Action continuity disposition + manifest hash, or an explicit independently accepted no-change disposition;
- runtime-environment manifest hash and exact paths.

It may not change any scientific field.

## Forward-generation transition

No forward counter is reset now.

If a clean refit later succeeds and is separately activated, it becomes a new generation: `V4_X1_CLEAN_REMEDIATED_PROSPECTIVE_V1`.

Parent V4-X1 models/scores remain archival. Existing or pre-freeze forward score sessions cannot count toward the clean generation. The clean generation starts at `0/100` only after its immutable model manifest is frozen and activation is authorized. The first eligible session is the first source-certified official IDX session strictly after that freeze; do not infer a calendar date in advance.

The outcome vault remains sealed until 100/100 clean-generation score sessions are captured and H10 for score session 100 is mature.

## Current stop

`WAIT_FOR_FINAL_CLEAN_BUNDLE_AND_CA_DISPOSITION_THEN_CREATE_HASH_ONLY_EXECUTION_LOCK`

Do not run Phase A, Phase B, V4-X2, historical performance, or forward-counter mutation from this lane yet.
