# V4-X1 Forward Corporate-Action Feature-Basis Closure V1

Status: `FORWARD_CA_FEATURE_BASIS_REMEDIATION_READY_FOR_REVIEW`

This checkpoint records an outcome-blind, review-only remediation candidate
based on the production workflow's pinned implementation ref
`82007457522d6e268de8bd6e1b75762fb76accfe`. It does not certify any forward
session and was not deployed or activated.

## Forensic finding

The retained certification ledger contains 44 resolved transition rows for
the requested transition semantic. All 44 remain `BASIS_UNKNOWN` separately
for price, volume, and regular-market-value. The executable clean scorer panel
ends on 2026-07-31 while the declared frozen historical end is 2026-07-17;
this is recorded as `ACTUAL_FROZEN_BOUNDARY_DRIFT`. No scorer-bound transition
or same-basis attestation was found. The 15 retained forward sessions from
2026-08-03 through 2026-08-31 remain `DATA_READY` and outcome-blind, but have
no feature-basis certificate.

## Remediation boundary

The candidate extends the existing `PopulationScoreGate` only. A required
`feature_basis_evidence.json` sidecar is bound to the exact `model_input`,
clean scorer panel, actual scorer historical boundary, official session
window contract, identity/calendar/revision/PIT attestations, and per-field
H/L/C/volume/regular-market-value source hashes. It covers the complete
scorer-consumed population and admits only explicit same-basis evidence with
no certified transition in any exact final-feature dependency window.

Missing, malformed, stale, contradictory, non-PIT, `NO_KNOWN_TRANSITION`, or
transition-overlapping evidence yields whole-session scientific
non-admission. The scorer formulas, model inputs, cross-sectional population,
PREOPEN_CA operational state, PaperState, counter, outcomes, provider calls,
and R2 are untouched.

## Validation and safety

- Layer 2 selected the acceptance-only whole-session gate; direct scorer
  wiring, row deletion, silent adjustment, and inferred no-event paths were
  rejected.
- Layer 3 passed only this minimal existing-gate extension for review.
- Focused population, runtime, and adversarial feature-basis tests pass.
- The retained 44-event replay remains `BASIS_UNKNOWN`; all 15 current
  forward sessions remain `SOURCE_CAPTURE_UNRESOLVED` on missing certificates.
- No outcome, provider, counter, PaperState, R2, scheduler, deployment, or
  production workflow action occurred.

The next acceptance gate is a separately authorized, genuine forward session
with a population-wide certificate from independently authoritative,
hash-bound evidence. Historical sessions are not rewritten and no prior
counter credit is implied.
