# O2 vs V2 Common-Support Comparator Preflight-Fix Runtime

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-o2-v2-common-support-comparator-v1`
Starting remote HEAD for fix: `e78efd476935229240549276e1111100dea60e4d`
Review addressed: `O2_V2_COMMON_SUPPORT_COMPARATOR_REVIEW_BLOCKED_O2_PARENT_PREFLIGHT_FIX_REQUIRED`
Runtime status: `O2_DIRECT_V2_COMMON_SUPPORT_BETTER`

## Bounded fix

The independent review identified two missing frozen preconditions in the
previous comparator runtime:

1. accepted O2 parent-artifact lineage was not verified before fitting;
2. the exact accepted O2 36-feature hash was computed but not explicitly
   fail-closed before fitting.

Only those preflight checks were added. The model set, feature set, population,
labels, folds, preprocessing, HGB parameters, evaluator, and verdict rule were
unchanged. A malformed JSON parent now also produces the harness's explicit
fail-closed `RuntimeError`.

## Accepted O2 parent lineage verified before fitting

The runtime verified every artifact listed by both authoritative parent
manifests:

- minimality selection lineage:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\ohlcv_o2_minimality_v1_20260812\artifact_manifest.json`;
  manifest SHA-256:
  `919e35bb8d2fe68588db331e3de25f6c2a490c2727aea9f68e1179c0bcbe5183`;
  schema: `idx-trade/ohlcv-o2-minimality-artifacts-v1`;
  status: `O2_MINIMALITY_EVIDENCE_COMPLETE`;
  listed artifacts verified: `11/11`;
  contains `O2_FULL_3` and the exact accepted 36-feature hash;
- accepted geometry parent:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\ohlcv_o2_geometry_v1_20260812\artifact_manifest.json`;
  manifest SHA-256:
  `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`;
  schema: `idx-trade/ohlcv-o2-geometry-research-artifacts-v1`;
  status: `O2_SURVIVOR`;
  listed artifacts verified: `10/10`;
  model identity: `O2_OPEN_GEOMETRY`.

Both parents independently verified the common-support contract:
`278,168` rows, `729` tickers, and key SHA-256
`716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`.

The explicit O2 feature-order preflight was:

- expected: `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- actual: `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- verified: `true`.

## Frozen rerun

The exact same two models and six folds were rerun into a new external root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\o2_v2_common_support_comparator_v1_20260812_preflight_fix`

The prior `..._retry1` root was preserved and not overwritten. Numeric
`fold_metrics.csv`, `aggregate_metrics.csv`, `paired_comparisons.csv`, and
`fold_row_identity_checks.csv` are identical to `retry1`; only runtime timing,
preflight contract, summary, and manifest hashes differ.

The result remains:

- median paired PR-AUC delta: `+0.002939019431462575`;
- lower-quartile paired PR-AUC delta: `+0.002304097591101159`;
- positive paired PR-AUC folds: `5/6`;
- median ROC-AUC guardrail reversal: `false`;
- verdict: `O2_DIRECT_V2_COMMON_SUPPORT_BETTER`.

Common support remained `278,168` rows / `729` tickers. The immutable panel
SHA-256 before and after remained:
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Validation and artifacts

- focused preflight/comparator tests: `8 passed`;
- scoped full pytest: `297 passed, 5 warnings`;
- provider/network calls: none;
- fresh-forward outcomes accessed: `false`;
- new artifact manifest SHA-256:
  `4e0fc0faf3b09f1e47a3455bd7cee2609ed79920960139922abf5cffac30903d`;
- new runtime artifact files listed: `10`;
- new runtime artifact hashes re-verified: `10/10`.

## Stop condition

Stop for independent ChatGPT review. No new model, tuning, provider work,
forward scoring, outcome access, canonical overwrite, or downstream experiment
was started.
