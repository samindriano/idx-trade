# O2 vs V2 Common-Support Comparator Preflight Fix — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-o2-v2-common-support-comparator-v1`
Reviewed runtime HEAD: `790bb0670e116fe38b2411b8cc3279712166cfb3`
Frozen comparator spec: `docs/checkpoints/2026-08-12_O2_V2_COMMON_SUPPORT_COMPARATOR_SPEC.md`
Prior blocking review: `docs/checkpoints/2026-08-12_O2_V2_COMMON_SUPPORT_COMPARATOR_INDEPENDENT_REVIEW.md`
Decision: `O2_V2_COMMON_SUPPORT_COMPARATOR_ACCEPTED_HISTORICAL_DEVELOPMENT_EVIDENCE`

## Review conclusion

The bounded preflight repair resolves the prior reproducibility/provenance blocker without changing the frozen experiment semantics. The repaired rerun is accepted as valid historical-development evidence.

The accepted scientific verdict is:

`O2_DIRECT_V2_COMMON_SUPPORT_BETTER`

This remains descriptive historical-development evidence only. It does not promote O2 over canonical V3-B, does not replace either fresh-forward gate, and does not authorize any downstream model/risk/sizing/execution work.

## Verified blocker resolution

The prior review required accepted-O2 parent verification and an explicit fail-closed O2 feature-order check before fitting. The reviewed implementation now performs those checks at the start of `run_comparator(...)`, before common-support loading, output artifact creation beyond the runtime root, and before any model fit.

Accepted O2 lineage is pinned and verified:

- minimality parent manifest SHA-256: `919e35bb8d2fe68588db331e3de25f6c2a490c2727aea9f68e1179c0bcbe5183`;
  - schema `idx-trade/ohlcv-o2-minimality-artifacts-v1`;
  - status `O2_MINIMALITY_EVIDENCE_COMPLETE`;
  - `O2_FULL_3` identity required;
  - common support `278168` rows / `729` tickers;
  - exact common-support key SHA required;
  - exact O2 36-feature hash required;
  - every listed artifact is re-hashed before fitting.
- geometry parent manifest SHA-256: `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`;
  - schema `idx-trade/ohlcv-o2-geometry-research-artifacts-v1`;
  - status `O2_SURVIVOR`;
  - model identity `O2_OPEN_GEOMETRY` required;
  - same common-support identity and O2 feature hash required;
  - every listed artifact is re-hashed before fitting.

The exact O2 feature-order preflight now explicitly requires:

`a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`

A mismatch raises before fitting.

Focused tests cover missing parent manifests, corrupted parent JSON, wrong accepted-O2 identity, and wrong O2 feature hash. The implementation also fail-closes on listed-parent artifact hash mismatches through the shared file-verification path.

## Reproduced frozen evidence

The rerun used a new external runtime root and preserved the previous `retry1` evidence.

Reproduced result:

- common support: `278168` rows / `729` tickers;
- median paired PR-AUC delta, O2 minus V2: `+0.002939019431462575`;
- lower-quartile paired PR-AUC delta: `+0.002304097591101159`;
- positive paired PR-AUC folds: `5/6`;
- median ROC-AUC + Q5-Q1 double-reversal guardrail: `false`;
- verdict: `O2_DIRECT_V2_COMMON_SUPPORT_BETTER`.

The result satisfies the frozen comparator rule: positive median and lower quartile paired PR-AUC delta, at least 4/6 positive folds, and no double ranking-guardrail reversal.

New runtime artifact manifest SHA-256:

`4e0fc0faf3b09f1e47a3455bd7cee2609ed79920960139922abf5cffac30903d`

All `10/10` listed runtime artifact hashes were reported and re-verified. The immutable source panel SHA remained unchanged.

Validation reported by the repaired runtime:

- focused comparator/preflight tests: `8 passed`;
- full pytest: `297 passed, 5 warnings`;
- provider/network calls: none;
- fresh-forward outcomes accessed: `false`;
- tuning/calibration: none;
- canonical model overwrite: none.

## Interpretation

This comparator answers a narrow question: on the exact O2 common-support population and the frozen historical folds, the selected O2 full-3 representation is better than the older frozen Ranking-V2 `HGB_XS_MARKET` comparator under the preregistered rule.

It is not a clean isolation of the three Open-geometry features versus canonical V3-B, because O2 contains the full canonical V3-B 33-feature representation plus the three geometry features while the direct V2 comparator contains the older 25-feature V2 set. Incremental geometry evidence versus the 33-feature baseline remains established by the separately accepted O2 geometry/minimality research lineage.

## Authorization boundary

This lane is complete and may be closed as accepted historical-development evidence.

Do not from this result alone:

- replace canonical V3-B;
- alter O2 or V3-B fresh-forward contracts/counters;
- access protected fresh-forward outcomes;
- tune/recalibrate either model;
- open another alpha feature/model rescue search;
- start Path Risk, sizing, execution, Kelly, paper/live, or any other downstream system automatically.

Any materially dependent next step must follow the repository checkpoint discipline and its own controlling authorization.