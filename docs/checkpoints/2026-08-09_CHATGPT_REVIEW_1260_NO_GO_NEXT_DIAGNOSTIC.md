# ChatGPT independent review — 1260 NO-GO and next diagnostic

Date: 2026-08-09

Branch reviewed: `data/idx-data-002c`

Runtime/result commit reviewed: `4230699233a02500a4c17b7f2c25840baec6a9ee`

Observability code added after review:

- `fb59d4dcea301662aefbf0294596cea16a49fb8f` — distinguish opening-only IDX price gaps;
- `a2c2f011851921762382ea4ddd4a0022dc5ff305` — regression tests for the new diagnostic classes.

## Review conclusion

The recorded `1260_RESEARCH_FEASIBILITY_NO_GO` is correct under the **provisional** research gate that required >=98% ticker coverage. It must not be relabelled as PASS retroactively.

However, this result is **not yet sufficient evidence that five-year research itself is infeasible**.

The reason is that the failure metrics point to a much narrower problem than a broken historical market foundation:

- exact official 1260-session calendar is complete;
- Stock Summary execution evidence is complete for all 1260 sessions;
- PIT identity reconstruction has zero unresolved required identities;
- strict 126 regression remains 963/963 PASS;
- research ticker coverage is 917/979 = 93.667%;
- ACTIVE-row coverage before exclusions is 99.316%;
- ACTIVE-row coverage after exclusions is 100%;
- known excluded Regular-Market value share is 2.373%;
- only 1 / 2 / 4 excluded names enter the known top 50 / 100 / 200 regular-market-value groups;
- most failures are historical public price-evidence gaps, not calendar/identity corruption.

The current 98% ticker threshold was intentionally provisional. Equal-weight ticker count can overstate research materiality because a dormant/illiquid historical security receives the same weight as a major liquid name. The threshold must not simply be lowered to force a green result, but the project should not stop before measuring the actual information loss.

## Critical unresolved question

The existing IDX fallback diagnostic historically collapsed two materially different cases into one label:

`OFFICIAL_OHLC_MISSING_OR_NONPOSITIVE`

That prevented the 6,716 unresolved ACTIVE pairs from being separated into:

1. **OPEN_ONLY_MISSING** — official IDX has valid H/L/C plus regular-market activity/value, but OpenPrice and FirstTrade are unavailable/non-positive;
2. **HLC_MISSING** — one or more of High/Low/Close is unavailable/non-positive;
3. **OPEN_AND_HLC_MISSING**;
4. other structural/envelope conflicts.

This distinction is decisive because the project's future **signal-research layer** may be able to use authoritative H/L/C/Volume/Value without Open, while the stricter **execution-grade layer** can continue to require full OHLCV.

No execution contract has been changed by this checkpoint.

## Observability fix

`src/idx_trade/idx_price_fallback.py` now emits separate diagnostics:

- `OFFICIAL_OPEN_MISSING_OR_NONPOSITIVE`
- `OFFICIAL_HLC_MISSING_OR_NONPOSITIVE`
- `OFFICIAL_OPEN_AND_HLC_MISSING_OR_NONPOSITIVE`
- existing envelope/active diagnostics remain unchanged.

The fallback still refuses to construct an execution-safe OHLCV row when Open is unavailable. The change is diagnostic only.

Regression tests cover all three new missing-field classes.

## Required next diagnostic

Before buying data, lowering coverage thresholds, changing the universe, or abandoning the 1260 research track:

1. rerun only the targeted missing-pair IDX fallback diagnostics for the existing 6,716 unresolved ACTIVE pairs using the new diagnostic classes;
2. do not redownload/rebuild the entire 1260 market unless necessary;
3. report counts by diagnostic class, ticker, year, and regular-market value;
4. compute how many of the 62 failed securities would become usable for a **signal-research HLCV panel** if Open were optional but H/L/C/Volume and PIT ACTIVE state remained mandatory;
5. recompute ticker, ACTIVE-row, and trading-value coverage under that hypothetical signal-research contract;
6. separately preserve the strict execution-grade OHLCV status as FAIL;
7. inspect the remaining genuine H/L/C gaps and UNKNOWN tradability cases independently.

## Possible phase split, not yet approved

If the diagnostic shows that the overwhelming majority of missing rows are Open-only, MAIN may consider explicitly separating:

- `EXECUTION_GRADE_OHLCV`: Open required; strict 504/1260 remain incomplete without entitled data;
- `SIGNAL_RESEARCH_HLCV`: authoritative H/L/C/Volume/Value plus PIT ACTIVE state required; Open optional and may not be synthesized.

The signal-research panel could support research into support/resistance geometry, excursions, close-to-close outcomes, volatility, volume, regime, and ranking information, but must not claim next-open execution, gap-aware fills, or production-grade backtest results.

Such a contract change must be explicit and justified by the Stage-2 label/execution specification, not introduced merely to improve the gate number.

## Current status

- strict 126: PASS;
- strict 504: FAIL;
- strict 1260: FAIL;
- provisional research 1260: NO-GO under >=98% ticker threshold;
- five-year research viability: **NOT YET DECIDED** pending the missing-field decomposition above;
- no modelling, IDX-VAL-002, main merge, paper trading, or live trading authorized by this review.
