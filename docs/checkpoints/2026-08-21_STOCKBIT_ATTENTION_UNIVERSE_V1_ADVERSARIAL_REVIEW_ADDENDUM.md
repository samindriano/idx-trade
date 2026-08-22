# Stockbit Attention Universe V1 — Adversarial Review Addendum

Date: 2026-08-21  
Parent review: `2026-08-21_STOCKBIT_ATTENTION_UNIVERSE_V1_ADVERSARIAL_REVIEW.md`  
Status: `ADDITIONAL_BLOCKER_RECORDED_NO_IMPLEMENTATION`

## Additional blocker: one-page market assumptions are too close to exhaustion

The parent review is strengthened with one additional blocker before V1.1 implementation.

Live provider acceptance observed `stock-summary` `recordsTotal=963` for 2026-08-20. Zapi documents `length` max 1000 with `start` pagination. The current V2 intentionally fails closed when `recordsTotal != returned rows`, which is safe today but leaves only 37 names of one-page headroom.

For a long-lived prospective collector, treating `>1000` as a future hard stop is unnecessary because the provider already exposes pagination.

V1.1 therefore must include a reusable paginated IDX panel reader before live promotion:

1. request deterministic pages using `start` + bounded `length`;
2. verify every page has provider `idx`, expected dataset, and exact requested date where applicable;
3. require stable `recordsTotal` / `recordsFiltered` across pages;
4. reject duplicate `StockCode` / identity codes across pages;
5. require the union row count to equal the declared total/filtered count;
6. hash and archive each exact raw page plus a canonical combined-panel manifest;
7. preserve bounded retry semantics for transport/5xx only; never multiply auth/quota failures;
8. test boundary cases at 999, 1000, 1001, multi-page duplicates, missing second page, changing total between pages, and page-order changes.

The same pagination primitive should be available to the future cloud identity-refresh audit because Zapi `securities` / `companies` are also market-wide lists and should not inherit a silent one-page ceiling.

This does **not** authorize replacing the current pinned identity roster. Zapi currently documents the `securities` endpoint as a listed-security source, but its live/current membership must first be delta-audited against the existing pinned 963-name common-stock roster before it becomes canonical.

## Decision impact

The high-level 120/30/80 allocation is still not rejected. The implementation block remains in force.

Required order remains:

`adversarial review -> V1.1 amendment -> second design review -> implementation tests -> live promotion review`

No model, sentiment, outcome, IC, O2, V4-X1, portfolio outcome, or forward-counter access is authorized by this addendum.
