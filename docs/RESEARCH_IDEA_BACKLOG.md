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
