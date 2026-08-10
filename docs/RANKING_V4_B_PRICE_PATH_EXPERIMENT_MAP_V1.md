# Ranking V4-B Price-Path Quality — Experiment Map V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **DESIGN MAP — NO OUTCOME SCORING AUTHORIZED**

## Family role

`V4-B-PRICE-PATH-V1` is the second family in the frozen V4 final-alpha arena.

The immutable common benchmark remains final V3-B Structure-Lite. V4-A Participation Quality / Price Impact is closed with no survivor and may not be rescued or folded into this family.

Primary family question:

> Conditional on the frozen V3-B statistical state and causal price geometry, does the *way the current price state was formed* add robust cross-sectional ranking information?

This family intentionally merges ideas that would otherwise create excessive researcher degrees of freedom: trend coherence, jump/spike concentration, tail-shape intuition, candle/range quality, and acceptance/rejection behavior.

## Sub-research B1 — Path Coherence / Jump Concentration

Economic question:

> Did the observed multi-session move form through coherent directional travel, or is it mostly back-and-forth noise / one-day displacement?

This is **not** another momentum-magnitude candidate. V3-B already knows 5- and 20-session return magnitude and volatility. B1 is restricted to path-shape quantities conditional on those states.

Pre-freeze concepts retained:

- directional path efficiency over short and medium windows;
- concentration of total absolute movement in the single largest daily move.

Concepts rejected before outcome access:

- multiple skew/kurtosis variants;
- MAX-return and MIN-return as separate candidates;
- separate trend-R2/slope/residual-noise candidate;
- many 5/10/20/60 lookback variants;
- thresholded jump flags.

Reason: these overlap heavily with the same underlying return path and would create a feature tournament rather than one information hypothesis.

## Sub-research B2 — Range Acceptance / Rejection Quality

Economic question:

> Across recent sessions, does price repeatedly finish in favorable parts of its daily high-low range, or does it repeatedly experience rejection / weak closes?

This differs from existing V3-B information:

- `close_position_20` is the current close position inside the **20-session aggregate high-low range**;
- Structure-Lite measures support/resistance geometry, breakout and retest state;
- B2 instead measures the **sequence of daily close locations inside each day's own high-low range**.

Pre-freeze concepts retained:

- continuous daily close-location acceptance over 5 and 20 sessions;
- a compact extreme-close balance over the recent 5 sessions.

Concepts rejected before outcome access:

- separate upper-wick/lower-wick families;
- many candlestick-pattern flags;
- Open-dependent candle bodies/gaps;
- many arbitrary rejection thresholds;
- structure-conditioned interactions before independent B2 evidence exists.

## First-pass research structure

If exact specification review confirms the two questions remain sufficiently distinct, reserve exactly:

- one exact V3-B control;
- one B1 challenger;
- one B2 challenger.

Both challengers must be fully frozen and implemented before either outcome is viewed. Their first historical-development scoring must be atomic / parallel-equivalent against the same exact control.

No B1+B2 integration candidate exists in first pass. One integration may be designed only if both independently pass their frozen gate and receives separate specification/review/authorization.

## Anti-overfit boundary

Do not create rescue variants after outcome access. In particular, do not respond to a weak B1/B2 fold by changing:

- lookback length;
- return definition;
- range-location threshold;
- feature subset;
- model family or hyperparameters;
- fold/gate definition.

If a frozen challenger fails, that hypothesis is closed for this V4 family.

## Data boundary

Only causal after-close information from the immutable regular-market signal-research panel is eligible. Historical Open is not required. Missing official-session observations may not be interpreted as flat trading.

Historical-development V4-B materialization must remain `<=1224`. Post-2026-07-31 fresh-forward outcomes and `FORWARD_OUTCOME_ACCESS_STARTED` remain untouched.