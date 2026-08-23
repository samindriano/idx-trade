# Historical E2E Close/RMV/Tradability Audit V1

Date: 2026-08-24
Branch: `research/idx-historical-e2e-replay-v1`
Scope: outcome-blind input audit only

## Result

The accepted readiness artifacts provide complete current-session Close/H/L/
Volume and regular-market-value inputs for the 5,693 exposure rows. This is
an input-integrity result, not a tradability certification and not a replay or
performance result.

Verdict: `CLOSE_RMV_CERTIFIED_FOR_EXPOSURE_INPUTS_TRADABILITY_REMAINS_SEPARATE_GAP`

## Pinned audit

External output root:
`D:\Documents\Project\idx-historical-e2e-close-rmv-tradability-audit-20260824-v2`

Summary SHA-256:
`36d35aa5a453b21441b209ffdb4b2553212d342fab25698e2f7ff5787b392bcb`

The audit was computed from these accepted inputs:

| Artifact | SHA-256 |
|---|---|
| readiness `MANIFEST.json` | `86304dac2226f40e58f18ea302f709106b67609165b4bb488bda4c5d7b4564e7` |
| `holding_input_coverage.csv` | `baf94a6c308eb054dc32e72f3dfaa94735ffc9800718dc2c2f2f731e4ec059b9` |
| `decision_v2_exposure_universe.csv` | `110d3f7543c33e90a7d2cea1352f6360e0385fd5399c4b61409ee3acba56d030` |
| `regular_market_value_coverage.csv` | `68048278f11a9b751fd939fdef8b5defed624204055e549941471907b31a0e8e` |

## Coverage and invariants

- 5,693 exposure rows, 1,297 intents/spells, 600 signal sessions, 347 tickers.
- Current Close/H/L/Volume: 5,693/5,693 complete; no missing, non-finite,
  non-positive, low-greater-than-high, or Close-outside-H/L violations.
- Current regular market value: 600/600 session coverage, minimum coverage
  100%; no missing, non-finite, or non-positive values.
- Exposure-universe outer-key mismatch: 0; duplicate ticker×signal-session
  keys: 0; signal-date parse failures: 0; entry-index/session-index
  mismatches: 0.
- Next-session H/L/C/Volume/RMV: 5,692/5,693 complete. The one incomplete
  next-session row remains excluded rather than repaired.
- `corporate_action_integrity_verified` is true for all current rows and for
  5,692 next-session rows in this input artifact; this does not replace the
  separate event-window CA gate.

## Boundary

The coverage artifact does not independently establish listing status,
suspension/tradability, or an exchange-session execution eligibility rule.
The field-level audit therefore records
`tradability_evidence_status=NOT_INDEPENDENTLY_CERTIFIED_BY_THIS_COVERAGE_ARTIFACT`.
No replay scope is expanded on this evidence alone.

No labels, protected outcomes, future returns, model fitting, or performance
metrics were accessed.
