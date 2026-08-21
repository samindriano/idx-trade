# Stockbit Identity Refresh Source Audit

Date: 2026-08-21  
Branch: `audit/stockbit-stream-v2-red-team-v1`  
Scope: prospective Stockbit acquisition identity roster only  
Status: `PREREGISTERED_LIVE_SOURCE_AND_LISTING_EVENT_OVERLAY_AUDIT_PENDING_NO_ROSTER_MUTATION`

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

Two Zapi IDX endpoints remain admitted as base identity candidates without choosing a winner in advance:

1. `finance:idx/securities`
   - security-level identity fields;
   - expected fields include `Code`, `Name`, `Shares`, `ListingDate`, `ListingBoard`.
2. `finance:idx/companies`
   - issuer-level listed-company reference data;
   - stock eligibility must be explicit through `EfekEmiten_Saham` rather than inferred from issuer existence alone.

The latest completed `finance:idx/stock-summary` panel remains a cross-check only. It is not automatically an identity authority because market-trading presence and current listing identity are different semantics.

### Preregistered listing-event overlays

Before inspecting their live payloads, the audit is extended to the newly exposed IDX listing-event endpoints:

- `finance:idx/delistings`
- `finance:idx/new-listings`
- `finance:idx/ipo` (IPO & relisting)

These endpoints are **candidate overlays**, not automatically accepted authorities. Their purpose is to test whether a current base security master can be transformed into a defensible current common-stock roster without ticker-specific hard-coding.

The frozen intended semantics are:

- a validated delisting event effective on or before the roster as-of date may remove a ticker from the base set;
- a validated new-listing / IPO / relisting event effective on or before the roster as-of date may add or corroborate a ticker, subject to common-stock/security-type eligibility;
- events after the roster as-of date must not affect that snapshot;
- an event endpoint is not allowed to override ambiguous security type, malformed ticker, or contradictory dates silently;
- if event payload semantics are insufficient to determine effective listing status, the result remains conditional rather than inventing a rule after observing deltas.

No exact field names, pagination schema, or dataset metadata are assumed for these new endpoints until the live structural probe observes them. The first live run must therefore record payload shape and relevant fields before any parser is promoted.

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

### D. Listing-event structural probe

For `delistings`, `new-listings`, and `ipo`:

- perform bounded authenticated live reads in GitHub Actions;
- record HTTP status, exact raw-response SHA-256, outer/unwrapped object shape, dataset/provider metadata when present, total/count metadata when present, and a small non-sensitive field-name/sample summary;
- explicitly search returned rows/items for `CNTX`, `CNTB`, and `GOTOM` because they are already known identity deltas from the base audit;
- do not fail the whole audit merely because a newly documented endpoint uses a different pagination envelope than `securities`/`companies`; structural discovery is the first step;
- never treat a 404/unsupported route as absence of delisting events—it means only that the candidate endpoint is unavailable under the tested contract.

After payload structure is observed, a parser may be added only if its field semantics are explicit enough to implement the frozen as-of rules above.

### E. Cross-set deltas

Produce exact sorted ticker deltas for:

- pinned roster vs `securities`;
- pinned roster vs stock-enabled `companies`;
- `securities` vs stock-enabled `companies`;
- pinned roster vs latest completed `stock-summary`;
- each candidate vs latest completed `stock-summary`.

For every delta ticker, include whatever non-sensitive reference metadata is already present in the retrieved provider rows. Do not silently classify unexplained deltas.

If listing-event overlays become structurally admissible, additionally report the reconstructed as-of set and exact additions/removals relative to both base candidate and pinned roster. Do not activate it automatically.

### F. Stability check

Fetch each base identity candidate twice in the same run using the same paginated contract.

Record:

- canonical ticker-set SHA for each fetch;
- exact raw-page SHA(s);
- whether the ticker set changed;
- whether row content changed while the ticker set remained stable.

A changing ticker set across immediate repeated reads is a blocker for automatic promotion until explained.

## Decision rule

Possible verdicts:

### `IDENTITY_REFRESH_SOURCE_ACCEPTED`

Only if a reproducible construction has:

- deterministic cloud retrieval;
- complete validated base pagination;
- stable immediate base ticker set;
- defensible common-stock/security semantics;
- defensible effective-date semantics for every listing-event overlay actually used;
- all material deltas against the pinned roster explained by observable listing/security facts or the frozen event rule;
- enough fields to regenerate `ticker`, company name, listing date, and current listed/not-listed status without local-only artifacts or ticker-specific hard-coding.

### `IDENTITY_REFRESH_SOURCE_CONDITIONAL`

Use when the base endpoint is technically usable but one or more ticker deltas, security-type rules, or listing-event semantics remain unresolved. No roster replacement is authorized.

### `IDENTITY_REFRESH_SOURCE_REJECTED`

Use when candidate data is incomplete, unstable, non-paginatable, materially malformed, or cannot support defensible current identity semantics even with the preregistered event overlays.

## Explicit non-goals

This audit does not:

- modify the current 963-name identity roster;
- modify the 35-day stale gate;
- build Structural Core / Social Hot / Discovery tiers;
- compute market cap or persistent liquidity;
- capture Stockbit Stream;
- use sentiment/NLP/LLMs;
- read any outcome or model-performance data;
- authorize PR #36 promotion.

## Next step after live audit

If the construction is accepted, a separate implementation step may define how and when a new immutable identity snapshot is materialized and activated relative to the weekly structural snapshot. If conditional, resolve the exact remaining semantics first.
