# Research checkpoint — PIT historical sector mapping as a new-information research direction

Date: 2026-08-11 (Asia/Jakarta)
Status: `RESEARCH_DIRECTION_RECORDED_NOT_AUTHORIZED`
Branch: `research/idx-ranking-v2-spec-v1`

## Why this checkpoint exists

Path Risk V2 is closed fail-close and the final V3-B Structure-Lite alpha ranker remains frozen. The next useful research work should therefore avoid post-result rescue/tuning of already-viewed hypotheses and instead look for genuinely new information that was not previously available to the model.

A strong candidate is **point-in-time historical sector classification**.

This is not a new concept for the project. The IDX data foundation has already used point-in-time reasoning for identity, listing/tradability state, market-data availability, and corporate-action handling. The missing piece is specifically a **PIT-safe historical sector map** that can answer, for each ticker and signal date, which sector classification was valid and knowable at that time.

Ranking V2 had already identified sector-relative features as potentially useful, but explicitly deferred them because a PIT-safe historical sector mapping did not exist. V3-D Sector Relative later remained blocked for the same reason. This checkpoint records the idea as a future research direction rather than silently losing it after the Path Risk line closed.

## Point-in-time requirement

For a signal at date `t`, the model may only use the sector assignment that was effective and knowable at `t`.

A present-day sector label must not be backfilled across all historical dates.

Conceptual effective-dated schema:

```text
ticker | effective_from | effective_to | sector_code | source_ref | observed_at
```

The exact production schema is not frozen here. Any future implementation must establish source provenance and the distinction between an effective date and the date the classification became available to the research system.

## Why this is a genuinely new information family

The frozen V3-B model already contains stock-level, market-state, cross-sectional, and Structure-Lite information. A PIT sector layer could add information such as:

- stock return minus same-sector median return;
- stock momentum minus same-sector momentum;
- stock volatility relative to same-sector peers;
- stock volume/liquidity relative to same-sector peers;
- sector breadth / participation context;
- sector-relative rank rather than market-wide rank alone.

Example intuition:

```text
stock 20d return          = +4%
market median 20d return  = +3%
sector median 20d return  = -2%

market-relative return = +1%
sector-relative return = +6%
```

The +6% sector-relative information is materially different from simply retuning V3-B on the existing 33-feature information set.

## Data/research gates before any model experiment

Any future PIT-sector work should fail closed unless all of the following are established:

1. historical sector source(s) and provenance are explicit;
2. ticker identity joins are point-in-time safe;
3. effective-date semantics are defined;
4. observation/availability timing is defined where relevant;
5. conflicting or ambiguous classifications are surfaced rather than silently resolved;
6. coverage across the frozen historical research window is measured;
7. missing coverage cannot silently inherit the current sector;
8. corporate/reclassification events are represented as effective-dated changes;
9. the resulting mapping and feature table are hash-pinned before any outcome-bearing experiment.

Only after the data layer passes a separate review should a sector-relative model family be preregistered with frozen features, folds, metrics, and gates.

## Research boundary

This checkpoint **does not authorize**:

- reopening or modifying the final V3-B model;
- running V3-D or any new sector-relative candidate now;
- using present-day sector labels historically;
- accessing fresh-forward realized outcomes;
- touching Path Risk F5/F6;
- creating PR-004 or another Path Risk rescue;
- alpha+risk integration, calibration rescue, sizing, execution-PnL, paper trading, or live trading.

It records a promising next research direction only.

## Suggested future sequence

```text
PIT sector source research
        ↓
effective-dated sector map
        ↓
coverage / provenance / leakage audit
        ↓
freeze sector-relative feature family
        ↓
separate preregistered historical development experiment
        ↓
independent review
```

The preferred principle is: **add a genuinely new information set first, then resume model research; do not keep squeezing the same historical information set after repeated closed experiments.**
