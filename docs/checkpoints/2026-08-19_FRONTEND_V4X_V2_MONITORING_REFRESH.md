# Frontend V4-X / V2 monitoring refresh

Date: 2026-08-19 (Asia/Jakarta)
Branch: `frontend/v4x-v2-monitoring-refresh-v1`
Base: `codex/frontend-compare-v2` at `bc91a5f99502bb507ed905bdce6c0ac993348d55`
Status: `IMPLEMENTED_LOCAL_BUILD_VALIDATION_PENDING`

## User direction

The primary product surface should stop presenting retired/non-final model lanes as if they remain active. The main dashboard and Forward Monitoring should focus on:

1. V4-X / V4-X1 Geometry3 as the current frozen alpha candidate under clean 100-session prospective confirmation; and
2. V2 `HGB_XS_MARKET` / **V2 HGB XS + Market** as the durable forward reference.

This is a hierarchy change, not a request to delete the existing research UI. Historical model inspection, chart hover/tooltips, model picker, and research archive must remain available.

The historical model-comparison page must remain in source control but be removed from normal navigation for now.

## Changes

### Main dashboard

`apps/web/app/page.tsx` keeps the rich research UI while changing the default hierarchy:

- V4-X Geometry3 is the hero/current alpha candidate.
- V2 HGB XS + Market is the active reference.
- O2, V3-B, and other historical experiments remain inspectable under `Past Model Evidence` and `Research Archive`, but are no longer presented as primary forward lanes.
- comparison navigation/linking was removed; `/compare` source remains untouched.
- the V4-X historical chart uses exact frozen V4-3R consensus rank-IC folds for Geometry3 vs the same 25-feature V4 control.
- user-facing UI calls that comparator **`V4 control · 25 features`**, rather than exposing the internal `Context25` label.
- the V4-X chart restores per-fold hover/tooltip, exact IC display, per-fold Geometry3-minus-control delta, and fold-method help.
- the historical model picker restores interactive V2/V3/V4/O1/O2/etc evidence and the prior hover behavior for their fold charts.
- the research archive restores ranking/result/model filters and expandable decision rows.
- summary values use the accepted historical evidence: Geometry3 median consensus IC `0.09775243938276076`, V4 25-feature control `0.08415844149089491`, approximately `+16.15%` relative lift.
- the dashboard explicitly distinguishes historical parent evidence from unknown X1 prospective performance.

### Monitoring

`apps/web/app/monitoring/page.tsx` has two primary monitored lanes only:

- `V4_X1_GEOMETRY3_PROSPECTIVE` / V4-X Geometry3;
- `HGB_XS_MARKET` / **V2 HGB XS + Market**.

The V2 card title includes the generation and actual model family so `Reference model` is not ambiguous.

The canonical automated EOD archive remains the only session source. The page does not recreate or alter capture infrastructure.

V4-X currently reports zero prospective score artifacts until the separate outcome-blind V4-X score adapter starts writing canonical model-run artifacts. This is intentional and must not be backfilled from historical V4-3R predictions.

### Model detail

`apps/web/app/monitoring/models/[modelId]/page.tsx` presents V4-X and V2 semantics.

- V4-X detail emphasizes frozen confirmation/no retraining and shows the bundle manifest rather than pretending there is one single model SHA; X1 has four frozen model files.
- V2 detail is explicitly titled `V2 HGB XS + Market` and restores a visible historical score summary: median PR-AUC delta `+2.39%`, median ROC-AUC `0.5244`, and median Q5−Q1 `+5.12%` across the six V2 development folds.
- the full interactive V2 fold chart remains available on Overview under `Past Model Evidence`.

### V4-X frontend catalog

Added `apps/web/lib/v4x-catalog.ts` containing the exact frontend-safe identity and accepted historical evidence, including:

- X1 generation ID;
- 28-feature Geometry3 contract (25-feature V4 control + 3 Geometry3 features);
- final-refit bundle manifest SHA-256 `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`;
- historical consensus/H5/H10 IC summaries;
- exact six Geometry3 and V4-control consensus fold IC values;
- bootstrap evidence;
- 100-session forward target.

### Comparison page

`apps/web/app/compare/**` is deliberately untouched. Normal Overview, Monitoring, and model-detail navbars no longer expose `/compare`.

## Scientific semantics

Do not label `0.09775` as X1 prospective IC. It is historical V4-3R Geometry3 evidence carried into the V4-X family. X1 exact final-refit prospective IC remains unknown and locked.

The historical V4-X chart compares Geometry3 with the frozen V4 25-feature control because those are the exact paired values produced by V4-3R. V2 remains the monitoring reference, but the V4 control series must not be falsely relabeled as the byte-identical V2 final model.

## Validation guard

`tests/test_frontend_v4x_focus_contract.py` now enforces:

- `/compare` is absent from normal primary nav links while compare source still exists;
- V4-X and V2 are the primary monitor routes;
- historical `RESEARCH_EXPERIMENTS`, model picker, hover/tooltips, fold help, filters, and expandable archive remain in the main dashboard;
- the user-facing comparator label is `V4 control · 25 features`, not `Context25`;
- exact V4-X manifest and historical IC evidence are pinned;
- V2 is explicitly named `V2 HGB XS + Market` and its historical summary remains visible in model detail.

Required local validation before merge:

- focused pytest for the frontend contract;
- `npm run build` under `apps/web`;
- HTTP 200 smoke for `/`, `/monitoring`, `/monitoring/models/v4x`, `/monitoring/models/v2`;
- visual smoke for desktop/mobile navigation, V4-X hover tooltip, V2 historical picker chart, and archive expand/filter behavior.

No backend model runtime, scientific model bytes, canonical EOD scheduler, outcome vault, V3-B/O2 history, or comparison source code was deleted or modified.