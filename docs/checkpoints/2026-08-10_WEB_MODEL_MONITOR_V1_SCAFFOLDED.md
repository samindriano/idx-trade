# Web Model Monitor V1 Scaffolded

Date: 2026-08-10 (Asia/Jakarta)

## Decision

A separate WEB lane is now authorized and scaffolded for an outcome-blind, model-switchable research dashboard. This does not change any Ranking V2 research gate or authorize fresh-forward outcome access.

## Branch

`frontend/model-monitoring-v1`

Base commit:

`46a5a2e9eaadb6111d59214633511eb11d21ab9e`

## Implementation

New Next.js application under `apps/web` using:

- Next.js 16.2.11;
- React 19.2;
- TypeScript;
- App Router;
- dependency-light plain CSS.

The first dashboard includes:

- model switcher for V1/V2 historical candidates;
- disabled V3 backlog entries for future model generations;
- frozen historical-development metrics and six-fold robustness visualization;
- V2 `HGB_XS_MARKET` final-model fingerprint;
- forward-monitoring shell with explicit outcome lock;
- session-ledger placeholder that contains no fabricated rows;
- V3 parallel research backlog display.

## Data/integrity boundary

The frontend must remain a display/monitoring layer and must not fabricate market values or forward results.

At this checkpoint:

- fresh-forward outcomes were not accessed;
- no forward rankings, TP/SL labels, or new session facts were invented;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains outside WEB scope;
- the current one-shot 100-session gate remains unchanged;
- no trading/execution action is exposed.

## Design references

The layout direction intentionally borrows high-level interaction principles rather than copying visual assets:

- Koyfin: modular dashboards, reusable watchlist/dashboard views;
- TradingView: dense market-oriented scanning patterns;
- Stock Analysis / modern finance research products: clean tables and compact hierarchy.

## Next action

Run the Next.js application locally, review visual fit, then iterate on UI before wiring any research-runtime adapter. Any adapter must preserve the V2 outcome-access boundary and distinguish signal-side monitoring from outcome access.
