# Price-Basis Open Forensic V1 — Frozen Boundary

Date: 2026-08-20 Asia/Jakarta  
Branch: `data/price-basis-remediation-v1`

## Trigger

The immutable post-remediation guard manifest
`d96fa15d5ae31fc1b50f765283df3dc7f244836e70bf4662f0bf045d6bc40bce`
returned `POST_REMEDIATION_GUARDS_BLOCKED_OPEN_HLC_INCONSISTENCY`.

Broad Volume/Regular-Market-Value evidence passed perfectly across all
981,940 panel rows, but all 1,657/1,657 HLC-remediated rows had the existing
accepted Open outside corrected raw IDX Low/High.  No Open repair was made.

## Relevant prior evidence

The repository already contains `data/idx-open-ca-scale-reconstruction-v1`.
That frozen audit proved that provider historical Open can share the same
corporate-action adjustment basis as provider H/L/C.  For CLEO, MMIX and WGSH,
an independently sourced official factor transformed provider H/L/C exactly to
the then-canonical raw H/L/C and produced 2,184 valid transformed Open rows.

Separately, `data/idx-open-official-stock-summary-recovery-v1` established that
official IDX Stock Summary contains an `OpenPrice` field.  Positive `OpenPrice`
was the only defensible official Open candidate in that audit; `FirstTrade` was
explicitly rejected as an Open fallback.

These are prior mechanistic/source facts, not authorization to repair the new
1,657-row population.

## Frozen forensic questions

For exactly the 1,657 HLC-remediated rows / 12 tickers:

1. What source currently wins the V4 accepted-Open precedence rule
   (`derivative_open` before recovery overlay)?
2. Does the existing accepted Open remain outside corrected raw H/L as recorded
   by the parent guard?
3. Does `accepted_open * independently certified expected_factor` fall inside
   corrected raw H/L?
4. Where official IDX `OpenPrice` is positive, is it inside corrected raw H/L?
5. Does the factor-transformed accepted Open exactly equal official IDX
   `OpenPrice`?

The factor direction is frozen before inspection: HLC remediation established
`official raw / parent Yahoo-adjusted = expected_factor > 1`, so the only
primary reconstruction diagnostic is `accepted_open * expected_factor`.
`accepted_open / expected_factor` is retained only as an adversarial diagnostic.

## Outcome-blind boundary

The forensic runner:

- makes zero provider/network calls;
- performs zero model fit/scoring/tuning;
- reads no historical target values and no protected/fresh-forward outcomes;
- does not mutate Open, HLC, the corrected candidate panel, or any parent
  artifact;
- does not authorize clean refit;
- uses official IDX `OpenPrice`, never `FirstTrade`, as the official Open witness.

## Possible dispositions

- full official Open support plus exact factor reconstruction: sufficient to
  preregister a separate field-level Open remediation;
- full official Open support without exact factor reconstruction: official-Open
  remediation may still be preregistered, but the mechanism remains partially
  unresolved;
- full factor-based in-range recovery with partial official support: remediation
  design remains review-required and cannot be auto-applied;
- otherwise: Open basis remains unresolved and clean refit stays blocked.

No disposition itself repairs Open.  A separate remediation contract must be
frozen after this forensic result if repair is warranted.
