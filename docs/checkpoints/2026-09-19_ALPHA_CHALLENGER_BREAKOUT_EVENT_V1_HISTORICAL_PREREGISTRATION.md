# Alpha Challenger — Breakout Event V1 Historical Development

Status: `PREREGISTERED / HISTORICAL DEVELOPMENT ONLY`

This is a new, fixed challenger after the outcome-blind Stage A audit. It is
not a rescue search for Foreign Flow V2, does not refit or rescore the V4-X1
incumbent, and cannot touch prospective/protected outcomes or runtime state.

## Frozen inputs

- clean OHLCV panel SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- historical target ledger:
  `D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2\clean_target_ledger.parquet`
- accepted incumbent validation scores:
  `D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2\clean_challenger_validation_scores.parquet`
- historical target boundary: `2026-07-17` / signal session index `1249`
- score support: six accepted chronological validation folds, dates
  `2023-12-28` through `2026-07-17`

Only the historical ledger and accepted validation scores are permitted. Any
fresh-forward, protected, O2, production, or provider artifact is forbidden.

## Frozen signals

The two event signals are built exactly from the Stage A constructor at session
`t`, with no future or centered rolling values:

- `failed_breakout_signed`: downside break that closes back above the prior
  20-session low is `+1`; upside break that closes back below the prior high is
  `-1`; otherwise `0`.
- `confirmed_breakout_signed`: close above the prior 20-session high is `+1`;
  close below the prior 20-session low is `-1`; otherwise `0`.

For each date, each signal is transformed to an average-tie percentile rank
across its available rows. The fixed event overlay is the equal-weight mean of
the two percentile ranks. No sign flip, subset selection, threshold, or
post-result orientation change is allowed.

The fixed comparison overlay is:

`0.80 * rank(accepted incumbent alpha_consensus) + 0.20 * event_overlay`

The `0.80/0.20` weight is fixed before reading target values. This is a
diagnostic challenger score, not a production change.

## Metric and gate

On exact common-support rows by date, calculate daily cross-sectional Spearman
IC against the accepted historical `realized_consensus` target. Report the
event overlay and fixed blend separately versus the accepted incumbent:

- mean daily IC and paired mean delta;
- q25 daily IC and paired q25 delta;
- all chronological non-overlapping 20-session block mean deltas;
- date count and row coverage;
- tie/usable-row diagnostics.

The fixed blend is a historical-development `PASS` only if all are true:

1. paired mean IC delta is at least `+0.005`;
2. paired q25 IC delta is non-negative;
3. at least `80%` of chronological 20-session blocks have non-negative delta;
4. at least `100` dates have valid common support and the blend does not lose
   more than `5%` of incumbent rows.

Any failure is a final `NO-GO` for this exact fixed event overlay. No alternate
weight, horizon, window, event definition, or model is permitted afterward in
this preregistered run.

Even a pass is historical evidence only. It cannot promote or alter V4-X1;
independent prospective evidence and the project's admission gates remain
required.
