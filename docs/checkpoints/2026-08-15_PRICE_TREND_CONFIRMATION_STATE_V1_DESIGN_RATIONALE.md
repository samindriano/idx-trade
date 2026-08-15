# Price / Trend / Confirmation State V1 — Design Rationale

This note records why V1 is deliberately simple and modular.

## Separate axes, not one score

A single technical-analysis score would hide materially different states. V1
therefore preserves separate evidence for trend, swing structure, volume,
volatility, and breakout confirmation. A future setup layer may combine these
with Foreign Flow, but this contract does not.

## Moving averages are context, not alpha

MA10/20/50/200 are interpreted as descriptive location/slope context. MA200 is
optional and does not force the main state to `INDETERMINATE`, avoiding an
unnecessary 200-observation warm-up for the core trend label.

## Breakout level excludes current bar

The prior 20-observation high is shifted by one observation. This avoids using
the current bar to define the level that the same current close is claimed to
break.

## Volume confirmation remains separate

A close above the prior high is `BREAKOUT_WEAK_VOLUME` unless current volume is
at least 1.5x the previous-20 median. This preserves the evidence distinction;
it does not claim that 1.5x is historically optimal.

## Basing is deliberately broad

Basing uses a flat-ish MA20, bounded 20-observation range, proximity to MA20,
and non-expanding recent range volatility. The thresholds are broad engineering
semantics frozen before outcome inspection. They are not intended as entry
rules.

## No OPEN / intraday dependency

The state uses H/L/C/Volume only. This keeps V1 independent from unresolved
historical OPEN recovery and separate TradingView intraday/session-semantic
lanes.

## No direct ENTRY_ELIGIBLE label

Even a confirmed breakout is only descriptive price evidence. ENTRY eligibility
belongs to a later explicitly frozen combination layer with Foreign Flow and,
if defensible, supply context.
