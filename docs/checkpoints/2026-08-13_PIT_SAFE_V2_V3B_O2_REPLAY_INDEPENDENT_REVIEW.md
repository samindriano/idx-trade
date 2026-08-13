# PIT-Safe V2/V3-B/O2 Replay — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `codex/pit-safe-v2-v3b-o2-reproduction-research-v1`
Reviewed HEAD: `944d72966ad28b21eef23872762007b69294ee3d`

Status: **`PIT_SAFE_REPLAY_PARTIAL_ACCEPTANCE_REMEDIATION_REQUIRED`**

## Decision

The corrected historical reconstruction and the V2/V3-B replay are substantively accepted, with one required cross-stage equivalence verification before final closure. The reported O2 `O2_SURVIVOR` result is **not accepted as the clean-ladder successor decision** because the clean replay first rejects its frozen parent architecture V3-B and retains V2.

No model promotion, canonical overwrite, forward-counter transition, or protected-outcome access is authorized by this review.

## Accepted findings

1. The fast-H10 label blocker was correctly resolved as an artifact-selection/path issue rather than missing historical labels. The replay contract pins the exact full-panel-equivalent H10 artifact and corrected tables.
2. Corrected V2/V3-B populations are 292,631 rows / 737 tickers and corrected O2 common support is 278,166 rows / 729 tickers.
3. V2 replay reselects `HGB_XS_MARKET` under the frozen five-model candidate set and original deterministic selection rule. This is accepted as a clean historical-development result.
4. V3-B Structure-Lite fails the exact late F5/F6 paired gate on the corrected lineage and the frozen decision is `V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`. The negative V2F5 paired PR/Q5 changes are sufficient to fail the preregistered gate. No rescue or retuning is authorized.
5. The old V2/V3-B/O2 models remain immutable `LEGACY_CONTAMINATED_REFERENCE`; the corrected inputs remain a sibling PIT-safe reconstruction lineage.

## Blocking finding 1 — O2 is orphaned by the clean V3-B failure

The original O2 experiment is explicitly defined as:

- baseline: `V3B_COMMON_SUPPORT_BASELINE`;
- challenger: `O2_OPEN_GEOMETRY`;
- challenger features: the full 33-feature V3-B architecture plus `open_position`, `open_to_high`, and `open_to_low`.

The corrected replay now determines that the 33-feature V3-B architecture does not survive and the final clean historical architecture reverts to `HGB_XS_MARKET` (V2).

Therefore the clean replay cannot propagate `O2_SURVIVOR` as if O2 remained the next valid ladder stage. The O2 result only establishes the descriptive statement:

> On corrected common-support rows, adding the three Open-geometry features improved the now-nonselected 33-feature V3-B baseline under the old O2 survivor rule.

That is useful historical diagnostic evidence, but it does not establish that a clean successor to V2 survives.

Required disposition:

- reclassify the replayed O2 result as **diagnostic-only / orphaned-parent evidence**;
- do not create a clean O2 model identity from this result;
- do not inherit or start a prospective counter from it;
- if Open geometry is to be tested on the new clean lineage, preregister a separate candidate whose baseline is the clean selected V2 architecture and whose feature contract is defined before results are inspected.

No such new experiment is authorized by this review.

## Blocking finding 2 — cross-stage V2-control equivalence is not asserted

The original final V3-B confirmation explicitly proved exact control equivalence against frozen V2 predictions/metrics before interpreting challenger deltas. The replay runner independently refits `HGB_XS_MARKET` in the V2 stage and again as the V3-B baseline, but the current runner does not assert score/metric equality between those two fitted control paths.

Because both paths use the same corrected rows, feature prefix, model constructor, folds, and deterministic random seed, equality is expected; however, expected equality is not the same as recorded evidence.

Required remediation:

- add a read-only cross-stage verifier over the existing replay artifacts;
- require exact row identity/order and score equivalence for `HGB_XS_MARKET` between V2 and the V3-B baseline, at minimum on F5/F6 and preferably all six folds;
- persist maximum score/metric difference and fail closed on mismatch;
- this verification should not require model refitting if the existing artifact predictions are sufficient.

Until this is recorded, V3-B failure is substantively credible but not yet fully closed under the same integrity standard as the original V3 review.

## Engineering note — strict boolean parsing

`pit_safe_replay._read_table()` currently checks `universe_primary_liquid` using `.astype(bool)`. This is the same generic fail-open pattern identified by the repository-wide scientific-integrity audit for textual booleans. The exact replay input files are hard SHA-pinned, so this is not evidence that the completed replay was contaminated. Nevertheless, this runner must not become a reusable/canonical readiness gate with generic `.astype(bool)` semantics.

Use strict accepted boolean parsing in the remediation or in the future executable data-readiness gate.

## Minor documentation issue

The final branch HEAD is `944d72966ad28b21eef23872762007b69294ee3d`, while the handoff currently records `head_commit: ab56f46569b398c529658b6b63d443cca89d0434`. Update the handoff during remediation.

## Scientific state after review

- Clean historical V2: **accepted champion `HGB_XS_MARKET`**, subject only to final artifact/equivalence closure.
- Clean historical V3-B: **fails / retain V2**; no rescue.
- Replayed O2: **diagnostic-only because its V3-B parent is no longer selected**; not a clean-ladder survivor.
- Existing old O2 prospective archive: preserve as immutable legacy evidence. It cannot validate or donate its counter to any future PIT-safe model.
- Canonical fresh-forward raw EOD capture should continue independently of this model-lineage decision.

## Required next action

Perform a narrow remediation/review pass only:

1. verify V2 `HGB_XS_MARKET` versus V3-B baseline prediction/metric equivalence from existing replay artifacts;
2. reclassify O2 output as orphaned-parent diagnostic evidence;
3. add conditional ladder semantics so a failed upstream architecture cannot automatically propagate a downstream successor verdict;
4. replace generic boolean coercion in the replay input validation with strict parsing;
5. correct the handoff HEAD and update documentation/status;
6. run focused/full tests and `git diff --check`;
7. stop for final independent review.

Do **not** refit models, tune V3-B, run a V2+Open challenger, touch the forward counter, overwrite old artifacts, or access protected outcomes in this remediation.
