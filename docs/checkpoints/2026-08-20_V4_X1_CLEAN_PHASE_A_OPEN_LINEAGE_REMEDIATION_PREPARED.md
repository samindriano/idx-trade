# V4-X1 Clean Phase-A Open-Lineage Remediation V1 — Prepared

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x1-clean-phase-a-open-lineage-remediation-v1`
Status: `V4_X1_CLEAN_PHASE_A_OPEN_LINEAGE_REMEDIATION_FROZEN_NOT_RUN`

## Independent review of first Phase-A result

The first authorized Phase-A replay remains immutable forensic evidence:

- status: `V4_X1_CLEAN_PHASE_A_CA80_SUPPORT_FAIL_REVIEW_REQUIRED`
- manifest SHA-256: `1dedb76db7c1fc620e4feb286e409d0266bf367581cbf7dab28bc862f298787c`
- old-support oracle exact match: PASS
- clean CA80 reported FAIL

That CA80 failure is **not accepted as a scientific clean-data verdict** because the first runner mixed two different Open evidence semantics:

1. old lineage: parent executable Open from the frozen derivative + recovery-overlay evidence layer;
2. clean lineage: direct `clean_panel.open` for the full panel.

Stage-A consolidation never claimed that `clean_panel.open` materialized the complete executable-Open evidence layer. It changed only the accepted Open-remediation candidate population and explicitly did not fill other missing Open.

The observed first-run support collapse (~123k H5/H10 row drops and 13.3% frozen minimum support) is therefore treated as an implementation diagnostic, not evidence that clean CA80 truly fails.

## Frozen remediation policy

Policy:

`PRESERVE_PARENT_EXECUTABLE_OPEN_EXCEPT_ACCEPTED_STAGE_A_CANDIDATES_V1`

Exact behavior:

- start from the already-frozen parent executable-Open evidence for all panel identities;
- outside Stage-A Open candidates, preserve **both accepted Open value and admission boolean exactly**;
- candidate identity is `open_repaired OR open_fail_closed_candidate` from the accepted field-provenance sidecar;
- candidate identity must exactly equal `hlc_repaired` identity;
- candidate population is frozen at `1,657` rows;
- `1,655` admitted candidates use the clean panel Open accepted by Stage A;
- `2` unsupported candidates remain `NaN` / not admitted;
- accepted candidate sources remain only `IDX_OFFICIAL_OPENPRICE` or `CA_FACTOR_RECONSTRUCTION`;
- fail-closed source remains `FAIL_CLOSED_UNAVAILABLE`;
- market-state semantics are copied exactly from parent executable evidence;
- Close/HLC continues to come from the accepted clean panel;
- final security master remains the accepted FINN+FREN reconciled master.

No CA gate, CA semantics, folds, primary-liquidity rule, observed-bar session semantics, feature definitions, learner, or hyperparameters change.

## Immutable parent evidence

The original Phase-A runner is intentionally unchanged:

- `scripts/run_v4_x1_clean_phase_a_structural_replay.py`
- blob: `352e331439dd89c8d66d6b36f98997d3b667e2c0`

The original Phase-A config is unchanged:

- `config/ranking_v4_x1_clean_phase_a_structural_replay_v1.json`
- blob: `c1dc1706b2dfc0c68b925988a03f1cbca83070c9`

## Remediation implementation

Wrapper:

- `scripts/run_v4_x1_clean_phase_a_open_lineage_remediation.py`
- blob: `91ecfd719c04fbd2749d2e1cf0d0f3bc0c2bec9a`

Focused tests:

- `tests/test_v4_x1_clean_phase_a_open_lineage_remediation.py`
- blob: `23268a37c5154895e1ed5a11ac15bb17131697f4`

Machine-readable contract:

- `config/ranking_v4_x1_clean_phase_a_open_lineage_remediation_v1.json`

The wrapper monkey-patches only the clean Open-evidence constructor at runtime while leaving the frozen parent Phase-A orchestration and all scientific components intact. The output manifest is annotated with the remediation policy, wrapper blob, and first failed manifest SHA.

## Frozen inputs

- field provenance: `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`
- clean panel: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- clean security master: `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`
- clean bundle: `561b1d72168debae319829faa549cb9b6fab662d989c5e7ab8b6b64f9bd01358`

All other old-reference, Stage-C, CA80, validation-fold, and execution-lock hashes remain inherited unchanged from the frozen parent Phase-A config.

## Hard guards

Still prohibited:

- provider/network calls;
- numeric H5/H10 return or target-rank access;
- model fit/scoring or historical performance;
- protected/fresh-forward outcome access;
- CA/session/universe/feature/model/hyperparameter changes;
- tuning or rescue;
- forward-counter mutation;
- Phase-B refit.

## Runtime state

No remediation runtime has been executed. Local focused tests, `py_compile`, and `git diff --check` have not yet been run for this branch.

The next allowed action is exactly one local remediation replay on a **new output root**, after canonical `main:coordination/TEAM_STATUS.md` is updated to claim this remediation lane. If validation or runtime fails, stop for review; do not patch/rerun in the same execution handoff.