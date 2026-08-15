# Price / Trend / Confirmation State V1 — Outcome-Blind Contract

Date: 2026-08-15 (Asia/Jakarta)

Branch: `research/idx-price-trend-confirmation-state-v1`

Status: `PRICE_TREND_CONFIRMATION_STATE_V1_IMPLEMENTED_REVIEW_REQUIRED`

## Purpose

Build a deterministic descriptive price-state layer that can later be combined
with the already accepted Foreign Flow Setup State.  This layer answers:

> What is the current price/trend/structure/confirmation context known after
> completed source session `t`, for use in the next official session `t+1`?

It does **not** answer whether the stock will rise, estimate probability or
expected return, fit a model, or issue BUY/SELL recommendations.

Target architecture remains:

`Foreign Flow State + Price/Trend State + later Supply State -> separate setup/eligibility logic -> ranking -> risk/execution`

V1 intentionally does not combine those layers yet.

## Scientific boundary

- Outcome-blind only.
- Source session `t` is assigned to next official `feature_session=t+1`.
- No target-session OHLCV is required to produce the `t+1` state.
- No TP/SL, label, realized return, forward return, protected outcome, model
  score, or historical performance result may enter the state builder.
- No threshold may be tuned from a historical or prospective outcome result.
- No O2 model/counter/runtime changes.
- No Foreign Flow formula/state changes.
- No HSC/free-float/effective-supply integration.
- No TradingView intraday or Path Risk dependency.

## Why Open is excluded

V1 uses raw observed **High / Low / Close / Volume** only.  Historical OPEN
recovery remains a separate unresolved lineage and TradingView open/session
semantics are separately governed.  Price State V1 therefore does not require
`raw_open` and cannot silently inherit those unresolved semantics.

## Raw evidence

Per ticker, using only observations available through source session `t`:

### Moving-average context

- `ma_10`
- `ma_20`
- `ma_50`
- `ma_200` (optional long-term axis; not required for the main trend state)
- `ma20_slope_5 = ma20[t] / ma20[t-5] - 1`
- `ma50_slope_10 = ma50[t] / ma50[t-10] - 1`
- `ma200_slope_20 = ma200[t] / ma200[t-20] - 1`
- distance of close to MA20 / MA50 / MA200

### Swing / range structure

- prior 20-observation high, **current excluded**
- prior 20-observation low, **current excluded**
- close distance to prior high
- 20-observation range position / range width
- recent 5-observation high/low
- immediately preceding 5-observation high/low

The V1 swing labels compare these two non-future windows directly.  No
outcome-derived tolerance is applied.

### Volume

`volume_ratio_20 = current raw volume / median(previous 20 raw volumes)`

Engineering thresholds, frozen before any outcome evaluation:

- `EXPANDING`: ratio >= 1.50
- `CONTRACTING`: ratio <= 2/3
- otherwise `NORMAL`

### Volatility / range contraction

Daily range proxy:

`range_pct = (high - low) / close`

Then compare median recent 5 observations with the prior non-overlapping
20-observation median:

`volatility_ratio_5_20 = median(range_pct[t-4:t]) / median(range_pct[t-24:t-5])`

Frozen engineering thresholds:

- `CONTRACTING`: <= 0.75
- `EXPANDING`: >= 1.25
- otherwise `NORMAL`

## State axes

### `ma_structure_state`

- `BULLISH_STACK`: `close > MA20 > MA50` and MA20/MA50 slopes positive
- `BEARISH_STACK`: `close < MA20 < MA50` and MA20/MA50 slopes negative
- `RECOVERING`: close above MA20 and MA20 slope positive
- `WEAKENING`: close below MA20 and MA20 slope negative
- `MIXED`
- `INDETERMINATE`

### `long_term_state`

MA200 is deliberately an optional context axis so a ticker with fewer than
200 observed bars can still have a defensible main trend state.

- `ABOVE_RISING_MA200`
- `BELOW_FALLING_MA200`
- `MIXED`
- `UNAVAILABLE`
- `INDETERMINATE`

### `swing_structure_state`

- `HIGHER_LOW_HIGHER_HIGH`
- `HIGHER_LOW_ONLY`
- `LOWER_LOW_LOWER_HIGH`
- `LOWER_LOW_ONLY`
- `MIXED`
- `INDETERMINATE`

### `confirmation_state`

Prior breakout level always excludes the current observation.

- `BREAKOUT_CONFIRMED`: close > prior 20 high AND volume ratio >= 1.50
- `BREAKOUT_WEAK_VOLUME`: close > prior 20 high without expanded volume
- `FAILED_BREAKOUT_RECENT`: a breakout occurred in the prior five observations
  and current close is below that breakout level
- `NEAR_BREAKOUT`: no current/recent failure and close is within 3% below the
  prior 20 high
- `NO_BREAKOUT`
- `INDETERMINATE`

`BREAKOUT_CONFIRMED` is descriptive confirmation only.  It is not an entry
recommendation.

## Main `trend_state`

Precedence:

1. `UPTREND` when `ma_structure_state=BULLISH_STACK`.
2. `DOWNTREND` when `ma_structure_state=BEARISH_STACK`.
3. `EARLY_REVERSAL` when price is `RECOVERING` and has a higher low.
4. `BASING` when all frozen descriptive conditions hold:
   - absolute MA20 five-observation slope <= 1.5%;
   - 20-observation range width <= 20% of close;
   - absolute close-to-MA20 distance <= 8%;
   - recent range volatility is not `EXPANDING`.
5. otherwise `TRANSITION`.
6. insufficient required evidence -> `INDETERMINATE`.

These cutoffs are broad engineering definitions for state interpretation, not
alpha gates.  They must not be changed after observing outcome performance.

## Missingness and fail-closed behavior

- Nonfinite or invalid raw H/L/C/Volume is rejected.
- Negative volume, low > high, or close outside H/L is rejected.
- Duplicate `(ticker, source_session)` is rejected.
- Input dates outside the supplied official calendar are rejected.
- Outcome-like columns are rejected case-insensitively.
- Insufficient rolling history returns `INDETERMINATE`, not synthetic values.
- Output duplicate `(ticker, feature_session)` is rejected.
- No forward fill of state evidence.

## Prospective timing

For a completed source session `t`:

`raw HLCV through t -> Price/Trend State evidence at t -> assign feature_session=t+1`

A convenience producer explicitly clips a larger cached frame back to `t`.
Adding, removing, or changing target-session `t+1` data must not change the
already computed state for `t+1` sourced from `t`.

## V1 implementation

- `src/idx_trade/price_trend_state.py`
- `tests/test_price_trend_state.py`

Tests cover uptrend, downtrend, basing without MA200, breakout with/without
volume confirmation, recent failed breakout, target/future invariance,
outcome-column rejection, duplicate rejection, insufficient-history
missingness, OPEN independence, and invalid HLC rejection.

## Next boundary

Before any integration with Foreign Flow or any outcome/performance evaluation:

1. run exact focused tests and repository suite in a real checkout;
2. adversarially review causality/missingness/state semantics;
3. independently review the frozen descriptive thresholds;
4. only after acceptance, add a separate prospective sidecar/runtime adapter
   that reuses the existing canonical EOD capture path and no new counter;
5. only after both state layers accumulate prospectively may a separate
   `Foreign Flow + Price State -> Setup/Eligibility` contract be frozen.
