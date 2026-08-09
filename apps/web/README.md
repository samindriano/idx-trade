# IDX Trade Web — Model Observatory V1

Next.js research dashboard for monitoring IDX Trade model generations without crossing research/outcome-access boundaries.

## Stack

- Next.js `16.2.11` (Active LTS security-patched line as of July 2026)
- React `19.2`
- TypeScript
- App Router
- Plain CSS; no chart/UI dependency required for V1

## Run locally

```bash
cd apps/web
npm install
npm run dev
```

Then open `http://localhost:3000`.

## Current UI scope

- model selector for frozen historical candidates;
- explicit placeholders for V3 research variants;
- historical-development aggregate metrics;
- six-fold robustness view;
- V2 champion artifact fingerprint;
- forward-monitoring readiness shell;
- empty forward session ledger designed for a later outcome-blind signal-side adapter;
- V3 parallel research lane.

## Research guardrails

The UI MUST NOT invent or display fresh-forward outcomes, rankings, TP/SL results, or session metrics that have not been authorized and produced by the research runtime.

Current V1 intentionally renders:

- frozen historical benchmark facts already recorded in the repository;
- model/artifact metadata already frozen by the V2 refit;
- `0 / 100 outcomes consumed` because fresh-forward outcomes have not been accessed;
- readiness state as `not evaluated` where the 100-session block has not been evaluated.

The dashboard is not a trading terminal and must not emit `BUY`, `SELL`, `EXIT`, order-routing, or live execution actions.

## Next integration seam

A later backend/API adapter may feed:

1. signal-side session metadata and model ranks without labels/outcomes;
2. H10 maturity/readiness state;
3. one-shot outcome metrics only after the explicit outcome-access gate is authorized and executed.

Keep the display layer separate from research/model code so model generations can be swapped through typed metadata rather than hard-wiring V2 semantics into the UI.
