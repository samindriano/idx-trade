# Handoff — V4-X1 Clean Replay / Refit Contract V1

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x-clean-replay-refit-contract-v1`
State: `CONTRACT_FROZEN_WAITING_FOR_FINAL_INPUT_LOCK`

## Frozen contract

- machine-readable contract: `config/ranking_v4_x1_clean_replay_refit_contract_v1.json`
- contract Git blob SHA-1: `36b9ed166efc8b58e37c439bd47d2c6a346ab901`
- checkpoint: `docs/checkpoints/2026-08-20_V4_X1_CLEAN_REPLAY_REFIT_CONTRACT_LOCKED.md`
- parent V4-X1 final model manifest SHA-256: `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`
- accepted PIT identity Stage-C manifest SHA-256: `5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`

## Interpretation

This is remediation of the existing V4-X1 Geometry3 lineage, not a new alpha experiment and not V4-X2. Preserve the exact V4-X1 scientific model contract, including observed-ticker-row feature-window semantics.

Phase A is an outcome-blind structural clean replay only. It may compare support identities, feature representations, and missingness, but it must not load numeric targets, fit/score models, generate historical predictions, or recompute historical performance.

Phase B is not authorized yet. After independent Phase-A review it may be separately authorized to fit exactly four clean models (CONTROL/CHALLENGER x H5/H10), with no tuning, rescue, feature search, or historical performance recomputation.

## Dependencies before Phase A

Do not execute until all are independently accepted and hash-pinned:

1. final V4-X clean-data bundle from the concurrent consolidation lane, including HLC/Open corrections and reconciled FINN/FREN security-master lineage;
2. final Corporate Action continuity disposition (or explicit independently accepted no-change disposition);
3. exact runtime-environment manifest.

A later execution lock may populate only dependency paths/hashes/review anchors. It may not change scientific fields.

## Forward boundary

Do not reset or mutate any forward counter now. Parent V4-X1 scores/models remain archival. If the clean refit later succeeds and is separately activated, the clean generation starts at 0/100 only after the immutable clean model manifest is frozen; earlier V4-X1 sessions do not count toward it.

## Stop

No replay, refit, V4-X2 execution, provider call, historical performance, protected/fresh-forward outcome access, or counter mutation is authorized from this handoff.
