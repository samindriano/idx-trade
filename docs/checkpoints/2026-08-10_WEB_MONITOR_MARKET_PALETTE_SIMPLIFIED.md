# Web Monitor — Market Palette + Copy Simplification

Date: 2026-08-10
Branch: `frontend/model-monitoring-v1`

## Decision

The frontend visual direction is now a light IDX/stock-terminal style rather than a blue SaaS/product-analytics style.

Primary visual semantics:

- green = positive / active / recorded / verified / champion progress;
- red = weak / negative / missing / failed;
- amber = pending / fetching / locked / transitional state;
- warm ivory + charcoal = neutral structure/background;
- blue is no longer a primary semantic color.

## Copy-density rule

The operator pages should prefer **status + number + action** over explanatory prose.

Removed/reduced:

- redundant hero descriptions;
- metric helper text;
- long forward-test teaching copy;
- large recovery explanation section;
- verbose model descriptions in the model toolbar;
- redundant `Models` top-nav item (the model table remains reachable by scrolling Overview).

Top navigation is now:

- `Overview`
- `Forward Monitoring`

## Chart interaction

The native browser SVG `<title>` tooltip is replaced with a custom floating finance-style tooltip showing:

- Fold;
- ΔPR-AUC;
- ROC-AUC;
- Q5-Q1.

Color semantics inside the tooltip:

- positive metrics = green;
- ROC below 0.5 / negative metric = red.

Weak fold chart points (`ROC < 0.5`) are visually marked red while the main historical ranking series remains green.

## Files

- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`
- `apps/web/app/model-monitor.module.css`
- `apps/web/app/monitoring/page.tsx`
- `apps/web/app/monitoring/monitoring.css`

## Research/runtime boundary

This change is presentation-only. It does not:

- access fresh-forward outcomes;
- score V2;
- alter model semantics;
- retrain/refit models;
- write `FORWARD_OUTCOME_ACCESS_STARTED`.

## Next verification

Local-only verification is appropriate after pull:

- `npm run build`;
- open `/`;
- open `/monitoring`;
- visually verify the custom fold tooltip and green/red/amber state semantics.

No Codex implementation work is required unless a local build/runtime issue is discovered.
