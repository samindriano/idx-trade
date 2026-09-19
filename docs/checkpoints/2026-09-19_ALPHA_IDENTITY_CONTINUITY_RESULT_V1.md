# Alpha Identity Continuity Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `B_J_IDENTITY_PROVENANCE_AUDIT`
Result: `PASS_STRUCTURAL_ONLY / DOES NOT CERTIFY CORPORATE-ACTION BASIS`

## Question

The red-team review noted that the feature runners use `(ticker,date)` keys and
do not themselves carry issuer/ISIN identity. This audit checks whether the
available reconciled security master supplies a unique active listing interval
for the panel keys used by the structural lane.

This is an identity-continuity audit only. It does not infer corporate-action
adjustments, price-basis validity, or predictive evidence.

## Evidence

| Item | Result |
|---|---:|
| Clean panel rows / unique `(ticker,date)` keys | 981,940 / 981,940 |
| Panel tickers | 945 |
| Security-master rows / security IDs | 979 / 979 |
| Security-master tickers | 979 |
| Duplicate ticker rows in master | 0 |
| Duplicate security IDs | 0 |
| Unmapped panel tickers | 0 |
| Panel keys with exactly one active security ID | 981,939 |
| Panel keys with no active security ID | 1 |
| Panel keys with multiple active security IDs | 0 |
| Frozen eligible keys with exactly one active security ID | 310,761 |
| Frozen eligible keys with no active security ID | 0 |
| Frozen eligible keys with multiple active security IDs | 0 |

The available security master is one-row-per-ticker in this snapshot. Every
eligible key used by C1–C4 is covered by exactly one listing interval under the
simple `listed_from`/`listed_to` audit.

## Interpretation and limitations

- This materially reduces the immediate ticker-reuse/relisting ambiguity for
  the current structural panel.
- The one uncovered source panel key is outside the frozen eligible universe;
  it does not enter the current candidate structural rows.
- The security master has no historical issuer/ISIN transition chain in the
  runner's input contract, so this is not proof that all ticker changes or
  corporate actions are represented correctly.
- It does not prove that `close`, `volume`, or `regular_market_value` share a
  consistent corporate-action basis. That remains a separate P0/P1 admission
  risk.
- H-LIQ's `log(close * volume)` remains subject to field-unit and price-basis
  review; identity success is not economic readiness.

## Disposition

| Risk | Current result |
|---|---|
| Ticker-to-master mapping for eligible structural rows | `PASS_STRUCTURAL_ONLY` |
| Historical issuer/ISIN continuity beyond this snapshot | `UNKNOWN` |
| Corporate-action transition basis | `UNKNOWN/BLOCKED` |
| H-LIQ candidate admission | unchanged: `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION` |

## Reproducibility and firewall

- Builder: `research/alpha_identity_continuity_audit_v1.py`
- Builder SHA-256: `7b2be0446b274ed663beb7e543c0ca70e2269c992b627e23a89bb6d3127d0f29`
- Output:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_identity_continuity_audit_v1.json`
- Output SHA-256: `fe61b38ebaadc74aad0eaeca37536b242efcc177c5b8c10f15dd00df8df73c97`
- Firewall artifact:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_identity_continuity_firewall_v1.json`
- Firewall artifact SHA-256: `81b0b371d4e509eff60400f6c392457f4d00cc9bdf17ceeca46d1a9281d00ba9`
- Firewall result: `PASS`

No target, forward return, incumbent score, provider, network, cloud, capture,
scheduler, counter, canonical, or production artifact was opened or modified.
