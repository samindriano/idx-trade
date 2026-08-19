# Frontend V4-X / V2 monitoring refresh

Date: 2026-08-19 (Asia/Jakarta)
Branch: `frontend/v4x-v2-monitoring-refresh-v1`
Base: `codex/frontend-compare-v2` at `bc91a5f99502bb507ed905bdce6c0ac993348d55`
Status: `AUDIT_EVIDENCE_REFRESH_IMPLEMENTED_LOCAL_BUILD_VALIDATION_PENDING`

## User direction

The primary product surface should stop presenting retired/non-final model lanes as if they remain active. The main dashboard and Forward Monitoring focus on:

1. V4-X / V4-X1 Geometry3 as the current frozen alpha candidate under clean 100-session prospective confirmation; and
2. V2 `HGB_XS_MARKET` / **V2 HGB XS + Market** as the durable forward reference.

Historical research remains inspectable. `/compare` remains in source control but is not in normal navigation.

## V4-X historical audit evidence carried into frontend

The dedicated red-team audit is recorded on branch `research/v4x-critical-alpha-audit-v1` in:

`docs/checkpoints/2026-08-19_V4X_HISTORICAL_ALPHA_CRITICAL_AUDIT_FINAL.md`

Final historical audit verdict:

`V4X_HISTORICAL_ALPHA_AUDIT_PASS_NO_CRITICAL_ERROR_FOUND`

Preferred defensible historical headline:

- **mean daily common-support Spearman RankIC `0.09545975125676774` across 600 chronological historical validation sessions**.

Conservative robustness result:

- strict exact-feature-window-support mean daily RankIC `0.08327323251280924`;
- retained observable rows `89.9685%`;
- consensus remained positive in 6/6 folds.

Control common-support consensus RankIC:

`0.08979323509925058`

Geometry3 common-support incremental mean daily consensus RankIC:

`+0.00566651615751716`

Paired historical incremental evidence:

- mean paired daily consensus delta `+0.005804318872319132`;
- median paired fold-mean delta `+0.0062863346170079215`;
- positive paired consensus-delta folds `5/6`.

### Important reporting correction

The original frozen V4-3R aggregates remain valid lineage values:

- Geometry3 median of six fold-mean consensus ICs `0.09775243938276076`;
- V4 control median `0.08415844149089491`.

However, their difference (`0.013594`, previously summarized as about `+16.15%`) is a **difference of two independently aggregated medians**, not the preferred paired incremental estimand.

Frontend must therefore:

- preserve the original six-fold chart and frozen medians for exact lineage;
- use `0.09546` when presenting a generic audited historical RankIC;
- use `0.08327` as the strict-support robustness IC when shown;
- use approximately `+0.0057` as the preferred common-support Geometry3 incremental IC;
- say paired Geometry3 delta is positive in `5/6` folds, while Geometry3's own absolute consensus IC is positive in `6/6` folds;
- never present `+16.15%` as the primary incremental Geometry3 conclusion;
- never label any historical V4-3R metric as X1 prospective performance.

## Historical audit tests represented by this evidence

The source-of-truth audit branch records the full commands, artifacts, and outputs. Frontend documentation preserves the summary so the UI can be interpreted correctly later.

Historical red-team coverage included:

1. synthetic future-mutation / causality tests: **11 passed**;
2. V4/V4-3R core regression and contract tests: **59 passed**;
3. frozen market/Open forensic audit: PASS with zero invalid canonical HLC, zero accepted Open outside H/L, and zero derivative/overlay finite conflicts;
4. exact reproduction of stored daily IC from consumed artifacts to floating-point noise (`~1e-16` maximum error);
5. true common-support Spearman recomputation;
6. paired Geometry3-vs-control incremental reinterpretation;
7. 1,000 within-date target permutations for challenger and control;
8. exact official-session / strict actual-feature-window support attack;
9. future target-observability selection attack;
10. repository-suite housekeeping: one stale storage-test expectation was identified and corrected; focused post-fix verification passed, while final full-repository post-fix rerun remains a local housekeeping check until recorded.

Permutation-null challenger consensus evidence:

- observed common-support RankIC `0.09545975`;
- null q99.9 `0.00647637`;
- z-score `36.86`;
- 0/1000 shuffled runs matched or exceeded the observed result (reported empirical resolution `1/1001`).

These diagnostics do not eliminate researcher/model-selection bias from the broader historical research process. That uncertainty belongs to the fresh V4-X1 prospective block.

## Changes

### Main dashboard

`apps/web/app/page.tsx` keeps the rich research UI while changing the default hierarchy:

