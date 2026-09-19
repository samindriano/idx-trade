# Price/Trend State Alpha Challenger V1 — Preregistration

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-challenger-pit-safe-20260919`
Status: `PREREGISTERED — STRUCTURAL SHADOW ONLY`

## Hypothesis

The accepted causal Price/Trend State V1 contains a small amount of directional
context not represented by the incumbent's continuous HLCV rank features. A
fixed low-weight overlay may improve stability without becoming a high-turnover
replacement signal.

## Data and timing

The sidecar must be built from H/L/C/Volume available through source session
`t`, assigned to feature session `t+1`, using the accepted
`PRICE_TREND_CONFIRMATION_STATE_V1` contract. `Open` is not used. Outcome-like
columns, labels, forward returns, fitting, and trade recommendations are
forbidden.

## Frozen candidate

State mapping and blend are pinned in:

`src/idx_trade/alpha_challenger_price_trend_v1.py`

```text
candidate_score = 0.90 * incumbent_alpha_consensus
                + 0.10 * price_trend_quality
```

The mapping is domain-defined before any outcome access. `INDETERMINATE` is
neutral `0.5`, never dropped or forward-filled.

## Structural shadow result

An in-memory read-only audit over the 15 available clean V4-X1 prospective
score sessions (2026-08-21 through 2026-09-17) found:

- mean non-indeterminate state coverage: `97.35%`;
- mean Spearman versus incumbent `alpha_consensus`: `0.09305`;
- mean corrected Top-30 churn under the fixed 10% blend: `15.3333%`;
- maximum Top-30 churn: `23.3333%`;
- no outcome, target, return, provider, counter, or canonical artifact access.

These numbers are structural only and do not establish OOS improvement.

## OOS gate

The candidate remains `NOT_ADMITTED` until a separately authorized unseen
canonical evaluation satisfies the fixed IC/stability/PIT gates and a friction
review. No alternate state map, sign, weight, or threshold may be searched after
outcomes are observed.
