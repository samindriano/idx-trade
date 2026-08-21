# Stockbit Attention Universe V1 — Adversarial Design Review

Date: 2026-08-21  
Branch: `audit/stockbit-stream-v2-red-team-v1`  
Scope: prospective acquisition design only  
Status: `RED_TEAM_REVIEW_FAIL_AMENDMENT_REQUIRED_NO_IMPLEMENTATION`

## Decision

Do **not** implement the 2026-08-21 `Stockbit Attention Universe V1` preregistration as written yet.

The high-level allocation (`120 Structural Core + up to 30 Social Hot + 80 Discovery`, with 150/150/230 slot sizes) remains plausible and is not rejected by this review. The failure is in enforcement, lineage, and operational semantics: several rules that look frozen on paper are not yet guaranteed to remain the same across independent cloud jobs, provider drift, partial captures, identity refreshes, or weekly structural refreshes.

No sentiment, return, target, IC, model score, O2, V4-X1, forward outcome, portfolio outcome, or forward counter was accessed in this review.

## Severity summary

### Blockers before implementation

1. **Daily roster freeze is not artifact-enforced.**
   The preregistration says the same high-frequency membership must be used across pre-open, midday, and after-close, but it does not require one immutable daily roster artifact to be materialized once and re-read by later jobs. Independent recomputation is not a real freeze. Identity source changes, provider changes, or implementation differences could silently produce different memberships.

2. **Weekly structural refresh is underspecified operationally and must not sit on the 08:47 critical path.**
   Persistent liquidity requires 20 completed market-wide `stock-summary` panels. Fetching/discovering 20 sessions serially immediately before a Stream slot adds avoidable latency and provider-failure exposure before any Stockbit observation begins. Structural state must be materialized separately and referenced by hash during capture.

3. **Identity roster expiry has no cloud-side refresh contract.**
   Current production runner fails closed after 35 days, while the pinned identity roster is `as_of_panel_date=2026-07-31` and originates from local external security-master artifacts. Without an explicit refresh procedure, a successful live collector is designed to stop after several weeks. Zapi exposes IDX `securities` / `companies`, but their current universe must be audited against the existing 963-name identity roster before they are admitted as a replacement source.

4. **Social Hot evidence lineage is not sufficiently frozen.**
   `most recent successful prior after_close observation set` is ambiguous unless success means a specific immutable `DATA_READY` manifest and the exact evidence artifact/hash is referenced by the next daily roster. A partial after-close run must not create an asymmetrically observed Hot candidate pool.

5. **Provider page-cap drift can silently change Hot semantics.**
   V1 says `at least 30` posts, while live evidence only established an observed cap of 30 under `count=50`. If the provider later returns 40 or 50, a 30-post threshold no longer means page saturation. If it later caps at 20, Hot disappears. V1 needs an explicit page-cap contract and a fail-closed Hot-disabled state on drift.

### High-severity robustness gaps

6. **Pinned posts can poison source-page span.**
   Stream items expose `isPinned`. One old pinned post inside a latest-page response can make an actively discussed ticker look quiet. V1 currently has no pinned-page rule. Conservative V1 behavior should make a page containing pinned content ineligible for Hot unless a separately specified non-pinned span rule is adopted.

7. **Single-author spam can hijack Social Hot.**
   Thirty posts in a short span can be produced by one account. Ranking only by page span confuses posting frequency with breadth of social attention. Existing normalization already preserves a pseudonymous author identity, so a minimal anti-concentration gate can be enforced without new provider calls or NLP.

8. **Structural-backup filling needs explicit uniqueness semantics.**
   When `H < 30`, structural backup must skip not only Core duplicates but also any selected Hot ticker. The final high-frequency roster must prove exactly 150 unique tickers.

