# INC-001 Authority Contract Gap Map V1

Date: 2026-08-31 Asia/Jakarta
Repository: `samindriano/idx-trade`
Lane: `data/ca-aware-feature-basis-remediation-v1`
Audit tree: `b359f1ee381cc0eca98d3b7012a0bb1164658d7a`
Mode: read-only, outcome-blind

## Purpose and decision

This is one bounded follow-up after the population/as-of feasibility decision.
It maps the existing minimum source contract to the canonical tracked gate,
current producer, retained evidence, and the smallest evidence package that
could close each gap. It does not design or implement an adapter.

`AUTHORITY_CONTRACT_GAP_MAP=COMPLETE`

`ADMISSION_READINESS=BLOCKED`

The canonical gate already has the required acceptance boundary. The material
gap is authoritative population-wide source evidence, not a missing V2/V3
orchestration layer.

## Requirement-to-boundary map

| Requirement | Existing canonical owner | Current producer/evidence | Status | Minimum evidence to close |
| --- | --- | --- | --- | --- |
| One explicit row for every required identity/session in fit, application, and dependency closure | `src/idx_trade/ca_aware_feature_basis_r3.py:615-689` (`global_ca_population_gate`); geometry builders at `:102-358` | `scripts/run_ca_aware_feature_basis_reconciliation_v1.py:255-316, 830-846` builds observed support and closure geometry from retained inputs | `UNKNOWN` | A single immutable source snapshot enumerating every required identity/session for all fit, application, and closure scopes, with explicit universe, session, and interval boundaries; bind exact row-set hashes to the existing gate |
| Stable PIT security identity and listing/delisting/relisting/symbol-change semantics | R3 identity normalization and containment at `src/idx_trade/ca_aware_feature_basis_r3.py:48-100, 641-693` | R3 and Security Master evidence establish identity geometry/presence only; source matrix classifies listing evidence as `PARTIAL_PASS_FOR_IDENTITY_ONLY` | `PARTIAL` | PIT-valid identity records with effective listing intervals, relisting/symbol-change mapping, knowledge time, source/version, and hash for every required identity/session |
| Complete positive enumeration for every frozen structural family | `src/idx_trade/ca_feature_basis_family_coverage_v1.py:75-143, 146-260`; global use at `ca_aware_feature_basis_r3.py:694-741` | Retained IDX/KSEI rows are parsed positive facts or partial result sets; no population-wide family census exists | `UNKNOWN` | Source-defined complete family enumeration across the exact scope and interval, including a deterministic manifest and per-claim source/hash provenance |
| Explicit exhaustive no-event result for every family and interval | `src/idx_trade/ca_feature_basis_family_coverage_v1.py:161-223, 236-260` requires every frozen family per identity/session; `ca_feature_basis_gate_v1.py:150-212` treats missing coverage as unknown | IDX negative authority is `UNSUPPORTED`; KSEI complete interval/no-event authority is `UNKNOWN`; page/query absence is not a no-event row | `UNSUPPORTED / UNKNOWN` | A source contract that explicitly defines exhaustive no-event semantics and emits one certified no-event claim per family/identity/session; empty pages and category responses cannot satisfy this row |
| Knowledge/as-of time no later than decision cutoff | `src/idx_trade/ca_aware_feature_basis_r3.py:742-795` validates temporal attestation fields and accepted semantics | Runner temporal output at `scripts/run_ca_aware_feature_basis_reconciliation_v1.py:391-435` records snapshot bounds but explicitly returns `UNKNOWN_NO_PER_SESSION_COVERAGE_ATTESTATION` | `UNKNOWN` | Per identity/session temporal attestation with source-defined knowledge/as-of semantics, decision cutoff ordering, source ref, evidence SHA, and deterministic row-set binding |
| Observed-through and coverage interval boundaries | Same R3 temporal boundary at `ca_aware_feature_basis_r3.py:742-795`; runner diagnostic at `:415-434` | KSEI snapshot has retrieval timestamp bounds but no per-session coverage start/end or observed-through authority | `UNKNOWN` | Source-defined `coverage_start`, `coverage_end`, `observed_through`, and session-calendar semantics for every scope/family, with no extrapolation beyond the stated interval |
| Revision, correction, amendment, and snapshot/version identity | R3 only validates hashes and source contracts at `ca_aware_feature_basis_r3.py:717-737, 775-795`; it does not manufacture revision authority | Source matrix says retained queries have no atomic snapshot, historical as-of, or revision contract; request records are retrieval evidence only | `UNKNOWN` | Immutable raw and normalized snapshot IDs, append-only revision/amendment lineage, supersession rules, and hash-bound version selection as of each decision cutoff |
| Exact basis-changing transition semantics | `src/idx_trade/ca_economic_event_reconciliation_v1.py:321-455`; semantic veto at `src/idx_trade/ca_feature_basis_gate_v1.py:63-98` | V16 remains immutable at 163 resolved / 178 unresolved; V17 promotes four rows to 167 resolved / 174 unresolved while conserving event/source/linkage populations | `PARTIAL; admission blocked` | For every basis-changing event in the admitted scope, an accepted transition semantic, valid transition date/interval, source event ID, source ref/SHA, or explicit fail-closed unresolved state; structural completion must be proven before admission |
| Immutable provenance binding from source through gate | Family and temporal checks require source contracts, refs, and SHA values at `ca_aware_feature_basis_r3.py:717-737, 775-795`; event semantics require SHA at `ca_feature_basis_gate_v1.py:72-90` | V16/V17/manifests are immutable and manifest-bound, but no authoritative population/as-of source contract is bound to the gate | `PARTIAL` | One deterministic manifest binding raw bytes, normalized rows, scope/session/family sets, source contract/version, as-of metadata, code/gate inputs, and all hashes; any mismatch remains blocked |
| Existing canonical producer reaches the gate before admission | `scripts/run_ca_aware_feature_basis_reconciliation_v1.py:900-914` calls the R3 gate and passes `structural_event_complete=False` | Current runner deliberately emits fail-closed diagnostics; no tracked V17 runtime reference exists, and no producer emits complete population-wide temporal/family attestations | `FAIL-CLOSED / BLOCKED` | A future producer may populate the existing inputs only after the source contract is proven; the current canonical gate must consume those exact bound artifacts before admission, without a parallel V2/V3 path |

