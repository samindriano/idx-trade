# CA / Issuer Price-Basis Admission Specification V1

Status: `SPECIFICATION_ONLY / NOT_ADMITTED`

This specification records the minimum evidence required before any candidate
history can be treated as comparable across corporate actions, security
transitions, and issuer identity. It is a future Data QA/admission contract,
not a repair instruction and not evidence that the current panel passes.

## Current evidence boundary

The independent CA/issuer review separates narrow checks from global
admission:

- The retained HLC overlay is internally consistent but covers only 1,657 of
  981,940 panel rows and two event families.
- The unresolved residual contains 188 keys across 19 tickers and is disjoint
  from the overlay. Candidate stress is material for C1 (82,357 score changes,
  31,346 rank changes, minimum Top-30 overlap 36.667%), while C2 and C4 are
  less sensitive but still not globally cleared.
- Security intervals pass only as a narrow ticker-level mapping. They do not
  establish issuer/ISIN continuity.
- Rights, conversion, listed-share transitions, and adjusted/unadjusted source
  behavior remain incomplete or semantics-unknown. BBCA cross-source evidence
  shows a 5x-to-1x basis block against IDX, but does not by itself establish
  event causality.

Therefore current disposition remains `GLOBAL_BASIS_BLOCKED`; no price repair,
candidate promotion, or protected evaluation is authorized.

## Required admission inputs

An admissible evidence package must bind, at minimum:

1. A population-complete security/issuer/ISIN master covering every finite
   candidate input row and every relevant listing, delisting, relisting, or
   security transition.
2. Event-level corporate-action records with event family, issuer/security
   identity, effective date, ex/record or transition dates where applicable,
   ratio/factor, and source authority.
3. Knowledge/publication time and revision/vintage lineage for each event;
   effective date alone is insufficient for PIT use.
4. Explicit OHLCV/value basis semantics, including whether each field is
   adjusted, unadjusted, split-adjusted, rights-adjusted, or mixed, with source
   and unit definitions.
5. Complete handling rules for split/reverse-split, rights distribution,
   bonus shares, mandatory/voluntary conversion, mergers, delisting/relisting,
   and ticker changes. Absence of an observed event is not a negative proof.
6. A reproducible event-to-window linkage that labels every affected candidate
   row/window as resolved, unresolved, or out of scope.

## Candidate-level gates

For each candidate and every finite input window:

- all security/issuer identities resolve to an admitted continuity chain;
- every potentially affecting event is linked or explicitly excluded with
  authority;
- feature fields share one admitted price/share/value basis;
- no fallback factor or unverified `idx_close` substitution is used;
- unresolved rows are either excluded under a predeclared population rule or
  cause the candidate gate to fail;
- the gate result, source hashes, code commit, and exclusion counts are
  independently reproducible.

The required result is `PASS` for each candidate input window. Any material
`UNKNOWN` remains a blocking result; a bounded overlay PASS cannot substitute
for population-complete admission.

## Explicit non-claims

This specification does not establish that C1, C2, C4, H-LIQ-01, H-VOL-01,
or H-EXC-02 is predictive, superior, or ready for target evaluation. It does
not authorize opening H5/H10, forward returns, or any protected outcome.

## Evidence references

- `2026-09-19_ALPHA_CA_ISSUER_BASIS_REDTEAM_RESULT_V1.md`
- `2026-09-20_ALPHA_CA_CANDIDATE_EXPOSURE_COMPLETENESS_RESULT_V1.md`
- `2026-09-20_ALPHA_BBCA_PRICE_BASIS_RECONCILIATION_RESULT_V1.md`
- `2026-09-20_ALPHA_BBCA_CA_EVENT_LINKAGE_RESULT_V1.md`
- `2026-09-19_ALPHA_C1234_REDTEAM_ADJUDICATION_V1.md`

No repository, canonical data, provider, cloud, capture, telemetry, target,
outcome, or production state was modified to create this specification.