- V4-X Geometry3 is the hero/current alpha candidate.
- V2 HGB XS + Market is the active reference.
- O2, V3-B, and other historical experiments remain inspectable under `Past Model Evidence` and `Research Archive`.
- comparison navigation/linking is removed; `/compare` source remains untouched.
- the V4-X historical chart retains exact frozen V4-3R fold IC values for Geometry3 and the same 25-feature V4 control.
- user-facing comparator label remains **`V4 control · 25 features`** rather than internal `Context25` terminology.
- chart hover/tooltip, fold methodology help, historical model picker, and archive controls remain intact.

The overview chart itself remains a display of the **frozen fold protocol**, so its original median-fold aggregate fields remain in the catalog for lineage. The audited generic RankIC is deliberately stored separately rather than silently changing the chart's statistical definition.

### Monitoring

`apps/web/app/monitoring/page.tsx` has two primary monitored lanes only:

- `V4_X1_GEOMETRY3_PROSPECTIVE` / V4-X Geometry3;
- `HGB_XS_MARKET` / **V2 HGB XS + Market**.

Canonical automated EOD archive remains the only session source. No capture infrastructure is recreated or altered.

V4-X may report zero prospective score artifacts until the separate outcome-blind V4-X score adapter starts writing canonical model-run artifacts. Historical V4-3R predictions must never be backfilled into the X1 prospective counter.

### V4-X model detail

`apps/web/app/monitoring/models/[modelId]/page.tsx` now presents the audited historical evidence explicitly for V4-X:

- headline `AUDITED HISTORICAL RANKIC` uses common-support Spearman `0.09546`;
- detail facts include common-support RankIC and strict-support RankIC;
- audit note records approximately `+0.0057` common-support incremental IC versus the V4 25-feature control;
- paired improvement is labeled `5/6` folds, not 6/6;
- text explicitly states that the audit found no critical historical leakage/metric error **without** claiming prospective validation;
- forward outcome remains locked and the model remains frozen.

V2 detail remains explicitly titled `V2 HGB XS + Market` and retains historical median PR-AUC delta `+2.39%`, ROC-AUC `0.5244`, and Q5−Q1 `+5.12%`.

### V4-X frontend catalog

`apps/web/lib/v4x-catalog.ts` now separates two statistical identities:

1. **frozen V4-3R fold aggregates** used by the exact historical chart;
2. **audited common-support / strict-support evidence** used by the defensible historical-alpha interpretation.

Pinned audit values include:

- `auditedCommonSupportConsensusIc = 0.09545975125676774`;
- `auditedCommonSupportControlConsensusIc = 0.08979323509925058`;
- `auditedCommonSupportH5Ic = 0.07493424533009098`;
- `auditedCommonSupportH10Ic = 0.09185167971133042`;
- `auditedStrictSupportConsensusIc = 0.08327323251280924`;
- `auditedStrictSupportRetainedFraction = 0.8996852225456887`;
- `auditedCommonSupportIncrementalIc = 0.00566651615751716`;
- `auditedPositivePairedConsensusDeltaFolds = 5`;
- audit status `PASS_NO_CRITICAL_ERROR_FOUND`;
- historical validation sessions `600`.

## Scientific semantics

Preferred concise statement:

> V4-X achieved a historical mean daily cross-sectional Spearman RankIC of approximately **0.095** across **600 chronological walk-forward validation sessions**; under a stricter exact-session feature-support filter, RankIC remained approximately **0.083**.

Required qualifier: **historical** / historical-development.

Do not say `V4-X IC = 0.095` as if it were already live or prospective.

Do not call the frozen `0.09775` value a generic mean RankIC; it is the median of six fold-mean ICs.

X1 exact prospective performance remains unknown and locked.

## Validation guard

`tests/test_frontend_v4x_focus_contract.py` now additionally pins:

- audited common-support RankIC;
- audited control RankIC;
- strict-support RankIC;
- audited incremental Geometry3 IC;
- 5/6 paired incremental fold semantics;
- audit PASS status;
- 600-session historical evaluation count;
- V4-X detail copy that separates audited historical evidence from prospective X1 performance.

Required local validation before merge:

```powershell
python -m pytest -q tests/test_frontend_v4x_focus_contract.py

git diff --check
```

Under `apps/web`:

```powershell
npm run build
```

Then HTTP 200 smoke for:

- `/`
- `/monitoring`
- `/monitoring/models/v4x`
- `/monitoring/models/v2`

and visual smoke for desktop/mobile navigation, V4-X historical hover tooltip, audited V4-X detail, V2 historical picker chart, and archive expand/filter behavior.

Do not claim these local frontend validations passed until their outputs are actually recorded.

No backend model runtime, scientific model bytes, canonical EOD scheduler, outcome vault, V3-B/O2 history, or comparison source code was deleted or modified.