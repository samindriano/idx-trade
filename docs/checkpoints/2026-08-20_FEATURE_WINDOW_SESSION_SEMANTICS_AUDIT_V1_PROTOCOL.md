# Feature-Window Session Semantics Audit V1 — Frozen Protocol

Date: 2026-08-20 (Asia/Jakarta)
Branch: `audit/feature-window-session-semantics-v1`

## Question

Do the frozen row-based `shift(5)`, `shift(20)`, ATR14, rolling-20, and rolling-60 feature windows on the actual V2/V4-X support represent their nominal IDX exchange-session horizons, or do observed-bar gaps materially extend the elapsed market-time horizon?

This is a feature-semantics audit, not a raw-data repair lane.

## Frozen inputs

- signal panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- official 1260-session calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- training-basis v1.1 manifest SHA-256: `62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6`
- full-panel official-IDX integrity manifest SHA-256: `bf87e0c8ce49468113eec32cb7df931ff0df887444de727a57c65b495d87c016`

The parent integrity audit already found zero missing official ACTIVE valid-HLC rows and complete 1260-session calendar witness coverage. Therefore an extended observed-row horizon, if found, is not attributed to an acquisition hole on the tested frozen panel.

## Support populations

The runtime reports:

1. `V2_PREPARED`: identities from the frozen V2 prepared-representation impact artifact.
2. `V4_H5_EXACT_FIT`: exact final-refit H5 identities, reconstructed from frozen training dates + `h5_full_target_support` and cross-checked to the final fit log row count.
3. `V4_H10_EXACT_FIT`: same for H10.
4. `V4_UNION_EXACT_FIT`: union of exact H5/H10 fit identities.

No target values are read.

## Nominal-vs-effective definitions

- `lag5`: exchange session-index distance to the fifth previous observed ticker row; nominal `5`.
- `lag20`: exchange session-index distance to the twentieth previous observed ticker row; nominal `20`.
- `atr14`: inclusive exchange-session span covering the 14 observed rows used by row-based ATR; nominal `14`.
- `rolling20`: inclusive exchange-session span covering 20 observed rows; nominal `20`.
- `rolling60`: inclusive exchange-session span covering 60 observed rows; nominal `60`.

An effective span greater than nominal means the feature is an observed-bar horizon that extends over more exchange time than its nominal label.

## Important non-target

The V4 primary-liquidity 60-session state is already implemented with an explicit exchange-session-index boundary. This audit does not classify that liquidity eligibility window as vulnerable to the row-window issue.

## Guardrails

- no provider/network calls;
- no data repair;
- no feature-definition changes;
- no model fit/scoring/tuning;
- no target-value access;
- no protected-forward access;
- no parent-panel overwrite.

A positive finding is **not leakage** and does not automatically invalidate V4-X. It establishes a hidden feature-semantic assumption that must be independently adjudicated. Any change from observed-bar to exact-session semantics would be a new scientific feature definition and must not be folded into the price-basis remediation/refit as a silent fix.
