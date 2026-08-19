# Frontend V4-X / V2 monitoring refresh

Date: 2026-08-19 (Asia/Jakarta)
Branch: `frontend/v4x-v2-monitoring-refresh-v1`
Base: `codex/frontend-compare-v2` at `bc91a5f99502bb507ed905bdce6c0ac993348d55`
Status: `IMPLEMENTED_LOCAL_BUILD_VALIDATION_PENDING`

## User direction

The primary product surface should stop presenting retired/non-final model lanes as if they remain active. The main dashboard and Forward Monitoring should focus on:

1. V4-X / V4-X1 Geometry3 as the current frozen alpha candidate under clean 100-session prospective confirmation; and
2. V2 `HGB_XS_MARKET` as the durable forward reference.

The historical model-comparison page must remain in source control but be removed from normal navigation for now.

## Changes

### Main dashboard

`apps/web/app/page.tsx` was simplified from a broad research archive into a current-alpha dashboard:

- V4-X Geometry3 is the hero/current alpha candidate.
- V2 is the only active reference lane shown beside V4-X.
- O2 and V3-B are no longer promoted in the primary dashboard.
- comparison navigation/linking was removed; `/compare` source remains untouched.
- historical evidence chart now uses exact frozen V4-3R consensus rank-IC folds for Geometry3 vs the Context25 control.
- summary values use the accepted historical evidence: Geometry3 median consensus IC `0.09775243938276076`, Context25 control `0.08415844149089491`, approximately `+16.15%` relative lift.
- the dashboard explicitly distinguishes historical parent evidence from unknown X1 prospective performance.

### Monitoring

`apps/web/app/monitoring/page.tsx` now has two primary monitored lanes only:

- `V4_X1_GEOMETRY3_PROSPECTIVE` / V4-X Geometry3;
- `HGB_XS_MARKET` / V2.

The canonical automated EOD archive remains the only session source. The page does not recreate or alter capture infrastructure.

V4-X currently reports zero prospective score artifacts until the separate outcome-blind V4-X score adapter starts writing canonical model-run artifacts. This is intentional and must not be backfilled from historical V4-3R predictions.

### Model detail

`apps/web/app/monitoring/models/[modelId]/page.tsx` now presents V4-X and V2 semantics. V4-X detail emphasizes frozen confirmation/no retraining and shows the bundle manifest rather than pretending there is one single model SHA; X1 has four frozen model files.

### V4-X frontend catalog

Added `apps/web/lib/v4x-catalog.ts` containing the exact frontend-safe identity and accepted historical evidence, including:

- X1 generation ID;
- 28-feature Geometry3 contract (Context25 + 3 Geometry3 features);
- final-refit bundle manifest SHA-256 `3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094`;
- historical consensus/H5/H10 IC summaries;
- exact six Geometry3 and Context25 consensus fold IC values;
- bootstrap evidence;
- 100-session forward target.

### Comparison page

`apps/web/app/compare/**` is deliberately untouched. Normal Overview, Monitoring, and model-detail navbars no longer expose `/compare`, and the old Overview comparison CTA was removed with the dashboard simplification.

## Scientific semantics

Do not label `0.09775` as X1 prospective IC. It is historical V4-3R Geometry3 evidence carried into the V4-X family. X1 exact final-refit prospective IC remains unknown and locked.

The historical chart compares Geometry3 with the frozen V4 Context25 control because those are the exact paired values produced by V4-3R. V2 remains the monitoring reference, but the chart must not falsely relabel the V4 Context25 control fold series as the byte-identical V2 final model.

## Validation guard

Added `tests/test_frontend_v4x_focus_contract.py` to enforce:

- `/compare` is absent from normal primary nav links while compare source still exists;
- primary dashboard/monitor pages use V4-X and V2 rather than O2/V3-B;
- exact V4-X manifest and historical IC evidence are pinned;
- monitoring routes only the active `v4x` and `v2` cards.

Required local validation before merge:

- focused pytest for the frontend contract;
- `npm run build` under `apps/web`;
- HTTP 200 smoke for `/`, `/monitoring`, `/monitoring/models/v4x`, `/monitoring/models/v2`;
- visual smoke for desktop/mobile navigation and the historical IC SVG.

No backend model runtime, scientific model bytes, canonical EOD scheduler, outcome vault, V3-B/O2 history, or comparison source code was deleted or modified.