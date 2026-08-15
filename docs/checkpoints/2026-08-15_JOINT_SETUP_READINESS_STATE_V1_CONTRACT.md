# Joint Setup Readiness State V1 — Contract Checkpoint

Date: 2026-08-15
Branch: `research/idx-joint-setup-readiness-state-v1`
Status: `REVIEW` (remediation complete; runtime wiring still blocked pending review)
Independent parent acceptance: `review/idx-price-trend-runtime-smoke-blocker-v1@5aa81aaf00533f3930cecdf302c0bf7de52acb4c`

## Scope

This lane defines a deterministic, outcome-blind contract over two accepted
descriptive parent states:

1. Foreign Flow Setup State V1 / Representation V2;
2. Price / Trend / Confirmation State V1.

It does not wire the contract into the prospective runtime. It does not call a
provider, read labels/outcomes, fit or score a model, change O2/counters, or
change either parent formula or threshold.

`ENTRY_ELIGIBLE` is a descriptive context state only. It is not a buy/sell,
trade, or execution recommendation.

## Join and provenance contract

The join key is exact `(ticker, feature_session)`. The Foreign Flow
`flow_through_session` must equal the Price State `source_session`, and both
must map to the next official session in the supplied unique official
calendar. Parent key sets, ticker identity, dates, and parent row contract
versions must match exactly; missing, duplicate, partial, or mismatched rows
fail closed without materializing a partial joint row.

Each parent also requires explicit 64-character artifact and manifest SHA-256
identities, contract version, source kind, `outcome_blind=true`,
`provider_calls=0`, `model_fitted=false`, `model_scoring=false`, and
`trade_recommendation=false`.

The joint output carries both parent identities, source kinds, exact source and
feature sessions, contract version, reason codes, and the same protected flags.
Contract fingerprint:
`a79e37cacf9ec428e27b4b398a757b9415e6e358b11b0d10edaf78a50c3d3599`.

## Frozen descriptive rule matrix

Rules are evaluated in this order:

| Condition | State |
|---|---|
| Invalid, missing, duplicate, or incompatible parent | fail closed; no output row |
| Foreign Flow or Price State is `INDETERMINATE` | `IGNORE` |
| Foreign Flow `DISTRIBUTION_PRESSURE` | `IGNORE` |
| Price `DOWNTREND` | `IGNORE` |
| Price `FAILED_BREAKOUT_RECENT` | `IGNORE` |
| Strong flow (`PERSISTENT_ACCUMULATION` or `STEALTH_ACCUMULATION_CANDIDATE`) + supportive trend (`UPTREND` or `EARLY_REVERSAL`) + `BREAKOUT_CONFIRMED` | `ENTRY_ELIGIBLE` |
| Supportive flow (`ABNORMAL_ACCUMULATION`, `PERSISTENT_ACCUMULATION`, or `STEALTH_ACCUMULATION_CANDIDATE`) + `BASING`, `EARLY_REVERSAL`, or `UPTREND` | `READY` |
| One supportive context or early confirmation (`BREAKOUT_WEAK_VOLUME` / `NEAR_BREAKOUT`) | `WATCH` |
| Otherwise | `IGNORE` |

## Reason codes

The implementation uses deterministic codes including:

`PARENTS_VALID`, `CAUSAL_SESSION_ALIGNED`,
`FOREIGN_FLOW_STATE_INDETERMINATE`, `PRICE_STATE_INDETERMINATE`,
`FOREIGN_FLOW_DISTRIBUTION_PRESSURE`, `PRICE_DOWNTREND`,
`PRICE_FAILED_BREAKOUT_RECENT`, `FLOW_STRONG_ACCUMULATION`,
`FLOW_ACCUMULATION_CONTEXT`, `PRICE_SUPPORTIVE_TREND`,
`PRICE_BREAKOUT_CONFIRMED`, `PRICE_EARLY_CONFIRMATION`, and
`NO_ALIGNED_SUPPORT`.

Compatibility failures use fail-closed codes such as
`PARENT_KEY_SET_MISMATCH`, `SOURCE_SESSION_MISMATCH`,
`CAUSAL_SESSION_MISMATCH`, `PARENT_DUPLICATE_KEY`,
`PARENT_ACCESS_FLAGS_INVALID`, `PROVENANCE_HASH_INVALID`, and
`PROVENANCE_CONTRACT_MISMATCH`.

## Validation

- Focused: `python -m pytest tests/test_joint_setup_readiness_state.py -q` → **11 passed**.
- Full: `python -m pytest -q` → **50 passed, 1 failed / 51 collected**.
- The sole failure is the known unrelated `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` expectation (expected 1, actual 2 independent `raw_close` and `vendor_adj_close` conflicts). This lane did not modify storage.
- `git diff --check` is required before push.

Synthetic/adversarial coverage proves deterministic four-state mapping,
missing/partial parent rejection, source-target causality, duplicate and
unknown state rejection, outcome/model payload rejection, provenance/hash and
flag enforcement, parent hash propagation, and stable contract identity.

## Remediation review closure

The reviewed issues are addressed without changing either accepted parent
module. `BASING` is now a READY trend state, while ENTRY remains restricted to
`EARLY_REVERSAL`/`UPTREND` plus strong accumulation and confirmed breakout.
Hard blockers, supportive/strong labels, READY/ENTRY trend sets, early and
entry confirmations, output schema, and the ordered matrix are explicit frozen
constants. The classifier and fingerprint consume those same definitions.
Invalid or incompatible parents are `FAIL_CLOSED_NO_OUTPUT`, not `IGNORE`.
Ticker identity is already canonical and is now rejected on null, lowercase,
whitespace, or `.JK` forms rather than normalized. Provenance flags are
explicit and optional forward/outcome flags are rejected unless explicitly
false. Parent SHA fields remain declared identities; byte verification is
reserved for the future runtime adapter.

## Boundary

No prospective runtime wiring is authorized by this checkpoint. A separate
review must approve any later runtime integration, and it must preserve the
same parent hashes, calendar/session contract, reason codes, and descriptive
only semantics.
