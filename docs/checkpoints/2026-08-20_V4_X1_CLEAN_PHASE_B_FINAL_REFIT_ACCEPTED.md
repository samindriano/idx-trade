# V4-X1 Clean Phase-B Final Refit — Independent Acceptance

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1`  
Execution HEAD: `b3b9338d420c60dbc3853117d74d4ceb62bace19`

## Decision

`V4_X1_CLEAN_PHASE_B_FINAL_REFIT_ACCEPTED_FRESH_PROSPECTIVE_SCORE_ONLY_PREPARATION_AUTHORIZED`

The exactly-once clean Phase-B final refit is accepted as decision-valid. Exactly four models were fit under the accepted clean Phase-A representation and frozen historical target boundary. No historical/prospective scoring, historical performance recomputation, provider/network call, protected/fresh-forward outcome access, or forward-counter mutation occurred.

This acceptance authorizes preparation/freeze of the immutable fresh prospective score-only capture contract. It does not itself authorize backscoring historical/pre-freeze sessions or inspecting outcomes.

## Accepted runtime evidence

Status:

`V4_X1_CLEAN_PHASE_B_FINAL_REFIT_COMPLETE_INDEPENDENT_REVIEW_REQUIRED`

Final manifest:

`D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\MANIFEST.json`

SHA-256:

`30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`

Accepted Phase-A parent manifest SHA-256:

`f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`

Validation before execution:

- focused pytest: `29 passed`
- py_compile: PASS
- `git diff --check`: PASS
- required frozen Git blobs: PASS
- branch clean/synced after run

Canonical TEAM_STATUS execution update:

`9a90eeaa04c6cf5fa323256c1161e3651909e572`

## Exactly four accepted fits

| Mode | Head | Features | Training rows | Training dates | Model SHA-256 |
|---|---|---:|---:|---:|---|
| CONTROL | H5 | 25 | 239,648 | 978 | `f727b10c6ea72c9ca7b447977ed4fa9cd3b5b32adb81793921c425d9085665b2` |
| CONTROL | H10 | 25 | 237,976 | 974 | `737be8c47fe2d689dab09950a931c1339039ed8ae379b79f0bfd5a8c2e7605db` |
| CHALLENGER | H5 | 28 | 239,648 | 978 | `d8a73d03ff72ab82826ef4e1be5e2073f6a61a5bb01b4e4268428436dc5eb082` |
| CHALLENGER | H10 | 28 | 237,976 | 974 | `935a6f9aeaa2ca30a4016819e3848d284eb677e38153a7bd3126da0c33a9f95d` |

`fit_count=4` exactly. No hyperparameter search, fifth fit, or retry occurred.

Feature identity checks:

- CONTROL feature identity: PASS
- CHALLENGER feature identity: PASS
- H5/H10 feature lists identical within each mode: PASS
- CONTROL exact 25-feature list is the prefix of the 28-feature CHALLENGER list: PASS

## Clean support identity — exact Phase-A parity

Authoritative clean eligible-date counts consumed by Phase B:

- H5: `978`
- H10: `974`

Support identities:

- H5: `239,648` rows, exact match to accepted Phase-A support identity
- H10: `237,976` rows, exact match to accepted Phase-A support identity

The target materialization was checked against these exact Phase-A child artifacts before the models were accepted.

### Metadata clarification: stale `986/982` parent count

The frozen Phase-B config contains an `expected_head_eligible_dates` field with H5 `986` / H10 `982`. Independent review found that this field is inherited stale parent metadata and is not used by the Phase-B runner as an execution guard or training-date selector.

The actual runner loads the hash-pinned accepted Phase-A `clean_ca80_support_per_date.csv`, verifies its child hash from the accepted Phase-A manifest, and derives the clean eligible-date sets from that artifact. The resulting clean counts are H5 `978` / H10 `974`, exactly eight fewer dates per horizon, consistent with the accepted Phase-A support delta of eight dropped dates per horizon.

Therefore:

`STALE_PARENT_ELIGIBLE_DATE_METADATA_NON_DECISION_CHANGING`

This discrepancy does not authorize a rerun and does not invalidate the fitted models. The four accepted model bytes remain tied to the original execution manifest/config identity. Future documentation/config generations must use `978/974` when referring to the clean Phase-B eligible-date counts and must not reinterpret `986/982` as the clean counts.

## Frozen target boundary — PASS

The validation-fold artifact is hash-pinned and contains 600 dates / 6 folds x 100 dates. Its final row is session `1249`, date `2026-07-17`.

Runtime boundary report:

- clean primary rows before target boundary: `348,762`
- rows materialized for historical training target domain: `345,770`
- post-freeze rows excluded before target materialization: `2,992`
- frozen end session: `1249`
- frozen end date: `2026-07-17`
- `post_freeze_numeric_target_accessed=false`
- `fresh_forward_training_target_accessed=false`

The wrapper filters decision rows before calling the frozen target materializer, so post-freeze rows could not enter numeric historical label/rank construction.

## Safety — PASS

All false:

- historical prediction generation
- historical performance recomputation
- historical model scoring
- prospective model scoring
- protected forward outcome access
- fresh forward outcome access
- provider calls
- network calls
- forward counter mutation
- prospective scoring authorization inside the refit runtime

Historical numeric target values/ranks were accessed only for the frozen historical training corpus required for the four authorized final fits.

## Scientific interpretation

The final models use the accepted clean representation:

- clean price/HLC panel
- clean security master
- inherited CA80 `0.80`
- parent executable-Open evidence preserved outside the exact 1,657 accepted Stage-A candidates
- two candidate Opens remain fail-closed unavailable
- observed-bar session semantics unchanged
- existing V4 CONTROL Context25 and CHALLENGER Geometry3 feature definitions unchanged
- same HGBR learner/hyperparameters
- no V4-X2 session-alignment semantics

No historical performance was recomputed after clean refit, so the refit does not consume a new historical model-selection opportunity.

## Next boundary

Authorized next action only:

1. prepare/freeze an immutable V4-X1 clean fresh prospective score-only capture contract;
2. pin this acceptance checkpoint, final Phase-B manifest, and all four model SHA-256 values;
3. preserve the existing prospective preregistration and outcome-vault rules;
4. define the first eligible score session as the first source-certified official IDX session strictly after the successful accepted clean model freeze; do not backscore earlier sessions and do not infer an unsupported calendar date;
5. score-only capture may not access H5/H10 outcomes or historical performance;
6. forward counter begins only from accepted fresh prospective score captures under the new frozen model bytes.

Still prohibited:

- historical/backfill scoring with these new model bytes;
- scoring any session that is not strictly post-freeze and source-certified;
- outcome inspection before the prospective gate/maturity rules permit it;
- provider/data semantic rescue;
- model/hyperparameter/feature changes;
- V4-X2 session alignment in V4-X1;
- forward-counter mutation outside accepted score-only capture.
