# O2 vs V2 Common-Support Comparator — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-o2-v2-common-support-comparator-v1`
Reviewed runtime HEAD: `39e85006e68ba45df3755f1d4bd6b75abc3c1ba4`
Frozen spec HEAD: `f3297c19adbb8e890b56849daa895aee36fe1fc6`
Reviewer decision: `O2_V2_COMMON_SUPPORT_COMPARATOR_REVIEW_BLOCKED_O2_PARENT_PREFLIGHT_FIX_REQUIRED`

## What is accepted from the evidence

The reported historical result is numerically consistent with the frozen comparator rule:

- exact reported common support: `278,168` rows / `729` tickers;
- paired PR-AUC delta positive in `5/6` folds;
- median paired PR-AUC delta: `+0.002939019431462575`;
- lower-quartile paired PR-AUC delta: `+0.002304097591101159`;
- median ROC-AUC and median Q5-Q1 do not jointly reverse against V2;
- therefore the reported runtime verdict `O2_DIRECT_V2_COMMON_SUPPORT_BETTER` is the correct verdict **if the frozen preflight contract is satisfied**.

The implementation also uses the same in-memory train/validation frames for both models within each fold, the same H10 labels/evaluator/HGB parameters, and records the expected common-support identity. The reviewed diff contains no provider calls, forward-scoring/counter work, tuning, canonical overwrite, or fresh-forward outcome access.

## Blocking contract deviation

The frozen spec explicitly requires **before fitting**:

1. verification of accepted O2 parent artifacts; and
2. verification of the exact accepted O2 36-feature hash.

The runtime implementation does not fully enforce those two preconditions:

- `_verify_v2_frozen_artifacts(...)` pins and verifies the V2 parent artifacts, but there is no corresponding accepted-O2 parent artifact verification path in `run_comparator(...)` or the CLI arguments;
- `EXPECTED_O2_FEATURE_ORDER_SHA256 = a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f` is defined, but the runtime does not explicitly fail closed on `feature_order_hash(O2_FEATURE_COLUMNS) != EXPECTED_O2_FEATURE_ORDER_SHA256` before fitting;
- the runtime checkpoint records the computed O2 feature hash but does not record verified hashes/status/identity for the accepted O2 parent artifact lineage.

This is a reproducibility/provenance gate failure, not a negative scientific result. The observed metrics should not be discarded, but this particular runtime cannot be independently accepted as satisfying the frozen spec until the missing O2 preflight is implemented and the comparator is rerun.

## Required bounded fix

Implement only the missing fail-closed preflight; do not change the experiment design or use the observed result to modify any threshold/model/feature/population.

Required actions:

- resolve the exact accepted O2 full-3 parent artifact(s) from the authoritative O2 minimality/selection lineage that the frozen spec was based on;
- pin their expected SHA-256 values and verify file hashes plus the relevant accepted status/model identity/36-feature identity before any fit;
- explicitly verify `feature_order_hash(O2_FEATURE_COLUMNS) == EXPECTED_O2_FEATURE_ORDER_SHA256` at runtime before fitting;
- add focused tests showing missing/corrupted/wrong-identity O2 parent artifacts and a wrong O2 feature hash fail closed;
- rerun the identical frozen comparator into a **new** external runtime root; preserve the current `retry1` root as superseded evidence and never overwrite it;
- rerun focused and full pytest, re-hash the new artifact manifest, write a new runtime/fix checkpoint, push, and STOP for independent review.

No new model, tuning, provider work, forward scoring, outcome access, canonical change, or downstream experiment is authorized by this review.

## Interpretation pending fix

Subject to the bounded provenance fix reproducing the same evidence, the historical conclusion is directionally clear: O2 full-3 beats the older V2 HGB comparator on the exact O2 common support under the preregistered rule. This remains historical-development evidence only and does not promote O2 over canonical V3-B or substitute for either model's fresh-forward gate.