## Current boundary and non-boundary

The canonical path is:

`observed dependency geometry -> R3 population gate -> family/temporal checks -> CA basis admission`

Observed geometry proves required support and containment properties, but it is
not population authority. KSEI ticker presence proves neither complete interval
coverage nor a negative event claim. V17 transition promotions prove selected
event semantics only; they do not define the population or historical-as-of
state.

There are two same-named population-gate implementations in the repository:
the runner uses `ca_aware_feature_basis_r3.global_ca_population_gate`, while the
older source-authority audit module has a separate implementation. This is an
ownership maintenance risk to resolve before future wiring, not a reason to
add another compatibility layer or silently treat the functions as equivalent.

## Acceptance sequence when authoritative evidence exists

1. Verify the source contract covers all required identity/session rows and all
   frozen structural families for the declared interval.
2. Verify explicit no-event semantics, PIT identity intervals, knowledge/as-of,
   observed-through, and revision/version rules from the source itself.
3. Verify raw/normalized bytes, scopes, calendar, source version, and code/gate
   inputs through one deterministic manifest.
4. Feed those artifacts into the existing R3 gate and require structural,
   family, temporal, identity-containment, and semantic checks to pass.
5. Keep any unresolved or ambiguous row fail-closed; do not narrow the
   cross-sectional population post hoc.

No step authorizes provider acquisition, production execution, historical
backfill, outcome access, model work, counter/PaperState/R2 mutation, or an
adapter. The next external decision is source-authority acquisition, not code
architecture.

## Safety result

No application/runtime/science code, immutable artifact, admission state,
provider state, production state, counter/PaperState/R2, or scheduler was
changed. No provider call, outcome/target access, deployment, backfill, or
Actions rerun occurred during this follow-up.