9. **Provider provenance should be enforced at the capture boundary, not only in the current REST client.**
   Current production runner uses `V2ZapiClient`, which rejects a wrong/missing Stockbit provider before returning to `capture_stream_v2`. However `capture_stream_v2` itself still parses returned raw bytes with the legacy parser. A future alternate transport (including a Bulk Jobs adapter) could bypass the client-side provenance check. The strict V2 parser must be applied at the archive/capture boundary as defense in depth, with provider-mismatch evidence handled explicitly.

### Accepted tradeoffs / non-blockers

10. **Pure-random Discovery is slow for ephemeral long-tail events, but this is an explicit tradeoff.**
    With roughly 963 active identities and 150 high-frequency names, the residual pool is about 813. Sampling 80/day gives about a 9.84% daily inclusion probability for an ordinary residual ticker. Under an idealized stable residual pool, expected first observation is about 10.2 capture days and median about 6.7 days; expected cumulative distinct coverage is roughly 64.5% after 10 days, 87.4% after 20, and 95.5% after 30. Therefore V1 can miss a short-lived small-cap event. Given the stated priority on structurally important/liquid names and the desire to avoid overengineering, this is acceptable for V1 if recorded honestly.

11. **The 60/60 market-cap/liquidity construction is arbitrary but scientifically acceptable.**
    It is simple, outcome-blind, understandable, and avoids tuning a composite score. No evidence in this review justifies adding Stockbit follower counts, index weights, NLP, or another structural leg before acquisition begins.

12. **`Close * ListedShares` is acceptable as a structural market-cap proxy for V1.**
    Zapi IDX `stock-summary` exposes both fields in the same historical session. Exact free-float/index-weight semantics are not needed for this acquisition ranking. Invalid/nonpositive fields must remain excluded/fail-closed as preregistered.

13. **A four-calendar-day Hot evidence freshness rule is conservative but acceptable.**
    It covers Friday-to-Monday and common one-day holiday extensions. Longer closures reset Hot and fall back to structural backup, which is safer than inventing a calendar in this lane.

14. **Source `createdAt` can be used for relative within-page span only.**
    Absolute timezone remains unresolved, but differences among timestamps generated under the same source convention are usable as acquisition telemetry. Collector response-receipt time remains the PIT authority.

15. **Quota capacity is not the limiting factor at the proposed allocation.**
    The safer ordinary-month planning number is 23 capture weekdays, not 22: `530 * 23 = 12,190` Stream items. This remains far below the live 25,000 monthly quota, leaving substantial headroom for rare retries and small support calls. Capture-window latency and synchrony are more relevant than quota for deciding whether to enlarge the high-frequency panel.

## Required V1.1 amendment before code

The next preregistration amendment should add, at minimum, the following contracts.

### A. Immutable selection lineage

- Materialize one immutable **weekly structural snapshot** with:
  - ISO week / effective dates;
  - identity roster SHA;
  - exact 20 completed sessions used;
  - SHA for every market-wide source panel;
  - market-cap and median-liquidity ranks;
  - Core 120 and ordered structural backup;
  - deterministic selection-rule version.
- Materialize one immutable **daily roster artifact** before the first successful Stream capture of date T.
- The daily roster contains exactly:
  - Structural Core 120;
  - selected Social Hot 0..30 and their evidence lineage;
  - structural backup fillers;
  - final high-frequency 150;
  - Discovery 80;
  - identity SHA, structural snapshot SHA, prior-attention evidence SHA, rule version, and roster SHA.
- Later slots must read/verify the same daily-roster bytes/hash. They must never silently recompute membership when a daily artifact already exists.
- If pre-open misses before roster materialization, the first later valid slot may materialize T once; subsequent slots must reuse it.

### B. Structural refresh off the Stream critical path

- The 20-session source window must be materialized before the Stream capture path that consumes it.
- Initial activation may perform a bounded outcome-blind historical support fetch of exact IDX stock-summary sessions solely for universe construction.
- Routine capture jobs consume the already-materialized weekly structural snapshot; they do not perform a 20-panel refresh inside the ticker Stream loop.
- Missing/corrupt weekly structural state blocks capture rather than falling back to a different ad-hoc ranking.

