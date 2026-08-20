# Claim — V4-X1 Clean Historical OOS Replay V1

Date: 2026-08-20 (Asia/Jakarta)
Status: `WAITING_LOCAL_ONE_SHOT_EXECUTION`
Owner: `ChatGPT/V4-X1-Clean-Historical-OOS-Replay`
Branch: `research/idx-v4-x1-clean-historical-oos-replay-v1`

## Scope

Measure historical out-of-sample rank-IC/Spearman for the already-deployed accepted clean V4-X1 representation.

This is a locked post-selection robustness replay, not a new model-selection opportunity. It reuses:

- accepted clean Phase-A representation and Open-lineage policy;
- clean security master and clean panel identities;
- inherited CA80 target/support semantics;
- exact frozen 600 validation dates / 6 x 100 folds;
- exact 10-official-session purge;
- exact CONTROL Context25 and CHALLENGER Geometry3 feature sets;
- exact HGBR learner/hyperparameters;
- exact H5/H10/consensus ranking and IC definitions.

Exactly 24 fits are allowed: CONTROL/CHALLENGER x H5/H10 x six folds.

## Frozen preparation

Controlling checkpoint:

`docs/checkpoints/2026-08-20_V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_FROZEN.md`

Decision:

`V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_FROZEN_LOCAL_EXECUTION_AUTHORIZED`

Frozen implementation:

- runner `scripts/run_v4_x1_clean_historical_oos_replay.py`, blob `273ec17f8d2da0d23ac5d2e9f08661b6ff6a35d7`;
- config `config/ranking_v4_x1_clean_historical_oos_replay_v1.json`, blob `583fe1791e0f2534032a41713e56a18f6d968e80`;
- launcher `scripts/run_v4_x1_clean_historical_oos_one_shot.ps1`, blob `61ff3424dbf51c26d8dd190653bd9dfe9945f953`.

The launcher resolves the accepted external bytes by SHA and refuses an existing output directory. The next action is exactly one local execution because the required historical panel/CA artifacts live only on the user's Windows `D:\...` runtime.

## Output rule

If execution is valid, the clean CHALLENGER consensus median fold mean daily IC becomes the canonical historical OOS score reported for the deployed clean model. The old pre-clean score remains only a parent benchmark.

The replay also reports H5/H10, Control, Challenger-Control deltas, q25, positive-fold counts, and bootstrap CIs using the existing frozen evaluator.

## Hard boundaries

- no hyperparameter search or retune;
- no model/feature/universe/CA80/session-semantic changes;
- no provider/network calls;
- no prospective score/counter mutation;
- no protected/fresh-forward outcome access;
- no use of this result to change the currently deployed model generation;
- no historical target materialization for signal dates after the frozen validation end (session 1249 / 2026-07-17).

Canonical `main:coordination/TEAM_STATUS.md` was read before starting. No duplicate ACTIVE clean historical replay lane was visible. The shared ledger is too large to safely overwrite from a truncated connector fetch; local execution may update only this lane minimally if coordination is needed.
