# V4-X1 Clean Remediation — Corporate-Action Disposition Acceptance

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x-clean-replay-refit-contract-v1`
Status: `V4_X1_CLEAN_CA_DISPOSITION_ACCEPTED_REUSE_PARENT_CA80_RECOMPUTE_ON_CLEAN_INPUT`

## Decision

No new Corporate Action acquisition/remediation campaign is required as a prerequisite to the clean V4-X1 structural replay.

The applicable Corporate Action contract for V4-X1 is the already-frozen **V4-3R CA80** lineage, not the original V4-3 >=90% generation.

The original V4-3 >=90% result remains historically failed/closed and is not retroactively waived. It is also not the support threshold used by the existing V4-X1 final training lineage.

For clean V4-X1 remediation:

1. preserve the V4-3R CA80 date-level support threshold at `0.80`;
2. preserve row-level fail-closed semantics for known/unresolved mechanical CA crossings and missing CA evidence;
3. preserve the same target definitions, decision-universe rule, folds, purge, features, learner, preprocessing, and hyperparameters;
4. reuse the accepted parent CA evidence/semantics lineage without new provider calls or semantic relaxation;
5. during clean Phase A, recompute state/support identities deterministically against the accepted clean panel/security-master bundle under the same CA80 contract;
6. if the clean replay no longer satisfies the frozen CA80 support requirements, stop fail-closed for independent review before any model fit. Do not lower the threshold, change CA semantics, or rescue support in-place.

## Why the prior ~88% / 90% observation is not a clean-refit blocker

The outcome-blind V4-3R preregistration explicitly created a new generation with the date-level support/evaluation threshold changed from `0.90` to `0.80` before historical target/model/performance access.

Its subsequent prefit support replay passed:

- H5 eligible sessions: `986`
- H10 eligible sessions: `982`
- consensus eligible sessions: `982`
- frozen 600 full-target eligible: `true`
- minimum frozen H5 support: `0.8432203389830508`
- minimum frozen H10/consensus support: `0.8395061728395061`
- all 12 fold/head training sets non-empty: `true`

The prefit checkpoint explicitly records that `541/600` frozen dates lie in `[0.80, 0.90)`. Therefore requiring clean V4-X1 to clear the old `0.90` V4-3 threshold would silently change its scientific parent rather than remediate the existing V4-X1 generation.

## Parent pins

V4-3R CA80 preregistration:

- path: `config/ranking_v4_3r_ca80_preregistration_v1.json`
- Git blob SHA-1: `bbdbd28dc642f9af78fdce1e3a164ac8631eb376`
- generation: `V4_3R_CA80`

Outcome-blind CA80 prefit result:

- status: `V4_3R_CA80_PREFIT_SUPPORT_PASS_READY_TO_FREEZE_EXECUTION`
- manifest SHA-256: `0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc`

Parent outcome-blind combined CA replay:

- manifest SHA-256: `12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`

Existing V4-X1 final-refit contract confirms:

- final training policy: `ALL_CA80_HEAD_ELIGIBLE_DATES_THROUGH_FROZEN_V4_3R_END`
- exact fit count: four models
- historical performance recomputation: forbidden

## Relationship to older CA closure work

Earlier V4 CA work did produce a separate 600/600 >=90% continuity certification for the then-frozen 611-ticker/material-six scope. That result is valid for its own scope but does not replace the later exact V4-3R CA80 training-domain lineage used by V4-X1.

Likewise, later V4-3R diagnostics explicitly preserved unresolved CA rows fail-closed rather than pretending full market-wide CA completeness.

Therefore the clean-remediation objective is **contract-preserving replay**, not proving universal corporate-action completeness or reopening old provider work.

## Clean-input correction boundary

The accepted HLC/Open and FINN/FREN identity corrections may change feature representation and possibly state/support identities. They do not authorize changing CA semantics.

Phase A must report any old-vs-clean support delta. A delta is admissible only when deterministically explained by the accepted clean input lineage under the unchanged CA80 rules.

No model fit, historical prediction, historical performance recomputation, provider call, protected/fresh-forward outcome access, or forward-counter mutation is authorized by this disposition.

## Final disposition

`ACCEPTED_NO_NEW_CA_ACQUISITION_REQUIRED_BEFORE_PHASE_A`

The Corporate Action dependency for the clean replay/refit contract is satisfied by reusing the frozen V4-3R CA80 contract/evidence and recomputing support on the clean input. The remaining prerequisite before Phase A is the independently accepted/hash-pinned final clean-data bundle and a separate execution lock.
