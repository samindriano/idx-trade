# Web Model Monitor V2 — Light Redesign

Date: 2026-08-10 (Asia/Jakarta)
Branch: `frontend/model-monitoring-v1`

## Decision

The first dark/sidebar-heavy monitor was intentionally superseded by a simpler light-theme finance research dashboard.

The redesign goal is not to imitate a generic admin dashboard. It prioritizes a small number of high-value model-monitoring surfaces on one page:

1. model selector;
2. four historical benchmark metrics;
3. one chronological robustness chart;
4. one forward-validation readiness panel;
5. one model-comparison table.

The V3 backlog and artifact registry are intentionally removed from the primary page to reduce information density. Model-generation switching remains supported through the selector and comparison table.

## Visual direction

- Light warm-neutral background with white analytical surfaces.
- Top navigation instead of a permanent dark sidebar.
- Minimal card count and stronger whitespace hierarchy.
- Green used as an analytical accent, not as a full-page terminal theme.
- CSS-only micro-interactions for model switching, line-chart draw, row hover, and state changes; no new animation/chart dependency was added.
- Chronological fold evidence is presented as a finance-style line/area chart rather than progress bars.

The layout is informed by current finance-dashboard patterns such as Koyfin's emphasis on at-a-glance dashboards, linked views, and reusable model/security selection, while deliberately keeping the IDX Trade page materially simpler than a general market terminal.

## Research integrity

No research/model semantics were changed.

- Historical metric values remain the frozen V2 values already present in the frontend fixture.
- `HGB_XS_MARKET` remains the V2 champion.
- Forward outcomes are not rendered or accessed.
- `FORWARD_OUTCOME_ACCESS_STARTED` is not written.
- The page continues to distinguish historical candidates from the champion's frozen forward contract.

## Files changed

- `apps/web/app/page.tsx`
- `apps/web/app/globals.css`

## Verification boundary

The GitHub-side redesign did not execute the local Next.js build. The preceding scaffold had already passed `npm install`, `npm run build`, and HTTP `200 OK` before this redesign. The next local action is to pull the branch and rerun `npm run build` plus a browser smoke test before further visual iteration.
