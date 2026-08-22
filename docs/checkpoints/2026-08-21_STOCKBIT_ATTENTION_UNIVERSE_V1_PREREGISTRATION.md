# Stockbit Attention Universe V1 — Preregistration

Date: 2026-08-21  
Lane: Stockbit Stream prospective acquisition only  
Branch: `audit/stockbit-stream-v2-red-team-v1`  
Status: `PREREGISTERED_NOT_IMPLEMENTED_NOT_LIVE`

## Purpose

Freeze the ticker-selection contract for prospective Stockbit Stream acquisition before implementation and before any sentiment, return, target, IC, model-score, O2, V4-X1, forward-outcome, or forward-counter access.

This document supersedes the current liquidity-only `top 200 prior-session regular value` selection concept for the next implementation candidate. It does not authorize live promotion by itself.

Primary objective:

> Maximize representative and information-rich Stockbit observations under the live Zapi Pro quota while keeping the acquisition rule simple, deterministic, point-in-time safe, and independent of future alpha results.

The capture universe is not the tradable portfolio universe. Small/speculative names may be observed without ever becoming eligible for portfolio construction.

## Frozen daily capacity

For capture date `T`:

- `STRUCTURAL_CORE_SIZE = 120`
- `SOCIAL_HOT_MAX = 30`
- `HIGH_FREQUENCY_SIZE = 150`
- `DISCOVERY_SIZE = 80`

Cadence:

- `pre_open`: 150 high-frequency tickers
- `midday`: 150 high-frequency tickers
- `after_close`: the same 150 high-frequency tickers + 80 discovery tickers

Maximum Stream items per ordinary capture day:

`150 + 150 + 230 = 530`

At 22 capture days this is approximately `11,660` Stream items/month, before rare retries. Live provider acceptance established an account-level monthly limit of 25,000; the existing monthly reserve remains separately enforced.

No additional intraday slot is introduced in V1.

## 1. Structural Core — exactly 120 when source integrity permits

Structural Core must not use Stockbit posts, sentiment, engagement, future returns, labels, model scores, or outcome information.

### 1.1 Market-cap leg

Rank active eligible tickers by prior-completed-session market capitalization:

`market_cap = Close * ListedShares`

Both inputs come from the exact completed IDX `stock-summary` session available before capture. Values must be finite and strictly positive. Invalid market-cap values are excluded from the market-cap leg rather than repaired or inferred.

### 1.2 Persistent-liquidity leg

For each active eligible ticker, compute over the latest 20 completed IDX sessions available before the structural refresh:

`regular_value = Value - NonRegularValue`

Persistent liquidity is:

`median_regular_value_20 = median(valid positive regular_value observations)`

A ticker requires at least 15 valid sessions within the 20-session window to enter the liquidity leg. Nonfinite, negative, or logically impossible values remain fail-closed under the existing numeric-integrity rules.

Recent IPOs with insufficient 20-session history are not force-filled into the liquidity leg. They may still qualify through market capitalization or Discovery.

### 1.3 Deterministic 60/60 construction

The design deliberately avoids a tuned weighted composite score.

1. Take top 60 by market cap.
2. Take top 60 by 20-session median regular value.
3. Form their de-duplicated union.
4. If the union has fewer than 120 tickers, continue down both ranked lists in deterministic alternating order, market-cap candidate then liquidity candidate, skipping duplicates, until 120 are selected.
5. Ticker ascending is the final tie-break inside each source rank.

The same alternating continuation defines an ordered `STRUCTURAL_BACKUP` list beyond rank 120.

If source integrity or eligibility cannot provide 120 valid structural names, the run fails closed; V1 does not silently reduce the core.

### 1.4 Refresh cadence

Structural rankings refresh at most once per ISO week, using only completed IDX sessions available at refresh time. The first valid capture opportunity in a new ISO week may perform the refresh.

No midweek structural reranking is performed merely because a stock becomes active or inactive in price action. This reduces unnecessary universe churn.

A refresh may be repeated after a transient provider failure only under the separately hardened bounded-retry transport rule. Auth/quota failures are not multiplied.

## 2. Social Hot — zero to 30 non-Structural names

