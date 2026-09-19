# Claim — Price/Trend State Alpha Challenger V1

- Owner: isolated alpha challenger lane
- Branch: `codex/alpha-challenger-pit-safe-20260919`
- Scope: outcome-blind, PIT-safe fixed overlay only
- Incumbent protection: do not modify, refit, rescore, or replace V4-X1

## Frozen construction

Consume only the accepted `PRICE_TREND_CONFIRMATION_STATE_V1` sidecar. Map its
descriptive `trend_state` to a fixed quality score:

| State | Score |
|---|---:|
| `UPTREND` | 1.00 |
| `EARLY_REVERSAL` | 0.75 |
| `BASING` | 0.50 |
| `TRANSITION` | 0.50 |
| `DOWNTREND` | 0.00 |
| `INDETERMINATE` | 0.50 |

The only candidate blend is:

`candidate_score = 0.90 * incumbent_alpha_consensus + 0.10 * price_trend_quality`

Both terms are higher-is-better values on `[0, 1]`. No fitting, sign search,
threshold tuning, forward fill, or outcome-derived mapping is allowed.

## Acceptance boundary

This is not admitted from structural diagnostics. A separate unseen canonical
evaluation must show mean daily IC delta `>= +0.005`, non-negative q25 delta,
at least `80%` non-negative 20-session blocks, common-support coverage `>=95%`,
and zero PIT/provenance violations. Economic friction and turnover must also be
reviewed before any promotion claim.

No historical consumed fold, protected outcome, runtime counter, or incumbent
artifact may be used for selection or rescue.
