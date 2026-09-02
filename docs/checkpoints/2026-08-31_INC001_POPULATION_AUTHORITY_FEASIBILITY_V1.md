# INC-001 Population Authority Feasibility V1

Date: 2026-08-31 Asia/Jakarta
Repository: `samindriano/idx-trade`
Review lane: `data/ca-aware-feature-basis-remediation-v1`
Review HEAD: `488f2ca3a9b07ad182bf17e113c90f4f59dbb538`
Outcome-blind: yes

## Scope and boundary

This is a bounded scientific-integrity feasibility review of the remaining
INC-001 historical Corporate Action population-authority blocker. It consumes
only already retained immutable artifacts and current repository code. It does
not acquire data, call providers, access outcomes or targets, fit/refit/score a
model, mutate canonical data, mutate counters/PaperState/R2, deploy, dispatch,
backfill, or merge.

The single primary artifact is:

`D:\Documents\Project\idx-ca-inc001-population-authority-feasibility-20260831-v1`

Artifact manifest SHA-256:

`89911c0ea1cd14f5c6dad771214f0fb2f6b4873afaae65541ab10329855c0145`

The artifact binds the current V16 reconciliation, closure feasibility, R3.1
geometry, retained V8 source-authority audit, and the bounded merger/capital
artifacts. Its validation report is all PASS for manifest binding, counts,
geometry recomputation, and outcome-blind guardrails.

## Red-team verdict

`KNOWN_EVENT_CLOSURE_RED_TEAM=PASS_WITH_NONBLOCKING_FINDINGS`

Known-event remediation is materially complete as a work disposition and the
long tail is parked fail-closed. However, the historical admission statement
“population authority is the sole blocker” is incomplete: V16 contains 178
`UNRESOLVED` transition semantics, including 19 capital-restructuring, 5
merger, and 4 composite cash/share events. The current R3.1 global gate remains
`FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED` and requires structural completion
before population certification can yield admission.

This is a decision decomposition correction, not permission to infer safe rows
or to reopen event-by-event archaeology.

## Current geometry

The retained R3.1 geometry was recomputed from its immutable closure CSV for
this report and matches its summary exactly:

- final fit: 240,344 rows / 629 tickers;
- application: 276,153 rows / 716 tickers;
- cross-section-only: 35,809 rows / 274 tickers;
- dependency closure: 365,968 rows / 716 tickers;
- closure date range: 2021-04-29 through 2026-07-17;
- retained KSEI presence: 610 of 716 tickers.

The per-ticker required geometry is in
`dependency_authority_requirements.csv`. Geometry is not event authority: it
describes the identities and intervals that an authoritative source would have
to cover.

## Minimum authority contract

Before historical admission, one authoritative contract must provide:

1. PIT-valid security/listing identity and symbol-change, listing, delisting,
   and relisting semantics;
2. explicit coverage for every required identity/session in fit, application,
   and dependency closure;
3. complete positive enumeration for every frozen structural family;
4. source-defined exhaustive no-event results for every family and interval;
5. exact basis-changing transition semantics or an explicit unresolved state;
6. knowledge/as-of and observed-through boundaries no later than the decision
   cutoff;
7. revision, correction, amendment, and snapshot/version semantics; and
8. immutable source-contract, raw-response, normalized-evidence, retrieval,
   and manifest hashes.

Unknown, malformed, incomplete, ambiguous, or unbound evidence remains
blocked. Absence from a current page, empty category query, or Security Master
listing does not become a no-event row.

## Retained-source feasibility

The current official evidence is insufficient to certify the contract:

- IDX category queries provide positive result sets only; all retained negative
  contracts remain `UNKNOWN_NO_EXHAUSTIVE_NO_EVENT_CONTRACT`.
- The comparable broad IDX result had 700 unique rows while the exact nine
  filtered union had 202, leaving 498 broad rows outside that union. The
  observed PACK disappearance between comparable results is source-result
  instability, not historical no-event authority.
- KSEI page parsing supports observed positive rows, but pagination,
  completeness, observed-through/as-of, and no-event semantics are unknown.
- Security Master/listing evidence is identity continuity only.
- OJK statistics are a supervisory cross-check, not a ticker/session negative
  or transition authority.

`EXISTING_OFFICIAL_SOURCES_CANNOT_CERTIFY_POPULATION_COMPLETENESS`

Documentary Phase 8 candidate assessment is limited to three paths and did not
acquire any candidate data or credentials: IDX Data Reference licensed product
(highest-likelihood candidate), KSEI CIRT/institutional data service (plausible
but unproven from public retained evidence), and OJK statistics (cross-check
only). Details and official references are in
`official_candidate_paths.csv`.

## Subset and prospective result

`CERTIFIABLE_SUBSET_FEASIBILITY=NO_SAME_SCIENCE_CERTIFIABLE_SUBSET_ESTABLISHED`

Post-hoc removal of uncertified tickers would change the frozen V4
cross-sectional ranks, market context, and population geometry. A future
source-defined subset would require an explicitly new science/evaluation
contract; it is not a historical rescue under the current frozen contract.

`HISTORICAL_INC001=BLOCKED_ON_POPULATION_AUTHORITY_AND_UNRESOLVED_TRANSITION_SEMANTICS`

`PROSPECTIVE=CONDITIONALLY_POSSIBLE_NOT_CURRENTLY_PROVEN`

Prospective acceptance would require per-session complete interval and explicit
no-event attestations, pre-cutoff knowledge/as-of, append-only revisions,
resolved transition semantics, and binding of the event census, scope,
geometry, and evidence hashes to the existing fail-closed gate. This review did
not execute that next action.

## Implementation hardening note

`src/idx_trade/ca_aware_feature_basis_r3.py` currently accepts
`structural_event_complete` as a caller boolean and only reports
`scope_evidence` diagnostics. The current result is still fail-closed, but any
future PASS must bind the structural census and validate scope evidence rather
than treating those inputs as unbound claims. No implementation change is made
in this audit.

## Scientific and operational state

- data admission: `FAIL`;
- research admission: `FAIL`;
- historical application: `BLOCKED_PHASE_E_NOT_RUN`;
- model promotion: `NOT_EVALUATED`;
- refit: not authorized;
- counter action: none;
- outcomes/targets: not accessed;
- provider calls/acquisition: none;
- canonical historical rewrite: none;
- production/backfill/deploy/merge: none.

## Next decision

Stop event-by-event archaeology. Obtain the smallest authoritative
population-wide complete-interval, explicit-no-event, historical-as-of, and
revision contract; bind it to the existing gate and V16 transition census; then
re-run the existing fail-closed admission check. Do not execute that action
from this checkpoint.