Social Hot is a bounded complement, not the primary universe driver.

### 2.1 Why raw daily post counts are prohibited

Core names are observed more often than Discovery names. Ranking by raw accumulated posts or raw accumulated unique authors would therefore create a self-reinforcing sampling bias.

V1 must not use accumulated post count across unequal observation schedules to select Social Hot.

### 2.2 Comparable after-close evidence only

Social Hot for day `T` is determined only from the most recent successful prior `after_close` observation set that:

- occurred strictly before day `T`;
- is no more than 4 calendar days old;
- contains valid raw Stream evidence;
- was already observable before `T` began.

This allows Friday evidence to inform Monday while resetting stale attention after longer closures.

If no valid comparable prior after-close evidence exists, Social Hot is empty and structural backup names fill the unused high-frequency slots.

### 2.3 V1 attention rule

For each non-Structural ticker observed in the qualifying prior after-close set, derive only acquisition telemetry from the returned Stream page:

- returned unique post count;
- source-page span = difference between the newest and oldest parseable `createdAt` values on that page;
- whether the page is at least as deep as the empirically observed provider page cap of 30 posts.

The duration between source timestamps may be used as a relative span even though absolute `createdAt` timezone semantics remain unproven. Absolute point-in-time authority remains the collector's response-receipt timestamp.

A ticker is eligible for `SOCIAL_HOT_V1` only when:

- at least 30 unique posts were returned; and
- all required source timestamps for the span are parseable; and
- `source_page_span <= 24 hours`.

Eligible names are ranked by:

1. shorter source-page span first;
2. ticker ascending tie-break.

Take at most 30 names after excluding Structural Core.

There is no sentiment model, NLP model, LLM, engagement weighting, exponential decay, manual meme-stock whitelist, or return-based tuning in Social Hot V1.

### 2.4 No forced Hot names

If only `H < 30` names satisfy the Hot rule, V1 uses only those `H` names.

The remaining `30 - H` high-frequency positions are filled from `STRUCTURAL_BACKUP` in frozen deterministic order.

Therefore the high-frequency roster remains exactly 150 without relabeling quiet stocks as socially hot.

## 3. Discovery — exactly 80 after-close names

Discovery exists to expose the collector to the long tail, including names that are neither structurally important nor already known to be socially active.

For capture date `T`:

1. Start from the active pinned identity roster.
2. Exclude the 150 high-frequency names.
3. Compute for every remaining ticker:

`discovery_key = SHA256(identity_source_sha256 | T | ticker)`

4. Sort ascending by `discovery_key`, then ticker ascending.
5. Select the first 80.

This is deterministic pseudo-random sampling without replacement within the day. V1 deliberately does not maintain a complex no-repeat state machine. Cross-day distinct coverage and repeat rate will be measured during acquisition QA; they are not tuned using returns or alpha metrics.

If fewer than 80 eligible residual names exist, the run fails closed rather than silently changing the requested sample size.

## 4. Daily roster freeze

Once the high-frequency and discovery rosters for capture date `T` are successfully materialized, membership is frozen for that date.

- `pre_open`, `midday`, and `after_close` must use the same 150 high-frequency membership for day `T`.
- An intraday Stream observation cannot promote a ticker into the same day's high-frequency roster.
- After-close observations may only influence a future capture date.

This prevents within-day lookahead-like selection and makes slot comparisons interpretable.

Execution order inside a roster remains independently deterministic and de-biased from ranking order under the existing SHA256 capture-order rule.

## 5. Provider and PIT contract

V1 preserves the hardened provider rules already established in PR #36:

- exact raw Zapi bytes are archived;
- current Zapi outer `project/timestamp/data` envelope is handled;
- Stockbit `provider` and requested symbol must match;
- collector receipt time is the authoritative prospective availability timestamp;
- source `createdAt` is metadata and may be used for relative page-span telemetry only;
- invalid/unknown/malformed responses fail closed under existing classifications;
- `stock-summary` historical dates must be exact and complete;
- one-page IDX market results must fail closed if `recordsTotal` exceeds returned page completeness until pagination is implemented;
- bounded retry is allowed only for transport failures and provider 5xx, never for auth/quota 4xx;
- every authenticated provider attempt is budgeted as potentially billable;
- Stream is treated as latest-page sampled observation, not as a complete Stockbit firehose.

