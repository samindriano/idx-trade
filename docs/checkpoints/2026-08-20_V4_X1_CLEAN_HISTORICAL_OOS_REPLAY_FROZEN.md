# V4-X1 Clean Historical OOS Replay — Frozen

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x1-clean-historical-oos-replay-v1`

## Decision

`V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_FROZEN_LOCAL_EXECUTION_AUTHORIZED`

The accepted clean V4-X1 model lineage now has a separately locked historical OOS robustness replay. This replay exists to measure the historical rank-IC/Spearman of the **clean representation actually deployed**, rather than continuing to quote the pre-clean parent score.

## Why this replay exists

The clean Phase-B final refit deliberately performed no historical scoring/performance recomputation. That preserved a strict prospective boundary, but it also left the deployed clean model without a measured clean historical OOS benchmark.

The correct measurement is not to score the four all-history final-refit model bytes back on their training history. Instead this replay rebuilds the same historical walk-forward experiment:

- 6 frozen validation folds;
- 100 dates per fold;
- exact inherited purge of 10 official sessions;
- CONTROL Context25 and CHALLENGER Geometry3;
- H5 and H10 heads;
- same HGBR learner/hyperparameters;
- same within-date percentile ranking;
- same CA80 target/evaluation semantics;
- same H5/H10/consensus rank-IC evaluator.

Exactly `24` fits are permitted (`2 modes x 6 folds x 2 heads`).

## Clean representation

The replay must rebuild from the already accepted clean lineage:

- accepted clean Phase-A manifest SHA-256 `f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`;
- clean panel SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`;
- clean security master SHA-256 `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`;
- accepted clean primary rows `348,762`;
- clean H5/H10 support rows `239,648 / 237,976`;
- Open-lineage policy `PRESERVE_PARENT_EXECUTABLE_OPEN_EXCEPT_ACCEPTED_STAGE_A_CANDIDATES_V1`.

Validation-fold SHA-256 remains `91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915` and frozen validation end remains session `1249`, date `2026-07-17`.

Historical signal identities after that boundary are prohibited. Future bars needed only to mature H5/H10 targets for an already-frozen validation signal date may be read from the accepted historical panel.

## Parent benchmark

The exact pre-clean V4-3R benchmark carried only for comparison is:

- CONTROL consensus median fold mean daily IC `0.08415844149089491`;
- CHALLENGER consensus median fold mean daily IC `0.09775243938276076`;
- CHALLENGER H5 `0.07891122009359626`;
- CHALLENGER H10 `0.09095594288451861`;
- consensus incremental median delta `+0.013593997891865855`.

These remain the **pre-clean parent** metrics. They are not the historical score of the deployed clean model once a valid clean replay result exists.

## Canonical-score rule

If the exactly-once replay is execution-valid, the following becomes the canonical historical score reported for the deployed clean model:

`CHALLENGER CONSENSUS MEDIAN FOLD MEAN DAILY IC`

The output must also preserve Control, H5, H10, q25, positive-fold counts, bootstrap CIs, and Challenger-Control paired deltas.

The old pre-clean metric remains visible only as a parent benchmark and must not be averaged with the clean result.

## Scientific interpretation boundary

This is explicitly a **post-selection diagnostic/robustness measurement**. It is not a new independent model-selection set.

Therefore the result may update the displayed/reported historical benchmark, but it may not:

- retune or replace the deployed model;
- change features, learner, folds, purge, CA80, universe, target, or session semantics;
- trigger a historical rescue;
- mutate the prospective counter;
- authorize outcome-vault access;
- mix V4-X2 semantics.

The fresh 100-session prospective run remains the primary post-freeze validation.

## Frozen implementation

- runner: `scripts/run_v4_x1_clean_historical_oos_replay.py`
- runner blob: `273ec17f8d2da0d23ac5d2e9f08661b6ff6a35d7`
- config: `config/ranking_v4_x1_clean_historical_oos_replay_v1.json`
- config blob: `583fe1791e0f2534032a41713e56a18f6d968e80`
- one-shot launcher: `scripts/run_v4_x1_clean_historical_oos_one_shot.ps1`
- launcher blob: `61ff3424dbf51c26d8dd190653bd9dfe9945f953`

The launcher resolves accepted external bytes by SHA and refuses an existing output directory, making the local measurement exactly-once/fail-closed.

## Next

`RUN_EXACTLY_ONCE_LOCALLY; RETURN MANIFEST_AND_CLEAN_IC; INDEPENDENT_REVIEW; NO_RETUNE`
