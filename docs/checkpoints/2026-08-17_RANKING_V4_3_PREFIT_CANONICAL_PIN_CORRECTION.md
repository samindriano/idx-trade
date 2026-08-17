# Ranking V4-3 prefit — canonical preregistration pin correction

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3-prefit-runtime-v1`
Status: `V4_3_PREFIT_CANONICAL_PIN_CORRECTED_NO_OUTCOME_ACCESS`

## Finding

The preregistration scientific config has not changed since the locked V4-3 preregistration.

Exact Git blob identity for `config/ranking_v4_3_preregistration.json` is the same at the original preregistration commit `8dbde070b18edf432348062e5a9218f6ef2665f9` and the blocked retry lineage: Git blob SHA-1 `57cc72ee68a9484b6bfe3843da17caadd5373908`.

The canonical tracked bytes hash to SHA-256:

`3a54dcf0266f8a2808b8c1d73dda41a32baea368e6b48aac21e9fa073f6824ed`.

The previously pinned value:

`835da85549b1d6874cb2ab49a029b9f4358fdf28cb8379b3f9df105835b05849`

was copied from the earlier support-run manifest, whose runner hashed the local checkout path. It is therefore preserved as historical support-run provenance but is not the canonical Git-byte identity of the preregistration config.

## Correction

Only the prefit runtime protocol provenance pin was corrected from `835da855...` to canonical `3a54dcf...`.

No field in `config/ranking_v4_3_preregistration.json` was edited. No V4-0/V4-1/V4-2/V4-3 scientific choice, target definition, universe rule, fold identity, learner, feature set, preprocessing rule, metric, threshold, or promotion gate changed.

This correction is allowed before first target/performance access because it repairs a provenance identifier rather than a scientific degree of freedom.

## Outcome boundary

Both blocked attempts stopped before environment capture and before any V4 target/model execution. No R5/R10, target rank, model fit, prediction, IC, Top-30 metric, raw-return performance, provider call, protected outcome, or fresh-forward outcome was accessed.

## Retry authorization

The exact same outcome-blind prefit environment capture may be retried against the corrected protocol. If any other required canonical artifact hash, estimator parameter, imputer parameter, worktree cleanliness check, or runtime check fails, stop fail-closed again.

Target materialization and model fitting remain unauthorized after environment capture until exact execution code and pathwise corporate-action continuity handling are separately frozen and reviewed.

Verdict:

`V4_3_PREFIT_CANONICAL_PIN_CORRECTED_NO_OUTCOME_ACCESS`
