# Stockbit Identity Refresh Source Audit

Date: 2026-08-21  
Branch: `audit/stockbit-stream-v2-red-team-v1`  
Scope: prospective Stockbit acquisition identity roster only  
Status: `PREREGISTERED_LIVE_SOURCE_AUDIT_PENDING_NO_ROSTER_MUTATION`

## Purpose

Resolve the first blocker from the Stockbit Attention Universe adversarial review: the current pinned identity roster is intentionally stale-gated after 35 days, but its lineage originates from local external security-master artifacts. A live cloud collector therefore needs a reproducible current-identity refresh source before production promotion.

This audit is outcome-blind. It must not access sentiment, returns, targets, IC, model scores, O2, V4-X1 outcomes/counters, portfolio outcomes, or protected-forward data.

No live identity CSV or manifest may be replaced by this audit. The audit may only inspect current provider identity/reference data and compare it to the pinned roster.

## Existing anchor

Current repository identity roster:

- path: `config/stockbit_stream_universe_v1.csv`
- pinned manifest: `config/stockbit_stream_universe_v1.json`
- manifest `as_of_panel_date`: `2026-07-31`
- expected current common-stock count: `963`
- CSV SHA is already pinned by the manifest.

## Candidate cloud sources

Two Zapi IDX endpoints are admitted for the audit without choosing a winner in advance:

1. `finance:idx/securities`
   - minimal security-level identity fields;
   - expected fields include `Code`, `Name`, `Shares`, `ListingDate`, `ListingBoard`.
2. `finance:idx/companies`
   - issuer-level listed-company reference data;
   - stock eligibility must be explicit through `EfekEmiten_Saham` rather than inferred from issuer existence alone.

The latest completed `finance:idx/stock-summary` panel is a cross-check only. It is not automatically an identity authority because market-trading presence and current listing identity are different semantics.

## Frozen audit procedure

### A. Current roster validation

- Read the repository CSV directly in GitHub Actions.
- Require valid unique ticker codes under the existing ticker regex.
- Require exactly 963 active rows for this audit anchor.
- Do not rewrite, normalize, or repair the anchor.

### B. Paginated candidate retrieval

For both `securities` and `companies`:

- fetch using pagination (`length=500`, `start=0,500,...`) rather than relying on a single <1000 page;
- require HTTP 200;
- require provider `idx`;
- require the expected dataset identity;
- require stable `recordsTotal` / `recordsFiltered` across every page;
- require the union row count to equal metadata exactly;
- reject duplicate ticker codes across pages;
- preserve SHA-256 of every exact raw response page in audit output;
- use bounded retry only for transport failures or provider 5xx; never retry 401/403/429.

This deliberately proves the pagination primitive needed when IDX crosses 1000 securities.

### C. Candidate semantic validation

For `securities`:

- `Code` must be a valid unique ticker;
- `Name` must be nonblank;
- `ListingDate` must be parseable when present;
- `Shares` and `ListingBoard` are diagnostics, not hard eligibility assumptions until observed.

For `companies`:

- use only rows where `EfekEmiten_Saham is true` for stock-identity comparison;
- `KodeEmiten` must be a valid unique ticker;
- `NamaEmiten` must be nonblank;
- `TanggalPencatatan` parseability is measured;
- do not infer the meaning of numeric `Status` without an independently documented contract.

### D. Cross-set deltas

Produce exact sorted ticker deltas for:

- pinned roster vs `securities`;
- pinned roster vs stock-enabled `companies`;
- `securities` vs stock-enabled `companies`;
- pinned roster vs latest completed `stock-summary`;
- each candidate vs latest completed `stock-summary`.

For every delta ticker, include whatever non-sensitive reference metadata is already present in the retrieved provider rows. Do not silently classify unexplained deltas.

### E. Stability check

Fetch each identity candidate twice in the same run using the same paginated contract.

Record:

- canonical ticker-set SHA for each fetch;
- exact raw-page SHA(s);
- whether the ticker set changed;
- whether row content changed while the ticker set remained stable.

A changing ticker set across immediate repeated reads is a blocker for automatic promotion until explained.

## Decision rule

Possible verdicts:

### `IDENTITY_REFRESH_SOURCE_ACCEPTED`

Only if one candidate has:

- deterministic cloud retrieval;
- complete validated pagination;
- stable immediate ticker set;
- defensible stock-security semantics;
- all material deltas against the pinned roster explained by observable listing/security facts or a separately documented rule;
- enough fields to regenerate `ticker`, company name, and listing date without local-only artifacts.

### `IDENTITY_REFRESH_SOURCE_CONDITIONAL`

Use when the endpoint is technically usable but one or more ticker deltas or semantics remain unresolved. No roster replacement is authorized.

### `IDENTITY_REFRESH_SOURCE_REJECTED`

Use when candidate data is incomplete, unstable, non-paginatable, materially malformed, or lacks defensible stock identity semantics.

## Explicit non-goals

This audit does not:

- modify the current 963-name identity roster;
- modify the 35-day stale gate;
- build Structural Core 120;
- compute market cap or persistent liquidity;
- capture Stockbit Stream;
- use sentiment/NLP/LLMs;
- read any outcome or model-performance data;
- authorize PR #36 promotion.

## Next step after live audit

If a candidate is accepted, a separate implementation step may define how and when a new immutable identity snapshot is materialized and activated relative to the weekly structural snapshot. If conditional, resolve the exact delta semantics first.
