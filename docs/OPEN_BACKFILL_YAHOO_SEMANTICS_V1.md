# Historical Open Backfill — Yahoo Semantics + Broad Coverage V1

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-yahoo-semantics-v1`
Parent review commit: `d00c8d74f2728836ed842ba545034e07b10e5405`

## Purpose

Determine whether Yahoo/yfinance can provide materially useful historical raw Open evidence for the immutable 1260-session IDX panel after explicitly accounting for stock-split scale semantics and testing broad ticker coverage. This is a source-semantics and coverage audit only. It is not a bulk backfill and does not authorize execution-grade promotion.

## Immutable baseline

- panel window: `2021-04-29 -> 2026-07-31`;
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- unresolved Open rows: `446,843`;
- existing non-null Open values are immutable;
- Ranking V1/V2 semantics are unchanged;
- `execution_grade_promoted=false`.

## Why this follow-up exists

The prior 50-row Tier-2 pilot found Yahoo H/L/C exact agreement on 7/8 returned sample rows, known Open exact agreement on 4/5 known rows, and three missing-Open rows that passed the frozen contract. It also found `BBCA 2021-08-03` at an exact 5x historical price-scale difference, consistent with a later 1:5 split. The prior sample covered only eight unique Yahoo tickers, so it was useful for failure discovery but not universe-wide coverage certification.

## Frozen audit design

Use a deterministic sample selected before querying Yahoo outcomes.

Target:

- at least **120 unique tickers**;
- at least **240 unique ticker/date rows** total;
- include both known-existing-Open and missing-Open rows;
- include at least 30 tickers with independently verified split/reverse-split evidence in or after the panel window where repository evidence permits;
- include at least 80 tickers with no verified split event in the relevant period;
- include liquid and illiquid names, early and late panel dates, IPO/new-listing edges, corporate-action-adjacent dates, suspension/resumption edges, and provider-gap names such as FREN/MASA/MFIN where applicable;
- preserve a manifest and SHA-256 of the exact sample before runtime.

Do not choose or replace rows after inspecting Yahoo results.

## Raw-price rule

Yahoo must be fetched with raw OHLC preserved (`auto_adjust=False`). `Adj Close`, dividend-adjusted prices, and total-return adjustments are never execution prices and may not be used to fill Open.

### Direct raw admission

A Yahoo row directly passes only if:

1. ticker/security identity exact;
2. date exact;
3. Yahoo raw High == certified High;
4. Yahoo raw Low == certified Low;
5. Yahoo raw Close == certified Close;
6. Yahoo raw Open is finite and > 0;
7. Yahoo raw Open is inside `[certified Low, certified High]`.

### Split-scale diagnostic path

If raw H/L/C are not exact, the audit may test whether a **single independently verified cumulative split factor** explains the entire OHLC scale mismatch. This path is diagnostic and must satisfy all conditions:

- split/reverse-split evidence comes from existing authoritative repository corporate-action evidence or another separately documented authoritative source, not inferred from Yahoo price ratios alone;
- no factor is fitted to make the row match;
- one factor must transform raw Open/High/Low/Close consistently;
- transformed H/L/C must equal certified panel H/L/C exactly;
- transformed Open must be finite, positive, and inside certified `[Low, High]`;
- dividend adjustments are prohibited;
- `Adj Close` is prohibited as execution evidence.

Classify such rows separately as `SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE`; do not silently treat them as native raw agreement.

If independently verified split evidence is absent, any scale mismatch remains rejected.

## Required metrics

Report separately for non-split and split strata:

- unique tickers requested/returned;
- ticker coverage rate;
- exact ticker/date coverage rate;
- direct raw H/L/C exact rate;
- known Open direct exact rate;
- missing Open direct-admissible count/rate;
- split-scale mismatch count;
- split-scale reconstructable count/rate;
- reconstructed known-Open exact rate;
- reconstructed missing-Open admissible count;
- provider errors by ticker/reason;
- no-provider-row count;
- duplicate-key/identity/date anomalies;
- early-vs-late panel coverage;
- corporate-action and IPO-edge diagnostics.

Also estimate, without writing any panel, how many of the 446,843 unresolved rows appear potentially recoverable under the frozen direct + independently verified split-scale contract. Any estimate must clearly state its denominator and provider coverage assumptions.

## Stop gate

Bulk Yahoo backfill remains blocked unless this broader audit shows all of the following:

1. broad ticker coverage is materially useful rather than concentrated in a small subset;
2. non-split known-answer raw Open/HLC agreement is high and stable;
3. split-scale mismatches are explainable by independently verified split factors, not fitted ratios;
4. transformed H/L/C are exact under the same immutable certified panel;
5. no silent adjusted/dividend semantics enter execution prices;
6. unresolved provider gaps remain explicit rather than synthesized.

Even if all pass, stop for independent ChatGPT review before any bulk write.

## Prohibited

- no direct IDX scraping/crawling;
- no TradingView/Investing ingestion;
- no source averaging/voting;
- no synthetic/forward-filled Open;
- no previous-close substitution;
- no outcome-driven sample changes;
- no Stage-5 rerun;
- no Ranking-V2 change;
- no execution-PnL/paper/live trading;
- no merge to `main`.
