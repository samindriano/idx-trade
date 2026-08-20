# V4-X1 Clean Phase-A Open-Lineage Remediation — Independent Acceptance

Date: 2026-08-20 (Asia/Jakarta)
Branch: `research/idx-v4-x1-clean-phase-a-open-lineage-remediation-v1`

## Decision

`V4_X1_CLEAN_PHASE_A_REMEDIATION_ACCEPTED_PHASE_B_PREPARATION_AUTHORIZED_REFIT_NOT_RUN`

The one-shot remediated Phase-A structural replay is accepted for scientific continuation. The first Phase-A replay remains immutable forensic evidence of an implementation-lineage failure and is not interpreted as a scientific CA80 failure.

This acceptance authorizes preparation/freeze of a separate Phase-B clean four-model refit contract only. It does **not** itself execute or authorize an unreviewed model refit, scoring, historical performance inspection, protected/fresh-forward outcome access, or forward-counter mutation.

## Accepted runtime evidence

Final remediated runtime status:

`V4_X1_CLEAN_PHASE_A_STRUCTURAL_REPLAY_COMPLETE_INDEPENDENT_REVIEW_REQUIRED`

Authoritative final runtime manifest:

`D:\Documents\Project\idx-v4-x1-clean-phase-a-open-lineage-remediation-20260820-v1\MANIFEST.json`

SHA-256:

`f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`

The parent runner initially emitted manifest SHA `32cc12b5027edecf43fbb0bf544e96fa5691aab2307c2f15eceee3cb7e129153` before the remediation wrapper appended frozen remediation metadata. The wrapper then rewrote the final authoritative manifest to the SHA above. This is expected behavior of the frozen wrapper and is not a second scientific replay.

First failed Phase-A forensic manifest remains:

`1dedb76db7c1fc620e4feb286e409d0266bf367581cbf7dab28bc862f298787c`

Open-lineage policy:

`PRESERVE_PARENT_EXECUTABLE_OPEN_EXCEPT_ACCEPTED_STAGE_A_CANDIDATES_V1`

## Open-lineage invariants — PASS

- candidate rows: `1,657`
- admitted clean Open rows: `1,655`
- fail-closed unavailable rows: `2`
- non-candidate rows: `980,283`
- parent non-candidate Open admitted: `938,666`
- clean non-candidate Open admitted: `938,666`
- `non_candidate_open_value_exact_parity=true`
- `non_candidate_open_admission_exact_parity=true`
- `market_state_reused_exactly_from_parent_executable_evidence=true`
- parent state conflicts: `0`
- final Open admitted: `940,321`
- clean Close admitted: `981,940`

These invariants resolve the first replay's implementation error: Stage-A `panel.open` is not a complete executable-Open evidence layer. Parent executable-Open semantics are now preserved exactly outside the frozen Stage-A candidate population.

## CA80 / frozen-tail gate — PASS

Inherited gate remains exactly `0.80`.

Frozen checks:

- `all_frozen_600_full_target_eligible=true`
- `tail_600_identity_unchanged=true`
- `eligible_sessions_after_frozen_end=0`
- minimum H5 support rate: `0.8396624472573839`
- minimum H10 support rate: `0.8360655737704918`
- minimum consensus support rate: `0.8360655737704918`

Therefore the clean replay remains above inherited CA80 without threshold relaxation or semantic rescue.

## Support deltas

### H5

- old support rows: `241,487`
- clean support rows: `239,648`
- shared rows: `239,648`
- added rows: `0`
- dropped rows: `1,839`
- dropped dates: `8`
- dropped tickers: `278`

### H10

- old support rows: `239,836`
- clean support rows: `237,976`
- shared rows: `237,976`
- added rows: `0`
- dropped rows: `1,860`
- dropped dates: `8`
- dropped tickers: `280`

The scale is consistent with the bounded accepted clean-data corrections and is materially different from the invalid first-run drop of more than 122k support rows.

## Primary representation / feature structure

- old primary rows: `347,829`
- clean primary rows: `348,762`
- shared primary rows: `347,829`
- primary additions: `933`
- primary drops: `0`
- features with at least one exact finite-value change: `27 / 28`

Aggregate missingness transitions across the 28 features:

- finite -> missing: `0`
- missing -> finite: `0`
- both missing: `72,502`

The 27/28 finite-value changes are accepted as structural propagation from the already accepted clean price/identity corrections under unchanged feature definitions. No new missingness transition was introduced.

## Clean training-date counts — all non-empty

- F1 H5: `368`
- F1 H10: `364`
- F2 H5: `468`
- F2 H10: `464`
- F3 H5: `568`
- F3 H10: `564`
- F4 H5: `668`
- F4 H10: `664`
- F5 H5: `768`
- F5 H10: `764`
- F6 H5: `868`
- F6 H10: `864`

All 12 fold/head training-date sets remain non-empty.

## Safety / outcome-blindness — PASS

All reported false:

- provider calls
- network calls
- numeric target values accessed
- target returns accessed
- target ranks accessed
- model fit
- model scoring
- historical predictions accessed
- historical performance accessed
- protected forward accessed
- fresh forward accessed
- counter mutation
- data mutation
- Phase-B refit authorization inside the Phase-A runtime

No model result or protected outcome was exposed during Phase A.

## Independent-review interpretation

The first CA80 fail was caused by an implementation mismatch between parent executable-Open evidence and incomplete Stage-A panel Open semantics. The separately frozen remediation changed only that lineage mapping and preserved the original first-run evidence. After remediation, the inherited CA80 gate passes with exact non-candidate Open parity and bounded support deltas.

Phase A is therefore accepted as decision-valid.

## Next boundary

Authorized next action:

1. prepare a separate Phase-B clean final-refit execution contract;
2. pin this acceptance checkpoint and final manifest SHA;
3. preserve the existing V4-X1 scientific contract: exactly four clean final fits, unchanged target/universe/folds/features/HGBR hyperparameters, inherited CA80 and observed-bar session semantics;
4. freeze runtime/input/code identities before execution;
5. stop for review before any model refit if the Phase-B preparation changes scientific semantics.

Still prohibited until separately frozen Phase-B execution authorization:

- model refit/scoring;
- historical performance inspection;
- protected/fresh-forward outcome access;
- forward counter reset/mutation;
- V4-X2 session-aligned semantics;
- CA80 threshold change;
- new data/provider acquisition or semantic rescue.
