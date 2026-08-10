# Ranking V3 Recency Specification — Independent Review Addendum V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **INDEPENDENT REVIEW PASS WITH PRE-OUTCOME CORRECTIONS**

This addendum reviews and clarifies the frozen `docs/RANKING_V3_RECENCY_SPEC_V1.md` before any V3 fitting or scoring. The original specification remains immutable evidence of the pre-review draft. For the first V3-A outcome-bearing run, this addendum is controlling wherever it conflicts with the original specification.

Original frozen specification identity:

- path: `docs/RANKING_V3_RECENCY_SPEC_V1.md`;
- reported SHA-256: `53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa`;
- Git blob: `b6e055ad4fe5e964e29892ef2bd0d9b8a4921c83`.

The review did not inspect or use any V3 recency outcome, any reserved Ranking-V2 post-2026-07-31 forward outcome, or any new model score. These corrections are therefore outcome-blind.

## 1. Review conclusion

The core V3-A design is accepted:

- exact frozen V2 `HGB_XS_MARKET` control;
- exact 25-feature order and H10 semantics;
- only fit-row recency weights may change;
- exactly two variants, half-life 252 and 504 official sessions;
- `raw_weight = 2 ** (-age / H)` with `age = train_end - signal_session_index`;
- fold-local normalization to mean weight 1.0;
- discovery on V2F1-V2F4;
- fixed robustness-first paired gates;
- permanent hypothesis ledger and cumulative candidate denominator;
- no access to reserved V2 fresh-forward outcomes.

The half-lives and normalization are reasonable bounded perturbations. They are accepted without search or tuning.

## 2. Correction A — V2F5/V2F6 remain sealed for the whole V3 generation

The original recency spec proposed a one-time late-development confirmation of the recency winner on V2F5/V2F6. **Do not do this.**

The controlling V3 roadmap intentionally reserves V2F5/V2F6 from repeated V3 hypothesis iteration so they can be used once, later, for the final V3 architecture after the bounded hypothesis ladder and at most one preregistered integration experiment are complete.

Therefore for `V3-A-RECENCY-V1`:

- authorized outcome-bearing folds are **V2F1-V2F4 only**;
- V2F5/V2F6 must not be loaded, scored, summarized, or used to promote/kill/tie-break the recency variants;
- no artifact for V3-A may contain V2F5/V2F6 candidate metrics;
- V2F5/V2F6 remain sealed late-development confirmation folds for the future final V3 architecture;
- if they are accidentally scored for a V3 candidate, record them as consumed and do not later call them a one-shot final-V3 confirmation.

This correction preserves the research value of the two latest historical folds and prevents each V3 hypothesis from adapting to the same late-development evidence.

## 3. Correction B — Recency promotion is discovery-only

Because V2F5/V2F6 remain sealed, remove the original late-confirmation promotion gate from V3-A.

A recency variant receives `PROMOTE_FOR_NEXT_RESEARCH_STEP` if and only if, on V2F1-V2F4:

1. all data/provenance/equivalence gates pass;
2. it passes the original discovery absolute sanity gate;
3. it passes the original discovery paired promotion gate versus the exact V2 control.

If both H=252 and H=504 pass, use the original deterministic discovery tie rule:

1. larger discovery median paired PR-AUC-delta improvement;
2. larger discovery q25 paired PR-AUC-delta improvement;
3. larger discovery worst-fold paired PR-AUC-delta improvement;
4. larger discovery median paired Q5-Q1 improvement;
5. simpler perturbation: H=504 before H=252;
6. lower candidate ordinal.

Only **one** recency component may be carried forward as the surviving V3-A component. Passing V3-A is development evidence, not final V3 validation.

If neither recency variant passes, close the hypothesis as `V3_A_RECENCY_KILL_KEEP_V2_CONTROL` and proceed to the next independently specified V3 hypothesis without rescue tuning.

## 4. Correction C — mandatory exact-control equivalence gate

Before any recency variant result may be considered valid, the new runner must prove that the uniform control reproduces the frozen V2 HGB_XS_MARKET semantics on V2F1-V2F4.

The implementation must compare the new control output against the existing frozen V2 candidate artifacts for those exact folds, including at minimum:

- eligible row identity/order;
- fold boundaries;
- prediction/ranking score for each row under the same numeric tolerance used by the existing research equivalence contract;
- prevalence;
- PR-AUC and `PR-AUC - prevalence`;
- ROC-AUC;
- Q1 and Q5 TP rates;
- Q5-Q1 TP-rate spread;
- top-decile TP rate and lift.

Prefer direct comparison to the immutable existing V2 metrics/score artifacts rather than retyping expected values into new code. Pin and record their hashes.

If the control fails equivalence, the entire V3-A run fails closed. Do not inspect, promote, or interpret recency-variant metrics as research evidence until the control path is fixed and a new explicitly documented engineering run is authorized. Do not weaken tolerances to obtain a pass.

## 5. Correction D — ROC wording

The original late-confirmation clause said median ROC-AUC must be "positive". ROC-AUC positivity is not a meaningful gate; the intended absolute sanity threshold is `ROC-AUC > 0.50`.

Because the V3-A late-confirmation gate is removed by this addendum, this wording is not active for the recency run. Any future final-V3 confirmation specification that uses an absolute ROC gate must write it explicitly as `> 0.50`, not merely `> 0`.

## 6. Correction E — terminology typo

Where the original recency spec says "the V4 discovery fold behavior explicitly", read this as:

`V3D4 = V2F4 discovery-fold behavior explicitly`.

It is not a reference to the legacy Model V4 path-risk experiment.

## 7. Weight implementation clarification

The mathematical normalization has mean weight 1.0. Runtime verification should use float64 and a strict numerical tolerance (for example `abs(mean_weight - 1.0) <= 1e-12`) rather than require impossible bitwise decimal exactness.

The weight formula remains unchanged. No date-level reweighting, class weighting, clipping, minimum weight, maximum weight, resampling, or effective-sample-size adjustment may be introduced under this hypothesis.

## 8. First authorized V3-A run boundary

After this review addendum and its checkpoint/handoff are pulled locally, a separate implementation/run task may be authorized to:

- implement deterministic recency weighting and its tests;
- run the exact V2 control on V2F1-V2F4 and prove equivalence;
- if equivalence passes, run H=252 and H=504 on V2F1-V2F4;
- compute only the frozen discovery metrics/gates;
- update the hypothesis ledger for ordinals 001-003;
- produce immutable manifests, hashes, profiling, checkpoint, result handoff, and continuity update;
- stop for independent review.

That task is **not** authorized to:

- score V2F5/V2F6;
- inspect any reserved post-2026-07-31 V2 forward outcome;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- change features, label, universe, HGB parameters, half-lives, normalization, gates, or tie rules;
- run Structure-Lite, Regime, Sector, True-Ranking, integration, Stage 6, calibration, execution-PnL, paper/live, or merge to main.

## 9. Effective reviewed specification identity

For the first V3-A run, the research contract is the ordered pair:

1. `docs/RANKING_V3_RECENCY_SPEC_V1.md` at the frozen identity above; and
2. this independent review addendum.

The run manifest must pin both artifacts and their Git/blob/SHA identities. No future edit to either artifact may silently alter an already-authorized run.
