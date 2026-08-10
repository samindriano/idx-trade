# Ranking V3-B Final Refit / Fresh-Forward Spec Review — PASS

Date: 2026-08-10 (Asia/Jakarta)
Status: **PRE-OUTCOME REVIEW PASS — IMPLEMENTATION + ONE FINAL HISTORICAL REFIT AUTHORIZED / FRESH OUTCOME ACCESS BLOCKED**

## Decision

`RANKING_V3_FINAL_FORWARD_SPEC_REVIEW_PASS`

Controlling specification:

`docs/RANKING_V3_FINAL_FORWARD_SPEC_V1.md`

Frozen spec Git blob:

`024f1919de8d5ea4e2e9933a9e4c1a1ef9bbe4f4`

The specification is accepted as a bounded continuation of the already-closed historical alpha program.

## Review findings

1. The final architecture is not reopened. Exact V3-B Structure-Lite remains the only active ranker.
2. The final refit is one training fit, not a new model-selection experiment. Using exact resolved historical rows through session 1250 after architecture closure is acceptable only because no metric or selection decision is made from sessions 1225..1250.
3. The exact V2 prepared row set is preserved; Structure-Lite is appended causally without row pruning.
4. The forward block remains strictly post-2026-07-31 and outcome-sealed.
5. Reusing the previously frozen V2 fresh-forward PASS/MIXED/FAIL semantics avoids introducing a more convenient threshold after V4.
6. The first fresh block is reserved for final V3-B; it cannot be used afterward to choose adaptively between V2 and V3-B.
7. The global one-shot marker remains mandatory before any future outcome read.

## Authorization now

Authorized:

- implement `ranking_v3_forward_runtime` and focused tests;
- reuse tested V2 maturity/metric/marker primitives where semantics are identical;
- build the exact 292,633-row V3-B final training table from frozen inputs;
- fit the exact frozen V3-B model once;
- serialize/hash the model and manifest;
- implement outcome-blind forward V3-B feature/scoring preparation;
- test causal and marker behavior only on historical/synthetic/temp fixtures.

## Still blocked

Do not:

- inspect post-2026-07-31 labels/outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED` in the real snapshot store;
- produce a fresh-forward verdict;
- change the 33-feature architecture or model parameters;
- score sessions 1225..1250 as a validation slice;
- reopen V4 or add a new alpha family;
- calibrate probabilities;
- start Stage 6 / `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.

The actual one-shot forward outcome phase remains a later event because the first 100 post-cutoff official signal sessions cannot yet be H10-mature on 2026-08-10.