### C. Identity refresh prerequisite

Before production promotion, separately audit a cloud-reproducible identity refresh source and delta against the existing pinned 963-name roster. Do not silently replace the current local-derived identity lineage merely because Zapi `securities`/`companies` exists.

Once accepted, identity and structural activation should be coordinated so that an identity SHA cannot change silently in the middle of a frozen structural week.

### D. Social Hot evidence contract

- Hot may be derived only from an immutable prior `after_close` artifact whose parent slot status is `DATA_READY` for the complete frozen after-close roster.
- Create a small content-free/pseudonym-only **attention evidence artifact** at after-close while the raw responses are already available. It should record per ticker at least:
  - requested symbol;
  - unique post IDs / count;
  - unique pseudonymous-author count;
  - pinned-item count;
  - parseable source-time count;
  - min/max raw source time and page span;
  - provider-page-depth contract/version;
  - parent manifest SHA.
- A partial parent run produces no Hot-authorizing evidence for the next day.
- The next daily roster references the exact attention-evidence SHA.

### E. Conservative V1 Hot integrity gates

Proposed, not yet frozen:

- requested Stream count remains 50;
- Hot page must return exactly the currently accepted saturated-page count of 30;
- every required source time must parse for relative span;
- any `isPinned=true` item makes that ticker ineligible for V1 Hot;
- require a modest minimum number of unique pseudonymous authors to prevent one-account bursts from becoming Hot; exact threshold must be fixed in the amendment before implementation;
- retain `source_page_span <= 24h` as a broad floor and rank eligible names by shorter span, with deterministic tie-breaks;
- if provider acceptance detects a page-cap contract change, Social Hot becomes disabled and backup fills the 30 positions until a new source contract is reviewed. Structural/Discovery capture need not automatically stop if their Stream schema remains valid.

### F. Strict provenance at archive boundary

`capture_stream_v2` (or its successor) must apply the strict Stockbit provider/symbol parser to raw returned bytes even if the current client already validates provider provenance. Alternate transports must satisfy the same raw-response contract.

### G. Quota and slot invariants

- pre-open planned Stream items = exactly 150;
- midday = exactly 150;
- after-close = exactly 230;
- ordinary 23-weekday planning baseline = 12,190 items/month before retry/support overhead;
- live `get_usage` remains the quota authority;
- monthly reserve remains fail-closed;
- retries remain bounded and never multiply 401/403/429.

## Additional adversarial tests required in V1.1

In addition to the original 20 proposed tests, add tests that prove:

1. second/later slots cannot recompute a different daily roster when a roster artifact exists;
2. same daily roster hash is required across all slots;
3. partial after-close cannot authorize next-day Hot;
4. provider page-cap increase/decrease disables Hot rather than silently changing semantics;
5. pinned old post cannot make or unmake Hot through an unintended span calculation;
6. one-author 30-post spam burst cannot obtain Hot under the finalized anti-concentration rule;
7. Hot + structural-backup fill yields exactly 150 unique names;
8. identity SHA cannot change midweek without an explicit structural activation transition;
9. missing weekly structural artifact blocks rather than recomputes inside a Stream slot;
10. strict provider provenance is enforced at the capture/archive boundary even with a non-V2 custom client/transport;
11. daily Discovery is exactly 80 unique residual names and empirical deterministic simulation matches expected coverage behavior;
12. 23-weekday quota plan plus bounded support overhead remains below the live quota/reserve gate.

## Current conclusion

The allocation concept survives the attack, but **V1 as written fails design review** because its freeze is not yet physically enforceable and its identity/Hot lineage can drift or bias silently.

Next action is **design amendment only**. Do not implement the Attention Universe until a V1.1 preregistration resolves the blockers above and is itself reviewed once more.

Cloudflare Bucket Lock/token-scope review remains separately deferred; no storage-layer WORM claim is made here.
