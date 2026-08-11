# Zapi Alternative-Endpoint Follow-up — Independent Review

Date: 2026-08-11 (Asia/Jakarta)
Reviewed runtime commit: `077748ad59fcd9b048c9e3de7bab25e397439895`
Branch: `data/idx-open-backfill-zapi-alt-endpoints-audit-v1`

## Decision

**`ZAPI_MONTHLY_QUOTA_EXHAUSTED_TRADINGVIEW_EVIDENCE_PRESERVED_INVESTING_UNASSESSED`**

The quota-aware follow-up is accepted as a valid fail-closed runtime. The single diagnostic 429 did not include the documented JSON `window`, but the returned headers are sufficient to strongly identify the monthly billable quota as exhausted:

- `X-RateLimit-Remaining-Minute = 100`;
- `X-RateLimit-Remaining-Month = 0`;
- no `Retry-After`;
- no plan-expired header.

Current official Zapi documentation defines `X-RateLimit-Remaining-Minute` as requests left in the current minute and `X-RateLimit-Remaining-Month` as billable requests left this month. It also states that the free tier has 2,000 billable requests/month and that quota `resetAt` is the first day of the next month in UTC. Therefore no further billable Zapi call is authorized on this key until monthly quota resets or the user explicitly chooses a paid upgrade.

This is a quota/access decision, not a price-quality rejection.

## TradingView evidence status

Preserve the existing bounded evidence unchanged:

- 61 recovery candidates already passed the frozen exact H/L/C + positive/in-range Open gate;
- 37 are from `RESIDUAL_PROVIDER_GAP`;
- 24 are from `RESIDUAL_HLC_MISMATCH`;
- year counts: 2021=10, 2022=18, 2023=20, 2024=13;
- largest ticker concentration: HKMU=5; BAYU/CBMF/JSKY=2 each;
- no candidate is promoted into the panel from this review.

TradingView remains **promising but incomplete** because the prior audit was materially censored by rate limits and the 1000-candle history window. The 61 candidates are valid evidence but do not authorize full-universe recovery.

## Investing status

Investing remains **unassessed**, not rejected. No Investing search identity ever returned usable data in the completed audit because all attempts occurred after Zapi billable capacity had effectively been exhausted. There were zero verified identities and zero historical requests.

Do not interpret that as an Investing data-quality result.

## Runtime integrity accepted

- frozen sample remains 240 rows / 206 tickers;
- sample SHA remains `9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`;
- prior runtime manifest remains `b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80`;
- follow-up manifest is `87e40d23e02f7557d8a90120577ff68fd3e3567ee339c856386c141fdb61802d`;
- immutable panel SHA remains `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- focused tests: 9 passed;
- full pytest: 251 passed, 5 existing warnings;
- prior successful TradingView tickers were not refetched;
- only one follow-up billable request was made before fail-closed stop.

## Next authorization

Zapi network work is paused on the current free quota until reset or explicit paid-upgrade authorization.

The next useful work should not burn additional Zapi requests. Allowed directions are:

1. offline analysis of the already accepted 61 TradingView candidates and provider disagreements;
2. independent Source-3 screening/pilot using a separate provider under a separately frozen spec;
3. resume the 70 rate-limited TradingView tickers and first Investing identity audit only after Zapi quota reset, preserving prior artifacts and retrying only unresolved tickers.

No new Zapi account/key may be created for the purpose of bypassing the monthly limit.

## Not authorized

- no bulk TradingView backfill;
- no Investing verdict;
- no panel write;
- no execution-grade promotion;
- no corporate-action repair;
- no modelling/Ranking/PIT-sector work in this lane;
- no execution PnL;
- no quota-bypass account/key rotation;
- no main merge.
