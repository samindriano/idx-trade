# Open Price-Basis Forensic V1 — Result + Residual Adjudication Preparation

Date: 2026-08-20 Asia/Jakarta  
Branch: `data/price-basis-remediation-v1`

## Parent forensic result

Local runtime manifest SHA-256:
`4538f4d35d042e7e3257b746a56065702463cf8393b1ae922db473a8b355724e`

Status:
`OPEN_BASIS_FORENSIC_UNRESOLVED_REFIT_BLOCKED`

Frozen population is exactly 1,657 HLC-remediated rows / 12 tickers. All 1,657
existing V4-X accepted Opens come from `DERIVATIVE_OPEN` and all remain outside
the corrected raw-IDX H/L envelope before Open-basis reconstruction.

Forensic totals:

- official IDX `OpenPrice` positive: 1,216 rows;
- official IDX `OpenPrice` inside corrected H/L: 1,216 rows;
- existing accepted Open x independently certified CA factor inside corrected
  H/L: 1,654 rows;
- factor-transformed Open exactly equals official IDX `OpenPrice`: 1,214 rows;
- existing accepted Open equals official IDX `OpenPrice`: 0 rows;
- factor-down hypothesis inside corrected H/L: 0 rows.

This strongly supports the interpretation that accepted Open remained on the
same adjusted basis that H/L/C remediation removed. It does not authorize an
Open repair because three factor-up rows fail corrected H/L and two
Official-vs-factor rows disagree despite official positive support.

## Relevant prior independent evidence

The existing `data/idx-open-ca-scale-reconstruction-v1` lane had already shown
that provider Open can require a corporate-action scale transform before it is
compatible with raw canonical H/L/C. That earlier lane admitted 2,184 exact
rows for CLEO/MMIX/WGSH only when independently sourced official CA factors
made transformed provider H/L/C exact and transformed Open remained inside
canonical H/L. That result is corroborating evidence, not a license to repair
this new population automatically.

Official IDX Stock Summary `OpenPrice` is treated as the primary raw-Open
candidate where finite, positive, and inside corrected H/L. `FirstTrade` is not
an Open fallback.

## Residual adjudication boundary

Before any Open remediation contract is frozen, run the read-only residual
adjudicator over the immutable forensic CSV. It must classify every row into
one of the evidence states needed for a later preregistration:

1. official IDX raw Open primary candidate;
2. official unavailable + CA-factor fallback candidate inside corrected H/L;
3. official-primary / factor disagreement;
4. no official support + factor reconstruction outside corrected H/L.

The adjudicator records exact ticker/date exceptions and per-ticker mechanism
support. It performs no repair and does not authorize model refitting.

## Model boundary

Even after Open remediation is eventually materialized, V2/V4-X clean refit is
not to run immediately. Other data lanes are under parallel audit. The corrected
price candidate should remain immutable and model work should wait for an
explicit cross-lane data-consolidation freeze.

No model fit/scoring/tuning, target-value access, protected-forward access,
provider calls, or parent-panel overwrite are authorized by this checkpoint.
