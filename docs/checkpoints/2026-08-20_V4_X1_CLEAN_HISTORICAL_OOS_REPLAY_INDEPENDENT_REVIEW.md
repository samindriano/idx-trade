# V4-X1 Clean Historical OOS Replay — Independent Review

Date: 2026-08-20
Reviewer: ChatGPT independent review
Execution branch: `research/idx-v4-x1-clean-historical-oos-replay-v1`
Execution HEAD: `9a421c0c4d8935c59b69689e8860230bdf524131`

## Verdict

`V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_ACCEPTED_WITH_PROVENANCE_NOTE`

The remediated clean historical OOS replay is accepted as valid historical measurement evidence for the deployed clean V4-X1 representation. It does not authorize retuning, feature changes, model replacement, reopening model selection, or any mutation of the prospective 100-session forward counter.

The canonical user-facing historical rank metric is the common-support Spearman result below. The frozen evaluator headline remains recorded as a separate evaluator statistic and must not be conflated with common-support Spearman.

## Accepted execution identity

- Execution commit: `9a421c0c4d8935c59b69689e8860230bdf524131`
- Runner blob used by remediation config: `4e6f3097ce8d6a3ad6899de4bcec7b38bb9abd62`
- Remediation config: `config/ranking_v4_x1_clean_historical_oos_replay_v2_execution_remediation.json`
- Remediation config blob: `9bd9ca76adf62a3bc583107ffc2ec8636731a844`
- Frozen fold contract: `EXACT_FROZEN_V4_3R_6X100_PURGE10`
- Validation fold SHA256: `91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`
- Frozen validation end: session `1249`, `2026-07-17`
- Required / actual fit count: `24 / 24`

The execution-remediation commit changed the evaluator preregistration wiring from the CA80 wrapper JSON to the inherited full V4-3 preregistration JSON. This matches the parent historical runner's intended gate configuration and does not change the CA80 evaluator, model family, features, targets, folds, purge, hyperparameters, universe, or session semantics.

## Runtime result evidence

The local remediated replay completed with:

- Status: `V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_COMPLETE_REVIEW_REQUIRED`
- Result root: `D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2`
- Manifest SHA256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- Fit count: `24`
- Clean frozen-evaluator headline IC: `0.09805414600339561`
- Parent pre-clean frozen-evaluator headline IC: `0.09775243938276076`
- Frozen-evaluator absolute delta: `+0.0003017066206348479`
- Frozen-evaluator relative delta: `+0.30864357200690584%`
- Clean control consensus IC: `0.08461269505069338`

Safety outputs were all preserved:

- `forward_counter_mutated = false`
- `deployed_model_mutated = false`
- `protected_forward_accessed = false`
- provider/network access remained false by contract and result manifest

The first failed output generation remains historical evidence and must not be overwritten. The accepted result is the distinct `v2` output generation above.

## Apple-to-apple common-support Spearman

A separate read-only re-derivation was run on the accepted clean `v2` score and target artifacts using the same common-support methodology as the prior consumed-result consistency audit: restrict each date to the identical observable target support, re-rank both alpha and target on that common support, then compute Pearson correlation of the re-ranked variables (Spearman).

Accepted result:

- Pre-clean common-support Spearman: `0.09545975125676774`
- Clean common-support Spearman: `0.097554036`
- Absolute delta: `+0.002094285`
- Relative delta: `+2.19%`
- Admitted dates: `600 / 600`

Therefore the canonical historical Spearman benchmark for the clean deployed V4-X1 representation is:

`0.097554036`

For display/rounding, `0.0976` is acceptable. The pre-clean `0.0954597513` remains a lineage benchmark and must not be deleted or silently replaced.

## Metric nomenclature

Three different numbers must remain separated:

1. `0.097554036` — canonical common-support Spearman for user-facing historical rank performance.
2. `0.09805414600339561` — frozen evaluator `CHALLENGER_CONSENSUS_MEDIAN_FOLD_MEAN_DAILY_IC` headline.
3. `0.099248615` — mean frozen-formula IC across the 600 admitted clean dates from the read-only comparison calculation.

The frozen evaluator computes correlation after full-universe alpha percentile normalization and then applies observable target support. The common-support Spearman audit re-ranks both variables after restriction to the same observable names. They are related rank metrics but not interchangeable aggregates.

## Provenance note

The accepted runner writes the manifest field `git.config_blob` using a hard-coded reference to:

`HEAD:config/ranking_v4_x1_clean_historical_oos_replay_v1.json`

while this accepted execution was explicitly invoked with:

`config/ranking_v4_x1_clean_historical_oos_replay_v2_execution_remediation.json`

This is a provenance metadata defect in the emitted manifest. It does **not** alter the executed model/evaluator result because `verify_contract()` consumes the supplied `--config` path, and the remediation config is scientifically identical to v1 except for remediation status and the updated runner blob. The exact executed remediation config is pinned above by Git blob `9bd9ca76adf62a3bc583107ffc2ec8636731a844`.

No historical replay rerun is authorized or required solely to rewrite this metadata. Any future reuse of this runner should record the actual supplied config path/blob rather than the hard-coded v1 config reference.

## Scientific interpretation

The clean representation preserves historical alpha and shows a modest positive historical rank-performance shift on the common-support metric (`+0.002094285`, `+2.19%`). This should be described as historical preservation with a positive shift, not as causal proof that data cleaning created new alpha.

The result does not reopen model selection and is not permission to retune. The prospective 100-session validation remains the primary fresh evidence for the deployed model.

## Final state / next action

Historical clean replay lane: `DONE` after this acceptance checkpoint is recorded.

Next authorized research action:

`CONTINUE_PROSPECTIVE_100_SESSION_ACCUMULATION_ONLY; DO_NOT_RETUNE; DO_NOT_REOPEN_HISTORICAL_MODEL_SELECTION; KEEP_FORWARD_OUTCOMES_LOCKED_PER_EXISTING_CONTRACT.`
