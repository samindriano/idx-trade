# Zapi TradingView Targeted Census — Independent Review

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-tradingview-targeted-census-v1`
Reviewed runtime HEAD: `ea748167d9df1d83d3f3d2c83cb8a25938cdd92c`
Decision: `TRADINGVIEW_5675_OPEN_CANDIDATES_ACCEPTED_DERIVATIVE_APPLICATION_AUTHORIZED`

## Review conclusion

The frozen 38,819-row non-corporate-action census is accepted as valid evidence.

The 5,675 TradingView rows satisfying all of the following may be promoted into a NEW derivative Open-backfill panel with row-level provenance:

1. exact ticker/date match;
2. exact certified panel High/Low/Close;
3. positive Open;
4. Open inside the certified Low–High range;
5. no corporate-action residual classification.

This approval is consistent with the previously frozen TradingView gate. In the prior 240-row validation sample, all 32 known-control rows classified as `TV_PANEL_HLC_OPEN_EXACT_CONTROL` had exact certified H/L/C and exact known Open. The census did not relax that gate.

No immutable-panel mutation is authorized.

## Accepted census facts

- authorized non-CA rows: 38,819;
- corporate-action rows excluded: 10,657;
- exact ticker/date coverage: 23,240;
- exact certified H/L/C: 5,675;
- admissible Open candidates: 5,675;
- unresolved non-CA after accepted candidates: 33,144;
- total project residual after derivative application would be 43,801 = 33,144 non-CA + 10,657 CA;
- original pre-Yahoo missing Open: 446,843;
- cumulative gap closure after Yahoo + accepted TradingView candidates would be 403,042 / 446,843 = 90.1977%;
- immutable panel SHA remains `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Remaining unresolved buckets

Non-CA:

- `TV_HISTORY_WINDOW_UNAVAILABLE`: 12,702;
- `TV_HLC_DISAGREEMENT`: 17,565;
- `TV_IDENTITY_OR_PROVIDER_ERROR`: 2,877.

Corporate-action lane remains separate:

- 10,657 rows.

## Authorization

Next authorized implementation is narrowly bounded to:

1. construct a new derivative panel by starting from the already accepted Yahoo Open-backfill derivative and applying only the 5,675 accepted TradingView rows;
2. preserve row-level source/provenance and all prior Yahoo provenance;
3. assert that no existing non-null Open is overwritten;
4. assert exactly 5,675 additional null Open values become non-null;
5. keep the certified immutable panel unchanged;
6. recompute Open coverage and execution-grade diagnostics factually;
7. write hashes/manifests and stop for independent review.

Not authorized in the same task:

- execution-grade promotion;
- corporate-action repair;
- alternate TradingView pagination/history tricks;
- Investing or another source;
- modelling / OHLCV alpha experiments;
- Ranking/PIT-sector work;
- execution PnL or live trading.

After derivative application is independently verified, the next research decision should split the remaining residual into three source strategies rather than treating all 43,801 rows identically: longer-history provider for the 12,702 history-window rows; independent source/arbitration for the 17,565 H/L/C-disagreement rows; and identity/provider remediation for the 2,877 provider-error rows, while the 10,657 corporate-action rows stay in their dedicated evidence lane.
