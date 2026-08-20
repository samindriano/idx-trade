# IDX Trade — Research Idea Backlog

Purpose: keep low-priority hypotheses discoverable by future ChatGPT/Codex research audits.

**Important:** entries here are ideas only. They are **not active lanes, preregistrations, experiment authorization, or priority changes**. Before doing material work, read `coordination/TEAM_STATUS.md` and follow the normal scientific/coordination gates.

## PARKED — Auction / effort-vs-result proxies

Recorded: 2026-08-21  
Priority: low / opportunistic  
Status: `PARKED_IDEA_ONLY`

Source inspiration: Chris Kmer day-trading discussion — https://youtu.be/PL7LKUsCgIQ

Potential quant translation for future alpha-idea search:

- **Effort vs result / failed participation** is the most interesting hypothesis family. Test OHLCV-safe proxies such as abnormal-volume × wick/recovery behavior, failed-breakout scores, gap rejection, range-expansion per unit volume, and other volume-price-efficiency measures.
- **Structural price location** is a secondary family: rolling-range percentile, ATR extension, pullback depth, and distance from VWAP / recent breakout / relevant price structure. Do not treat discretionary Fibonacci levels as assumed truth; any implementation must be independently tested.
- **Intraday confirmation / timing** belongs in a separate future entry/execution layer, not automatically inside the medium-horizon alpha ranker. Only consider genuine order-flow / absorption features if defensible intraday tick, trade-side, or order-book data becomes available.
- **Selective participation / abstention** conceptually maps to reliability/uncertainty or eligibility gating, but must not modify the existing frozen reliability lane without a new contract.
- **GEX / US options-dealer gamma mechanics are not a current IDX priority.** Do not force-transfer them to Indonesian equities without a separate evidence-backed reason.

Suggested future use: when an agent is explicitly searching for genuinely new alpha or execution hypotheses, it may include this family in the candidate pool, then preregister and test it like any other hypothesis. Do not automatically start it merely because this note exists.

## PARKED — Stockbit behavioral sentiment / retail emotional excess

Recorded: 2026-08-21  
Priority: medium / opportunistic data capture  
Status: `PARKED_IDEA_ONLY`

Source / acquisition lead: Zapi `finance:stockbit` Stream endpoint — https://zpi.web.id/api/finance/stockbit

Core observation / hypothesis:

- Stockbit community behavior appears qualitatively very different across market states: deep-red sessions can produce anger, fear, capitulation, despair, or hopelessness; strong-green sessions can produce euphoria, FOMO, profit-flexing, extreme confidence, and apparent proliferation of paid classes / guru behavior.
- The interesting alpha question is **not** generic positive-vs-negative sentiment. Test whether the *excess emotional response relative to what price/market conditions would normally imply* contains incremental predictive information beyond the existing clean price-state / market-context alpha.
- Treat this as a behavioral-finance hypothesis, not an assumed contrarian rule. Extreme despair could predict reversal, continuation, or nothing; extreme euphoria could predict continuation first and reversal later. Direction and horizon must be preregistered and measured rather than imposed.

Potential post-level labels / representations:

- optimism / pessimism;
- anger / frustration;
- fear;
- despair / hopelessness;
- capitulation language;
- euphoria / overconfidence;
- FOMO;
- profit-flex / screenshot-cuan behavior;
- `guru_mania` / class-selling / premium-group / sudden-expert behavior;
- denial;
- disagreement / polarization;
- attention / post intensity;
- user diversity and anti-spam weighting;
- engagement such as likes / replies where defensible;
- image-derived behavioral cues only if provenance, privacy, storage, and licensing/terms constraints are acceptable.

Potential ticker-date or market-date features:

- mean / median emotion scores;
- emotion shares and extreme-tail shares;
- change / acceleration over 1D/5D windows;
- attention z-score and unique-user count;
- disagreement / entropy;
- despair extremity;
- euphoria extremity;
- profit-flex share;
- `guru_mania` share;
- stock-specific sentiment percentile versus other tickers;
- market-wide Stockbit behavioral state indices.

Most important research formulation:

`Retail Emotional Excess = observed Stockbit behavioral state - expected behavioral state conditional on contemporaneous price/market information`

Possible controls should include the existing information set where appropriate: stock return, market return, breadth, volatility, volume / traded-value state, and existing V4-X1 alpha/context. This is intended to test whether Stockbit behavior adds **orthogonal information**, rather than merely rediscovering that people are happy when prices rise and angry when prices fall.

Potential model role:

1. **Stock-specific behavioral alpha** for cross-sectional ranking is the most interesting path.
2. **Market-wide behavioral regime/context** could be a separate contextual input.
3. **Reliability / crowding overlay** is another possibility: e.g. strong V4-X1 alpha accompanied by extreme euphoria may behave differently from strong V4-X1 alpha accompanied by disbelief/pessimism.
4. Do not assume a standalone sentiment model must beat V4-X1; the more realistic target is incremental clean OOS information or useful conditional/extreme-state behavior.

Acquisition feasibility as of 2026-08-21:

- Zapi documents `GET /v1/finance:stockbit/stream` for latest community posts by `symbol`, with optional `count`.
- Documented response fields include post `id`, `content`, `createdAt`, `username`/`fullName`, likes, dislikes, replies, images, and flags such as `isPro`, `isPinned`, and `isOfficial`.
- Zapi also documents per-post and public-user endpoints that may support richer metadata.
- The currently documented Stream interface does **not** show a historical date range, cursor, or pagination contract suitable for a defensible 2018–2026 backfill. Therefore the realistic first assumption is **prospective append-only capture**, deduplicated by post ID, unless a separate historical-access audit proves otherwise.

Guardrails / future use:

- Do not start acquisition or model testing automatically from this note.
- Before any material work, read latest `coordination/TEAM_STATUS.md`, claim a non-conflicting lane, audit Stockbit/Zapi terms and data-handling constraints, and preregister hypotheses before outcome inspection.
- Keep raw capture timestamps and source timestamps so PIT semantics are defensible.
- Avoid user-level profiling as the research objective; aggregate behavior at ticker/time or market/time level unless a clearly justified, policy-compliant research reason exists.
- Benchmark every candidate against the existing clean V4-X1 information set; generic sentiment that merely tracks contemporaneous returns is not considered new alpha.

Suggested future trigger: revisit when explicitly searching for new orthogonal alpha families, or when there is capacity to start a prospective Stockbit Stream archive without interfering with higher-priority active research lanes.
