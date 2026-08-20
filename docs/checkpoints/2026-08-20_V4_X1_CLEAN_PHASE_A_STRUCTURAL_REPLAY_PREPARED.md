# V4-X1 Clean Phase-A Structural Replay — Prepared

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x1-clean-phase-a-structural-replay-v1`
Status: `V4_X1_CLEAN_PHASE_A_STRUCTURAL_REPLAY_PREPARED_NOT_RUN`

## Scope

Prepare one deterministic, outcome-blind structural replay of the existing V4-X1 lineage on the independently accepted clean input. This checkpoint does **not** record a replay result and does **not** authorize Phase-B model refit.

The branch was created from the exact independent execution-lock acceptance commit:

`30885d3a7c37511ef9cdedd6cb1f599f3350dea1`

Accepted local execution-lock manifest SHA-256:

`1846c94a74de8132672777c96f46580d298f942d87584e12b5e99e78e83a77f3`

## Scientific contract preserved

- V4-X1 observed-ticker-row feature-window semantics remain unchanged.
- Control = Context25; challenger representation = Context25 + frozen Geometry3.
- Geometry3 continues to use only admitted exact-session Open; unresolved Open remains NaN without fallback.
- V4-3R CA80 date-level support gate remains exactly `0.80`.
- Missing/unresolved CA continuity remains fail-closed at row level.
- Frozen validation folds, purge boundaries, historical end, and primary-liquidity rule remain unchanged.
- V4-X2/session-aligned semantics are explicitly out of scope.

## Old-reference oracle

Phase A must not read numeric targets to reconstruct the old training set. Instead it uses the exact Stage-C outcome-blind support identities as the canonical old oracle:

- Stage-C manifest: `5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`
- H5 support identities: `2c2874bde129f8cefb68af1aae01ab88203dfe74c2bc8cf4cf3e5bab61e76ede` (`241,487` rows)
- H10 support identities: `606eae2a431d0b924f7dbe574cbca493f1b857bf55aeb0d1af74db3d01c03386` (`239,836` rows)

The Phase-A runner first re-derives old support from old price/state/CA booleans only. If that re-derivation is not exactly identity-equal to the Stage-C H5/H10 oracle, the run fails closed before any clean verdict can be accepted.

## Clean inputs

- final Stage-B bundle manifest: `561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`
- Stage-A clean panel: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- final reconciled security master: `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`
- field-level provenance parquet: `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`

The clean panel's Open column is the accepted post-remediation Open. Phase A does not reuse the legacy Open derivative/overlay to define clean Open. The two fail-closed Open candidates remain unavailable.

## Corporate Action lineage

Parent combined CA replay manifest:

`12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`

Phase A attaches the frozen parent continuity evidence to old and clean decision rows under the same semantics. Missing continuity for a clean identity fails closed. Date-level eligibility is then rethresholded with the already-preregistered V4-3R CA80 rule.

The clean replay may proceed to independent review only if:

1. all frozen 600 validation dates remain H5/H10/consensus eligible under CA80;
2. frozen tail-600 identity remains unchanged;
3. eligible sessions after the frozen end remain zero;
4. all 12 fold/head training-date sets remain non-empty.

A support delta versus the old generation is allowed only as a deterministic consequence of the accepted clean input lineage. It is reported, never tuned away.

## Prepared implementation

Runner:

`scripts/run_v4_x1_clean_phase_a_structural_replay.py`

Git blob SHA-1:

`352e331439dd89c8d66d6b36f98997d3b667e2c0`

Frozen config:

`config/ranking_v4_x1_clean_phase_a_structural_replay_v1.json`

Git blob SHA-1:

`c1dc1706b2dfc0c68b925988a03f1cbca83070c9`

Focused tests:

- `tests/test_v4_x1_clean_phase_a_structural_replay.py` — blob `1c90ff14e4de589ee43b162907269f0b9bacad32`
- `tests/test_v4_x1_clean_phase_a_no_outcome_paths.py` — blob `ecddcb2a9df9d4ee0d099c1d7ba2d80e5f8ff273`

The static guard test rejects target-materialization, model-fit/scoring, evaluation, target-rank/return, and model-eval import paths in the Phase-A runner.

## Required outputs when eventually run

- `clean_h5_support_identities.csv`
- `clean_h10_support_identities.csv`
- `old_vs_clean_support_delta.csv`
- `old_vs_clean_primary_identity_delta.csv`
- `old_vs_clean_feature_delta_summary.csv`
- `old_vs_clean_missingness_transition_summary.csv`
- `clean_ca80_support_per_date.csv`
- `clean_training_date_counts.csv`
- `summary.json`
- `MANIFEST.json`

Feature delta reporting covers all frozen 28 representation fields on shared primary identities and reports exact finite-value changes plus absolute delta p50/p95/p99/max. Missingness transitions are reported separately. No performance meaning is assigned to those deltas in Phase A.

## Hard guardrails

Not authorized in Phase A:

- provider/network calls;
- numeric H5/H10 returns or target ranks;
- target materialization;
- model fit or scoring;
- historical predictions or performance;
- protected/fresh-forward outcome access;
- data, CA, universe-rule, session-semantic, feature, learner, or hyperparameter changes;
- tuning/rescue;
- V4-X2 reuse;
- forward-counter mutation;
- Phase-B refit.

## Runtime state

Preparation is complete. Focused tests / `py_compile` / `git diff --check` and the one local Phase-A runtime have **not yet been executed** for this branch.

Canonical `main:coordination/TEAM_STATUS.md` was read before preparation. Because the connector cannot safely patch one row of the large shared ledger without replacing the full file, this preparation does not claim that canonical main was updated. The local execution handoff must update/claim the exact Phase-A replay row on canonical main before runtime if no duplicate owner exists.

Next:

`LOCAL VALIDATION + ONE OUTCOME-BLIND PHASE-A STRUCTURAL REPLAY; THEN STOP FOR INDEPENDENT REVIEW.`