Live provider acceptance on 2026-08-21 observed:

- Pro monthly limit: 25,000;
- Stream accepted requested counts through 50 but returned at most 30 posts in the tested names;
- count 51 and 100 returned HTTP 400;
- BBCA/GOTO/DADA Stream contract passed;
- exact post-ID dereference passed;
- exact-date historical IDX stock-summary passed on repeat;
- invalid auth returned 401 and unknown symbol returned 404.

Those observations are provider evidence, not promises that the provider can never change. Runtime contract validation remains fail-closed.

## 6. Explicitly prohibited selection inputs

Universe membership must not use:

- future or same-day future returns;
- any target or label;
- historical or prospective IC/performance;
- V2/V3/V4/V4-X1 scores;
- O2;
- protected outcome vault data;
- portfolio positions;
- user manual preference for a ticker after seeing model/return results;
- sentiment polarity or stance classifier output;
- LLM interpretation of Stream content;
- author identity beyond acquisition-integrity telemetry;
- same-day later-slot observations to rewrite earlier/day-frozen membership.

## 7. Implementation acceptance tests required before live use

Implementation remains unauthorized for promotion until adversarial tests cover at least:

1. 60/60 structural dedup and alternating fill.
2. Missing/invalid `ListedShares` and `Close` fail safely.
3. Persistent-liquidity 20-session window and 15-session minimum.
4. No current/future session can enter a structural calculation.
5. Weekly refresh stability across ordinary midweek captures.
6. GOTO-like case: large market-cap / abnormal turnover can remain structurally represented.
7. DADA-like case: non-Structural name can be promoted only from prior observable after-close attention evidence.
8. Core names cannot gain Hot priority merely because they were captured more frequently.
9. Hot eligibility rejects malformed source timestamps and stale evidence.
10. Hot shortfall fills from structural backup, never quiet pseudo-Hot names.
11. Day-frozen high-frequency roster is identical across all three slots.
12. Discovery excludes all high-frequency names and contains exactly 80 unique tickers.
13. Discovery is deterministic for identical inputs/date and changes when date changes.
14. Malformed/stale identity roster fails closed under existing identity gates.
15. Quota-before gate budgets the actual slot-specific planned calls (150/150/230).
16. 401/403/429 stop behavior remains intact.
17. bounded retry does not retry auth/quota failures.
18. capture order remains independent of market-cap/liquidity/social rank.
19. provider page-cap drift does not silently produce false Hot membership.
20. no model/outcome/counter access is introduced anywhere in the selection path.

## 8. Acquisition QA after implementation

Only acquisition-quality telemetry may be reviewed during the initial prospective observation period. Examples:

- unique ticker coverage;
- Discovery repeat rate and cumulative distinct coverage;
- returned Stream page counts;
- source-page spans;
- overlap/new post IDs across slots;
- percentage of pages at the observed 30-post cap;
- high-frequency/Discovery response success rate;
- slot execution duration and observation span;
- Zapi quota usage and retry frequency;
- Hot occupancy (`0..30`) and Hot persistence;
- structural weekly churn.

No return, target, IC, model-performance, or portfolio-outcome metric may be used to tune this universe during acquisition QA.

## 9. Change control

The numerical allocation and selection rules in this document are frozen for the implementation candidate.

If implementation testing discovers an internal contradiction or provider constraint that makes the contract impossible, stop and document the failure. Any substantive redesign must be preregistered in a new checkpoint before live prospective use.

A poor future alpha result is not grounds to rewrite this acquisition universe retroactively.

## 10. Deferred items

This preregistration does not resolve or authorize:

- Cloudflare R2 Bucket Lock / retention / least-privilege token review;
- PR #36 merge/promotion;
- Bulk Jobs transport migration;
- Stockbit stance/sentiment classification;
- LLM labeling;
- alpha feature engineering;
- any model retraining or outcome evaluation.

Those remain separate later steps.

## Current verdict

`ATTENTION_UNIVERSE_V1_PREREGISTERED_IMPLEMENTATION_AND_RED_TEAM_REQUIRED`
