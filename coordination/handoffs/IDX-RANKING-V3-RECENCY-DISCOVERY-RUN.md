# Handoff — IDX Ranking V3 Recency Discovery Run

Date: 2026-08-10 (Asia/Jakarta)

Status: **AUTHORIZED FOR V3-A IMPLEMENTATION + F1-F4 DISCOVERY RUN ONLY**

## Required reads

Before changing or running anything, fetch/pull remote and explicitly acknowledge reading:

1. `docs/CURRENT_STATUS.md`
2. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
3. `docs/RANKING_V3_RESEARCH_BACKLOG.md`
4. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
5. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
6. `docs/RANKING_V3_RECENCY_SPEC_V1.md`
7. `docs/RANKING_V3_RECENCY_SPEC_REVIEW_ADDENDUM_V1.md`
8. `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_SPEC_REVIEW_PASS.md`
9. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
10. frozen V2 model/validation code and immutable candidate artifacts needed for exact control equivalence

The review addendum controls wherever it conflicts with the original recency spec.

## Objective

Implement and execute exactly one bounded V3-A hypothesis:

> Does deterministic recency weighting with H=252 or H=504 official sessions improve F1-F4 temporal robustness versus the exact frozen V2 HGB_XS_MARKET control, with every other research semantic unchanged?

## Frozen candidate set

Run exactly:

- `V3-A-RECENCY-V1-CONTROL-001` — uniform weight 1.0;
- `V3-A-RECENCY-V1-HL252-002` — H=252;
- `V3-A-RECENCY-V1-HL504-003` — H=504.

No additional half-life, cap, floor, class weight, resampling, model family, feature, threshold, ensemble, seed, or search is allowed.

## Authorized folds

Outcome-bearing V3-A work is limited to:

- V2F1 / V3D1;
- V2F2 / V3D2;
- V2F3 / V3D3;
- V2F4 / V3D4.

**Do not score or summarize V2F5/V2F6.** They remain sealed for the future final V3 architecture.

## Mandatory control-equivalence gate

Implement the uniform control first and compare it to the immutable existing V2 HGB_XS_MARKET artifacts for F1-F4.

At minimum verify:

- exact eligible row identity/order;
- fold boundaries;
- score semantics and row-level scores under the existing strict numeric tolerance;
- prevalence;
- PR-AUC and PR-AUC minus prevalence;
- ROC-AUC;
- Q1/Q5 TP rates and Q5-Q1 spread;
- top-decile TP rate/lift.

Pin the existing reference artifact hashes in the equivalence report.

If control equivalence fails: fail closed, do not interpret recency results, document the mismatch, and STOP for review. Do not weaken tolerance.

## Recency implementation

For training row session index `s`, training-end session `T`, and H in {252,504}:

- `age = T - s`;
- `raw_weight = 2 ** (-age / H)` in float64;
- normalize fold-locally: `weight = n * raw_weight / sum(raw_weight)`;
- require finite, positive weights;
- verify mean approximately 1.0 with strict tolerance such as 1e-12;
- validation metrics remain unweighted.

The exact V2 25 features, preprocessing, HGB parameters, H10 label, universe, score transform, and V2 metric semantics remain unchanged.

## Tests required before the outcome-bearing run

Add focused tests for at least:

- age definition and newest-row age zero;
- same-date rows receiving identical raw weight;
- H=252 and H=504 numerical formula;
- fold-local normalization;
- all weights finite/positive;
- no validation weighting;
- feature order/model parameters unchanged;
- fold boundaries unchanged;
- F5/F6 access blocked by the V3-A runner;
- provenance/hash mismatch fails closed;
- deterministic candidate order and tie rule;
- ledger cannot fabricate viewed results before run.

Run the relevant existing/full pytest suite as practical and report exact result/warnings.

## Runtime

The mandatory runtime note must be acknowledged. This workload is small enough that the preferred reference implementation is simple and deterministic. Profile first. Use sequential execution unless measured evidence justifies bounded concurrency. Do not create an optimization project inside this hypothesis.

Any optimized path must prove reference equivalence before it can produce accepted outcome artifacts.

## Metrics and verdict

Use the original spec's discovery absolute sanity gate and discovery paired promotion gate on F1-F4, with the review addendum's discovery-only promotion rule.

If both variants pass, use the original deterministic discovery tie rule and carry forward at most one recency component.

Possible V3-A result:

- one promoted recency component;
- or `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.

Do not invent a third outcome path or rescue criterion.

## Hypothesis ledger

Update ordinals 001-003 permanently. Record the spec and addendum identities, cache/provenance, code commit, fold set, model/weight identity, result-viewed state, artifact hashes, verdict, and cumulative evaluated candidate count.

Do not delete failed candidates or reuse ordinals.

## Deliverables

- recency implementation code + tests;
- exact-control equivalence report + reference hashes;
- F1-F4 candidate/fold metrics artifacts;
- aggregate paired-comparison artifact;
- deterministic verdict artifact;
- updated `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`;
- profiling/runtime report;
- dated implementation/result checkpoint;
- result handoff for ChatGPT review;
- `docs/CURRENT_STATUS.md` continuity update;
- clean git status and pushed branch.

All output artifacts must be immutable/hash-pinned where the repo convention requires it.

## Hard prohibitions

Do not:

- access V2F5/V2F6 candidate outcomes;
- inspect any reserved post-2026-07-31 V2 forward outcome;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- change the recency spec/addendum based on scores;
- add features or change label/universe/model parameters;
- start V3-B Structure-Lite or any later V3 lane;
- start Stage 6, calibration, IDX-VAL-002, execution-PnL, Kelly, paper/live trading, or main merge.

## Stop rule

After the F1-F4 V3-A result is fully documented and pushed, STOP and return the exact branch/HEAD, tests, equivalence result, candidate metrics, verdict, artifact hashes, ledger state, and confirmation that F5/F6 + V2 fresh-forward outcomes were not accessed.
