# Alpha Corporate-Action / Price-Basis Audit V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `B_J_CORPORATE_ACTION_PRICE_BASIS_EXPOSURE_AUDIT`
Result: `PASS_STRUCTURAL_ONLY / PARTIAL FORENSIC EVIDENCE`

## Question

Do the retained local corporate-action and price-basis artifacts establish
that C1/C2/C4 input histories are comparable across corporate actions and
issuer/security transitions? If not, what candidate-specific exposure can be
quantified without touching outcomes or modifying the frozen panel?

## Boundary

This is a read-only, outcome-blind audit. It does not acquire providers, repair
the canonical panel, refit or rescore a model for research admission, open
H5/H10 or forward returns, or authorize a clean refit. The upstream retained
price-basis artifacts explicitly say `clean_refit_authorized=false` and
`STOP_FOR_FORENSIC_REVIEW_NO_CLEAN_REFIT`; those decisions remain in force.

## Evidence inventory

### Official IDX split/reverse-action inventory

The retained official IDX listing-activity artifact contains 55 `stockSplit`
rows across 52 tickers from 2021-05-18 through 2026-07-21. Only 39 rows have a
numeric ratio; the remaining ratio semantics are not sufficient to infer a
transition. Its source identity is
`IDX_LISTING_ACTIVITY_ISSUED_HISTORY`.

This is an event inventory, not a complete certification of all split,
reverse-split, rights, bonus, conversion, dividend, relisting, or issuer/ISIN
transitions.

### Retained HLC overlay

The staged HLC overlay contains 1,657 rows across 12 tickers from 2025-04-28
through 2026-07-20:

- 1,201 `MANDATORY_CONVERSION` rows;
- 456 `RIGHT_DISTRIBUTION` rows;
- all 1,657 rows have non-unit observed factors;
- 727 overlay keys intersect the eligible decision universe.

The current clean panel contains the remediated close exactly on all 1,657
overlay keys: panel close equals `remediated_close` for 1,657/1,657 rows,
equals the retained `original_close` for 0/1,657 rows, and has 0 mismatches.
This shows that the known overlay is already represented in the panel for this
bounded population; it does not show that the panel is globally CA-complete or
that its `YAHOO_RAW` provenance label is an authoritative historical-basis
contract.

### Remaining forensic gaps

The retained upstream summaries report:

- 188 `unresolved_nonstable_scale_basis_rows` intersect the panel, across 19
  tickers, with representative scale factors around 1.014, 1.05, 1.167,
  1.48, 1.69, 2, 5, 10, and 25;
- post-remediation HLC exactness improved to 980,154/981,940 rows (99.8181%),
  but remained non-universal;
- the broad volume/value guard found 0 value mismatches and 0 volume
  mismatches over 981,940 rows, but retained 21,221 provenance seams;
- open-price adjudication retained 439 factor-fallback candidates, 2
  official/factor disagreements, and 2 unresolved out-of-range rows;
- open-price clean refit remained unauthorized and fail-closed.

These findings are incompatible with a global `corporate_action_basis=PASS`
or a target-admission claim.

## Candidate-specific exposure

Using the frozen 1,260-session universe and the existing C1/C2/C4 feature
artifact:

- 1,227 eligible rows across 7 tickers fall within the forward 60 official
  sessions of an HLC-overlay row; this is a structural exposure count, not a
  target or return calculation.
- The corrected implementation reproduces the stored C1/C2/C4 scores exactly
  (maximum absolute difference 0 for every candidate).
- Replaying the retained HLC overlay in memory produces no score changes, no
  rank changes, and no Top-30 changes for C1/C2/C4. Top-30 overlap is 100% on
  all 1,141 C1 dates and all 1,201 C2/C4 dates.

The correct interpretation is narrow: the current panel already contains the
bounded HLC overlay, so replaying that same overlay is a no-op. It is not
evidence that unresolved rows, other event families, or open-price basis are
safe. The candidate statuses therefore remain unchanged.

## Decision matrix

| Question | Result | Consequence |
|---|---|---|
| Known HLC overlay represented in current panel? | `PASS` for 1,657/1,657 rows | No additional bounded HLC replay needed |
| Candidate score/rank sensitivity to replayed overlay? | `NONE OBSERVED` | No candidate status change |
| All historical CA transitions covered? | `UNKNOWN` | No global CA admission |
| 188 non-stable scale rows resolved? | `NO` | Keep basis risk open |
| Open-price residuals fully resolved? | `NO` | H5/H10 packet remains blocked |
| Issuer/ISIN transition chain certified? | `NO` | Security-master interval pass is insufficient |
| Clean refit authorized? | `NO` | Do not refit, rescore, or promote |

## Artifacts and hashes

- Builder: `research/alpha_corporate_action_basis_audit_v1.py`
- Builder SHA-256: `b405f69f4ed723d19560de93cae16b10367dbb695846ea75db8ce1f9b9de8f41`
- Verifier: `research/verify_alpha_corporate_action_basis_audit_v1.py`
- Verifier SHA-256: `fb525311cad8783758db5b67b1a583eff5c7183aeae8a38acdce9711d93a18e4`
- Output: `alpha_corporate_action_basis_audit_v1.json` in
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`
- Output SHA-256: `30d4083a8b3311cfd490f6b03ebad72cffa7e404cb8565f0fc979c6d3e516955`
- Audit status: `PASS_STRUCTURAL_ONLY`
- Independent verifier: `PASS`
- Target/provider/outcome access: none
- Panel mutation/model fit/model scoring: none

## Final disposition

Corporate-action and price-basis risk is **partially narrowed, not cleared**.
C1/C2/C4 remain `FUTURE_RESEARCH`; C3 remains `BLOCKED`; no candidate becomes
`READY_FOR_REENTRY`. The next useful CA task requires a separately admitted,
complete transition/issuer-basis package or an independent red-team that can
resolve the 188 non-stable rows and open-price residuals without changing the
frozen research contract.
