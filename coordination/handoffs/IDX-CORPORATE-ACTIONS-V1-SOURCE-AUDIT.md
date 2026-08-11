# Handoff — Corporate Actions V1 Source Audit

from: Codex MAIN  
to: ChatGPT reviewer / next Corporate Actions V1 task  
task_id: IDX-CORPORATE-ACTIONS-V1-SOURCE-AUDIT  
model_used: GPT-5.6 Luna xhigh with two read-only Orchestra explorers  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `44c06fc6376342b5e66bae45e5fc4c0eda1f1a40`  
branch: `data/corporate-actions-v1`  

## Scope

Bounded official IDX/Zapi source discovery and raw-price diagnostic for
2021-01-01 through 2026-07-31. No adjustment, model, outcome, or unrelated
lane work.

## Result

Verdict: `CONDITIONAL_PASS_SOURCE_DISCOVERY_REVISION_SENSITIVE_NO_CANONICAL_PRICE_ADJUSTMENT`.

Official `ListingActivity/GetIssuedHistory` returned 535 rows with complete
response counts. Zapi `/v1/finance:idx/raw` returned the exact same ordered
535-row upstream payload. Direct raw SHA:
`24ec30beabddda2053f825d06ef8b03de0df1ef727330724b6a6ab1bd661afc8`; Zapi
raw SHA:
`e93f86cc51b43071464226f7ac94480f41a7fa396e3a3d40e5258c1a5c683006`.

Inventory: 56 stock splits, 0 reverse stocks, 64 HMETD, 44 without HMETD,
13 bonus, 7 stock dividend, 21 capital reductions, 7 mergers, 2 ESOP/MSOP,
and 3 mandatory convertibles. Strict positive stock-split terms exist for 40
rows / 39 logical ticker-date events; 16 rows are placeholders or invalid.

The official field `TanggalPencatatan` is not promoted to
`market_effective_date` without an explicit first-session/ex-date contract.
Type-specific terms are also incomplete in the listing-history response.
Zapi company-announcement metadata found official attachment URLs for ASDM,
BBNI, and BUAH, but direct PDF retrieval was HTTP 403 in this runtime; no
error page was promoted as evidence.

Revision control is a blocker for immutable completeness: a later live query
through 2026-08-11 returned 549 rows, and the current query for
2021-04-29..2026-07-31 returns 519 rows / 54 stock splits. The older persisted
1260 CSV contains 55 rows and an `SCMA / 2021-10-29` split absent from the new
query. `recordsTotal == returned rows` is therefore only a capture-level page
completeness check.

Raw 1260-panel diagnostic: 40 strict split rows had files; 38 had both
adjacent observations; 0 matched the expected mechanical post-price ratio
within 10% or 20% using the source date. No prices were rewritten.

## Files changed

- `docs/CORPORATE_ACTIONS_V1_SPEC.md` — status only;
- `docs/checkpoints/2026-08-11_CORPORATE_ACTIONS_V1_SOURCE_AUDIT.md`;
- this handoff.

Raw captures and audit output remain outside Git under
`D:\Documents\Project\idx-trade-corporate-actions-20260811`.

## Validation

- focused: `python -m pytest tests/test_corporate_actions.py -q` — 8 passed;
- full: `python -m pytest -q` — 479 passed, 0 failed, 3 existing pandas
  FutureWarnings, 20.98s.

## Next safe action

Reconcile a bounded set of official issuer/listing attachments to establish
market-effective date and type-specific terms, starting with the 16 incomplete
stock-split rows and representative HMETD/bonus/stock-dividend records. Keep
the strict canonicalizer fail-closed and do not adjust the price panel until
those semantics are proven.
