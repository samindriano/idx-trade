# Corporate-Action and Issuer-Basis Red-Team — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Category: `B / J — CA, identity, and adversarial review`
Status: `PASS_NARROW_CHECKS / GLOBAL_BASIS_BLOCKED`

## Question

Does the existing HLC overlay, residual-scale audit, and security-master
mapping establish a defensible issuer/security price basis for the current
candidate histories?

This is an independent read-only red-team. It does not repair prices, refit or
rescore candidates, open targets, or alter canonical data.

## Evidence

- The retained HLC overlay covers `1,657/981,940` panel rows, only `12`
  tickers, and `2` event families. All `1,657` panel closes equal the
  remediated close and `0` equal the original close; this is bounded overlay
  consistency, not population-wide basis authority.
- The `188` unresolved non-stable-scale rows are unique across `19` tickers,
  have `0/188` overlap with the HLC overlay, and each has one active listing
  interval. The residual therefore remains a separate unresolved population.
- The security master exposes `security_id`, ticker, company name, listing
  interval, and source, but no issuer/ISIN transition chain or event-level
  corporate-action semantics. All `19` residual tickers map to open-ended
  `IDX_STOCK_LIST` rows.
- Existing counterfactual evidence is candidate-sensitive: C1 has `82,357`
  score changes, `31,346` rank changes, a `10.617%` rank-change rate, and
  minimum Top-30 overlap `36.667%`; C2 and C4 have minimum overlaps `83.333%`
  and `86.667%`. H-LIQ, H-VOL, and H-EXC-02 also show nonzero changes and
  minimum overlaps of `90.000%`, `86.667%`, and `93.333%` respectively.
- The overlay includes `456 RIGHT_DISTRIBUTION` rows but only ratio/factor
  metadata; TERP, rights valuation, event ID, and ISIN transition evidence are
  absent. Ratio equality cannot certify event mechanics.
- Open-basis evidence remains blocked: all `1,657` overlay Open rows violate
  the corrected HLC range; `439` factor-fallback candidates, `2` official/
  factor disagreements, and `2` unresolved rows remain.
- “Direct” versus “spillover” is key-membership bookkeeping, not causal
  attribution. Three RISE overlay rows differ by up to `5.53e-8` between
  observed and expected factor; this is a tolerance issue, not clearance.

## Adjudication

| Review item | Result |
|---|---|
| HLC overlay internal consistency | `PASS — bounded` |
| HLC overlay population coverage | `FAIL — not global` |
| Residual disjointness check | `PASS — bounded` |
| Residual basis resolution | `FAIL / UNKNOWN` |
| Security-master listing interval mapping | `PASS — narrow` |
| Issuer/ISIN transition authority | `UNKNOWN / BLOCKED` |
| Candidate price-basis safety | `C1 FAIL; C2/C4/H-LIQ/H-VOL/H-EXC-02 UNKNOWN` |
| Global CA/issuer-basis admission | `NO-GO` |

## Decision

The existing fail-closed CA/issuer-basis disposition is upheld and should be
strengthened: no candidate history is globally certified as same-basis or
issuer-continuous. The HLC overlay is useful forensic evidence, but cannot be
expanded into a repair or admission artifact without event-level issuer/ISIN
and price-basis authority.

No new data acquisition, fallback provider, or candidate refit is justified by
this red-team. Future progress requires an independently admitted transition
source or a formal Data QA decision.

## Reproducibility

- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Guarded feature SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- HLC overlay SHA-256: `0b372d1925ae8f0a5342e7ed3c3d8b91b77ae547dbc75ad9ed9d8c28fefc5b02`
- Security-master SHA-256: `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`
- Residual-scale source SHA-256: `eaedba187a3645a83c06c3885dac2c819e818fb68636cfedf2d32e7792432743`
- Related checks: `ALPHA_CA_PRICE_BASIS_RESULT_V1`,
  `ALPHA_CA_RESIDUAL_COVERAGE_RESULT_V1`, `ALPHA_HEXV02_CA_SENSITIVITY_RESULT_V1`,
  and `ALPHA_HEXC02_CA_SENSITIVITY_RESULT_V1`.

No target, outcome, provider, cloud, canonical, capture, scheduler, telemetry,
or production state was accessed or modified.
