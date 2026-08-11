# Corporate Actions V1 — Final Bounded Split Diagnostic

Date: 2026-08-12  
Branch: `data/corporate-actions-v1`  
Parent: `957b7d0c2fc6ef8b6138ab959aabfb2cd01eefdf`  
Scope: stock-split diagnostics only; no price adjustment or event-date promotion

## Decision

`SPLIT_METADATA_DISCOVERY_ONLY_CANONICAL_PROMOTION_FAIL_CLOSED`

The official IDX split metadata is useful for discovery and for constructing a
bounded diagnostic input. It is not promoted to a canonical
`market_effective_date` event table in this task. The price panel is not
semantically reliable enough to validate exchange-effective split sessions:
one nearby mechanical match was found, but official documents show that the
matched price transition is dated five observed sessions too early.

## Method

- 39 logical positive-ratio events were built from the existing official IDX
  issued-history capture;
- duplicate source rows were reduced by `(ticker, TanggalPencatatan)` only
  after confirming the normalized ratio; BBNI has multiple source component
  rows but the same approximately 2:1 ratio;
- `scan_split_candidate_transitions()` was run with `window_sessions=10`;
- the panel was the existing 1260-session raw directory, with no adjusted
  fields, provider action flags, or inferred dates used for the transition
  calculation;
- each event was summarized by the nearby transition with the smallest
  relative error against `ratio_old / ratio_new`.

External diagnostic artifacts:

- scan CSV: `D:\Documents\Project\idx-trade-corporate-actions-20260811\split_candidate_scan_39_events_window10.csv`;
- best-transition CSV: `D:\Documents\Project\idx-trade-corporate-actions-20260811\split_candidate_best_39_events_window10.csv`;
- summary SHA-256: `7109c9b9112f5844a0fd2f4571a99899b2029896d23c1a0cd83a67837463ce98`.

## Results

- Events scanned: `39/39`; price files missing: `0`;
- match within 10%: `1/39`;
- match within 20%: `1/39`;
- only match: `FISH`, anchor `2025-09-09`, candidate `2025-09-01`, offset `-5`,
  expected ratio `0.1`, observed open/close ratio `0.1/0.1`;
- offset distribution of matches: `{-5: 1}` — no consistent offset can be
  inferred;
- second-best relative error: `TMAS`, `45.30%`;
- best-error quantiles: minimum `0.000`, p10 `0.839`, p25 `0.909`, median
  `3.666`, p75 `3.832`, maximum `21.198`;
- only `2/39` events had best relative error at or below `50%`, and `14/39`
  at or below `100%`.

Representative non-matches:

- `ASDM 2023-12-12`, official ratio 2:1, provider split flag present on the
  anchor, but OHLC remains approximately continuous;
- `MLPT 2026-07-21`, official ratio 25:1 and provider split flag present on
  the anchor, but the adjacent OHLC ratio is not mechanical;
- `TMAS 2023-05-23`, official/provider ratio 10:1, observed ratio about
  `0.1453` rather than `0.1`.

No normalized ratio disagreement was found among the 39 logical positive-ratio
events. The source still contains 16 separate zero/placeholder or invalid
stock-split rows outside this logical set; these remain source anomalies.

## FISH official semantic check

The nearby match was not promoted. Official IDX/issuer documents establish the
actual schedule:

- issuer correction, published 2025-08-28, states the last trading date at
  the old nominal value is 2025-09-08 and new-nominal trading starts in the
  Regular/Negotiated Market on 2025-09-09;
- official IDX theoretical-price notice dated 2025-09-08 states the JATS
  adjustment is performed on 2025-09-09 and calculates `10,350 / 10 = 1,035`;
- official IDX listing notice records 480,000,000 shares before, 4,320,000,000
  additional shares, 4,800,000,000 after, with listing date 2025-09-09.

The price panel instead shows FISH at 10,350 through 2025-08-29 and 1,035
starting 2025-09-01; its provider `stock_splits=10` flag appears on 2025-09-09.
Thus the nearby price match is a provider/date-alignment diagnostic, not
evidence that 2025-09-01 is the exchange-effective session.

Official attachment captures retained outside Git:

- theoretical-price notice SHA-256:
  `10cf9e9f4a25e86163eeb9a9ed3c72b09d76f8213fc6f62cd71a7a90988e0c58`;
- listing notice SHA-256:
  `019eb57b1963ee36290bf94a09280359141600a50fcdb7b2fd4c48e33c8bfcd6`;
- issuer correction SHA-256:
  `e76d7d41988c39169fc8385a77b444fb696bf4de92d67dbef79b5e1d0d3a493b`.

## Price-provider provenance and interpretation

The repository documents the existing provider as Yahoo/yfinance with
`auto_adjust=False`; `src/idx_trade/providers/yahoo.py` calls
`yf.download(..., auto_adjust=False, actions=True)`. The canonicalizer aliases
provider `Open/High/Low/Close` to `raw_open/raw_high/raw_low/raw_close` and
keeps `vendor_adj_close` and `stock_splits` separate. These names and the
configuration are not independent proof that every historical OHLC value is
exchange-unadjusted.

Empirically, 37 of 39 official events have a provider split flag within the
same ±10-session neighborhood, often with the official ratio, but only 1 of 39
has a matching OHLC transition. The panel is therefore not demonstrated to be
uniformly split-adjusted or uniformly exchange-unadjusted. It has mixed/date-
alignment behavior and is unsuitable for systematic mechanical split
validation.

This is a limitation of the price diagnostic, not evidence that the official
IDX split records are false. No price row was rewritten.

## Validation

- focused diagnostic tests: `3 passed`;
- full pytest: `482 passed, 0 failed, 3 existing pandas FutureWarnings`;
- no code or research-definition changes were made to the diagnostic
  implementation.

No HMETD/bonus/capital-reduction reconstruction, OPEN backfill, PIT sector,
Historical Universe, model, outcome, Path Risk, execution/PnL, or main work
was performed.
